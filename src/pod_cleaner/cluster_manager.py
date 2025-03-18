import os
from typing import List, Dict, Optional
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from .config import KUBECONFIG_DIR, POD_ERROR_STATES
from .logger import setup_logger

logger = setup_logger(__name__)

class ClusterManager:
    def __init__(self):
        """初始化集群管理器"""
        self.clusters: Dict[str, client.CoreV1Api] = {}
        self.version_apis: Dict[str, Dict] = {}
        self._load_all_clusters()
    
    def _load_all_clusters(self) -> None:
        """加载所有kubeconfig文件并初始化客户端"""
        if not os.path.exists(KUBECONFIG_DIR):
            logger.error(f"Kubeconfig目录不存在: {KUBECONFIG_DIR}")
            return
            
        for filename in os.listdir(KUBECONFIG_DIR):
            # 跳过隐藏文件
            if filename.startswith('.'):
                continue
                
            # 检查文件是否符合要求：
            # 1. 以.yaml或.yml结尾
            # 2. 以k8s或K8S开头
            is_valid = (
                filename.endswith(('.yaml', '.yml')) or
                filename.startswith(('k8s', 'K8S'))
            )
            
            if not is_valid:
                continue
                
            kubeconfig_path = os.path.join(KUBECONFIG_DIR, filename)
            # 跳过目录
            if os.path.isdir(kubeconfig_path):
                continue
                
            cluster_name = os.path.splitext(filename)[0]
            
            try:
                # 加载kubeconfig
                config.load_kube_config(config_file=kubeconfig_path)
                # 创建API客户端
                api_client = client.CoreV1Api()
                # 创建版本API客户端
                version_api = client.VersionApi()
                # 测试连接
                api_client.list_namespace(limit=1)
                # 获取并存储版本信息
                version_info = version_api.get_code()
                
                # 获取API服务器地址
                try:
                    # 获取当前上下文的配置
                    _, active_context = config.kube_config.list_kube_config_contexts(config_file=kubeconfig_path)
                    if active_context:
                        cluster_name_from_context = active_context['context']['cluster']
                        # 获取集群配置
                        cluster_config = config.kube_config.load_kube_config(config_file=kubeconfig_path)
                        api_server = None
                        
                        # 从配置中读取当前集群的server地址
                        kube_config = config.kube_config.new_client_from_config(config_file=kubeconfig_path)
                        if hasattr(kube_config, 'configuration') and hasattr(kube_config.configuration, 'host'):
                            api_server = kube_config.configuration.host
                except Exception as e:
                    logger.warning(f"无法获取API服务器地址: {str(e)}")
                    api_server = "未知"
                
                self.version_apis[cluster_name] = {
                    'version': version_info.git_version,
                    'build_date': version_info.build_date,
                    'platform': version_info.platform,
                    'api_server': api_server
                }
                # 存储客户端
                self.clusters[cluster_name] = api_client
                logger.info(f"成功加载集群配置: {cluster_name}")
            except Exception as e:
                logger.error(f"加载集群配置失败 {cluster_name}: {str(e)}")
    
    def get_cluster_info(self) -> Dict[str, Dict]:
        """
        获取所有集群的版本和API信息
        
        Returns:
            Dict[str, Dict]: 按集群名称组织的版本和API信息
        """
        return self.version_apis
    
    def list_problem_pods(self, namespace: Optional[str] = None) -> Dict[str, List[Dict]]:
        """
        列出所有集群中状态为Error或Unknown的Pod
        
        Args:
            namespace: 可选的命名空间过滤
            
        Returns:
            Dict[str, List[Dict]]: 按集群名称组织的问题Pod列表
        """
        problem_pods = {}
        
        for cluster_name, api in self.clusters.items():
            try:
                pods = api.list_pod_for_all_namespaces() if namespace is None else \
                      api.list_namespaced_pod(namespace)
                
                problem_pods[cluster_name] = []
                for pod in pods.items:
                    if pod.status.phase in POD_ERROR_STATES:
                        pod_info = {
                            'name': pod.metadata.name,
                            'namespace': pod.metadata.namespace,
                            'status': pod.status.phase,
                            'creation_timestamp': pod.metadata.creation_timestamp,
                        }
                        problem_pods[cluster_name].append(pod_info)
                        
                if problem_pods[cluster_name]:
                    logger.info(f"集群 {cluster_name} 发现 {len(problem_pods[cluster_name])} 个问题Pod")
                    
            except ApiException as e:
                logger.error(f"获取集群 {cluster_name} 的Pod列表失败: {str(e)}")
                continue
                
        return problem_pods
    
    def delete_problem_pods(self, namespace: Optional[str] = None, dry_run: bool = False) -> Dict[str, Dict[str, int]]:
        """
        删除所有集群中状态为Error或Unknown的Pod
        
        Args:
            namespace: 可选的命名空间过滤
            dry_run: 是否执行试运行而不实际删除Pod
            
        Returns:
            Dict[str, Dict[str, int]]: 每个集群的删除统计信息
        """
        stats = {}
        problem_pods = self.list_problem_pods(namespace)
        
        for cluster_name, pods in problem_pods.items():
            stats[cluster_name] = {'total': len(pods), 'success': 0, 'failed': 0}
            
            if dry_run:
                logger.info(f"[试运行] 将删除集群 {cluster_name} 中的 {len(pods)} 个Pod")
                continue
                
            api = self.clusters[cluster_name]
            for pod in pods:
                try:
                    api.delete_namespaced_pod(
                        name=pod['name'],
                        namespace=pod['namespace'],
                        body=client.V1DeleteOptions()
                    )
                    stats[cluster_name]['success'] += 1
                    logger.info(f"成功删除Pod: {pod['namespace']}/{pod['name']} in {cluster_name}")
                except ApiException as e:
                    stats[cluster_name]['failed'] += 1
                    logger.error(f"删除Pod失败 {pod['namespace']}/{pod['name']} in {cluster_name}: {str(e)}")
        
        return stats 