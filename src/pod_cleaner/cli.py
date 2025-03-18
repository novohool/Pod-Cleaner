import typer
import os
import sys
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.box import ROUNDED
from datetime import datetime
from .cluster_manager import ClusterManager
from .logger import setup_logger
from .config import get_kubeconfig_dir

app = typer.Typer(
    help="Pod Cleaner - 用于清理Kubernetes集群中的问题Pod的工具",
    no_args_is_help=True,  # 没有参数时显示帮助
    add_completion=False,  # 禁用自动补全，简化帮助输出
)
logger = setup_logger(__name__)
console = Console()

def create_pod_table(pods: list) -> Table:
    """创建用于显示Pod信息的表格"""
    table = Table(show_header=True, header_style="bold magenta", box=ROUNDED, show_lines=True)
    table.add_column("命名空间", style="cyan")
    table.add_column("Pod名称", style="green")
    table.add_column("状态", style="red")
    table.add_column("创建时间", style="yellow")
    
    for pod in pods:
        table.add_row(
            pod['namespace'],
            pod['name'],
            pod['status'],
            pod['creation_timestamp'].strftime("%Y-%m-%d %H:%M:%S")
        )
    
    return table

@app.command()
def list_pods(
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="指定命名空间"),
    kubeconfig_dir: Optional[str] = typer.Option(None, "--kubeconfig-dir", "-k", help="指定kubeconfig目录路径"),
):
    """列出所有集群中状态为Error或Unknown的Pod"""
    # 检查kubeconfig目录是否存在且不为空
    if kubeconfig_dir:
        os.environ['KUBECONFIG_DIR'] = kubeconfig_dir
        
    current_kubeconfig_dir = get_kubeconfig_dir()
    if not os.path.exists(current_kubeconfig_dir):
        console.print(f"\n[bold red]错误: kubeconfig目录不存在: {current_kubeconfig_dir}[/bold red]")
        return
        
    try:
        manager = ClusterManager()
            
        # 检查目录中是否有kubeconfig文件
        kubeconfig_files = [f for f in os.listdir(current_kubeconfig_dir) 
                          if f.endswith(('.yaml', '.yml')) or f.startswith(('k8s', 'K8S'))]
        if not kubeconfig_files:
            console.print(f"\n[bold yellow]警告: 目录 {current_kubeconfig_dir} 中没有找到k8s kubeconfig文件[/bold yellow]")
            return
            
        problem_pods = manager.list_problem_pods(namespace)
        
        console.print("\n[bold blue]Pod 状态检查报告[/bold blue]")
        console.print(f"检查时间: [yellow]{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/yellow]")
        if namespace:
            console.print(f"命名空间: [cyan]{namespace}[/cyan]")
        console.print("─" * 50)
        
        total_clusters = len(problem_pods)
        clusters_with_problems = sum(1 for pods in problem_pods.values() if pods)
        total_problem_pods = sum(len(pods) for pods in problem_pods.values())
        
        # 显示摘要信息
        summary = Text()
        summary.append("\n摘要信息:\n", style="bold")
        summary.append(f"检查的集群总数: {total_clusters}\n", style="blue")
        summary.append(f"发现问题的集群数: {clusters_with_problems}\n", style="yellow")
        summary.append(f"问题Pod总数: {total_problem_pods}\n", style="red")
        console.print(Panel(summary, title="检查结果摘要", border_style="blue"))
        
        # 显示详细信息
        for cluster_name, pods in problem_pods.items():
            panel_title = f"集群: {cluster_name}"
            if pods:
                table = create_pod_table(pods)
                console.print(Panel(table, title=panel_title, border_style="red"))
            else:
                status_text = Text("\n✓ 未发现异常Pod\n", style="green")
                console.print(Panel(status_text, title=panel_title, border_style="green"))
                
    except Exception as e:
        logger.error(f"列出Pod时发生错误: {str(e)}")
        console.print(f"\n[bold red]错误:[/bold red] {str(e)}")
        raise typer.Exit(1)

@app.command()
def clean_pods(
    namespace: Optional[str] = typer.Option(None, "--namespace", "-n", help="指定命名空间"),
    dry_run: bool = typer.Option(False, "--dry-run", help="试运行模式，不实际删除Pod"),
    kubeconfig_dir: Optional[str] = typer.Option(None, "--kubeconfig-dir", "-k", help="指定kubeconfig目录路径"),
):
    """删除所有集群中状态为Error或Unknown的Pod"""
    # 检查kubeconfig目录是否存在且不为空
    if kubeconfig_dir:
        os.environ['KUBECONFIG_DIR'] = kubeconfig_dir
        
    current_kubeconfig_dir = get_kubeconfig_dir()
    if not os.path.exists(current_kubeconfig_dir):
        console.print(f"\n[bold red]错误: kubeconfig目录不存在: {current_kubeconfig_dir}[/bold red]")
        return
        
    try:
        manager = ClusterManager()
            
        # 检查目录中是否有kubeconfig文件
        kubeconfig_files = [f for f in os.listdir(current_kubeconfig_dir) 
                          if f.endswith(('.yaml', '.yml')) or f.startswith(('k8s', 'K8S'))]
        if not kubeconfig_files:
            console.print(f"\n[bold yellow]警告: 目录 {current_kubeconfig_dir} 中没有找到k8s kubeconfig文件[/bold yellow]")
            return
            
        # 首先显示要删除的Pod
        problem_pods = manager.list_problem_pods(namespace)
        total_pods = sum(len(pods) for pods in problem_pods.values())
        
        if total_pods == 0:
            console.print("[bold green]没有发现需要清理的Pod[/bold green]")
            return
            
        console.print(f"\n[bold yellow]发现 {total_pods} 个问题Pod需要清理:[/bold yellow]")
        for cluster_name, pods in problem_pods.items():
            if pods:
                console.print(f"\n[bold blue]集群: {cluster_name}[/bold blue]")
                table = create_pod_table(pods)
                console.print(table)
        
        # 如果不是试运行，请求确认
        if not dry_run:
            confirm = typer.confirm("\n确定要删除这些Pod吗?")
            if not confirm:
                console.print("[bold yellow]操作已取消[/bold yellow]")
                return
        
        # 执行删除操作
        stats = manager.delete_problem_pods(namespace, dry_run)
        
        # 显示结果
        console.print("\n[bold blue]清理结果:[/bold blue]")
        for cluster_name, result in stats.items():
            status = "[bold green]成功[/bold green]" if result['failed'] == 0 else "[bold red]部分失败[/bold red]"
            console.print(f"集群 {cluster_name}: {status}")
            console.print(f"  总计: {result['total']}")
            console.print(f"  成功: {result['success']}")
            console.print(f"  失败: {result['failed']}")
            
    except Exception as e:
        logger.error(f"清理Pod时发生错误: {str(e)}")
        raise typer.Exit(1)

@app.command()
def cluster_info(
    kubeconfig_dir: Optional[str] = typer.Option(None, "--kubeconfig-dir", "-k", help="指定kubeconfig目录路径"),
):
    """显示所有集群的Kubernetes版本和API地址信息"""
    # 检查kubeconfig目录是否存在且不为空
    if kubeconfig_dir:
        os.environ['KUBECONFIG_DIR'] = kubeconfig_dir
        
    current_kubeconfig_dir = get_kubeconfig_dir()
    if not os.path.exists(current_kubeconfig_dir):
        console.print(f"\n[bold red]错误: kubeconfig目录不存在: {current_kubeconfig_dir}[/bold red]")
        return
        
    try:
        manager = ClusterManager()
            
        # 检查目录中是否有kubeconfig文件
        kubeconfig_files = [f for f in os.listdir(current_kubeconfig_dir) 
                          if f.endswith(('.yaml', '.yml')) or f.startswith(('k8s', 'K8S'))]
        if not kubeconfig_files:
            console.print(f"\n[bold yellow]警告: 目录 {current_kubeconfig_dir} 中没有找到k8s kubeconfig文件[/bold yellow]")
            return
            
        cluster_info = manager.get_cluster_info()
        
        if not cluster_info:
            console.print("[bold yellow]没有找到集群信息[/bold yellow]")
            return
            
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("集群名称")
        table.add_column("Kubernetes版本")
        table.add_column("API服务器地址")
        table.add_column("构建日期")
        table.add_column("平台")
        
        for cluster_name, info in cluster_info.items():
            table.add_row(
                cluster_name,
                info.get('version', 'N/A'),
                info.get('api_server', 'N/A'),
                info.get('build_date', 'N/A'),
                info.get('platform', 'N/A')
            )
        
        console.print("\n[bold blue]集群信息:[/bold blue]")
        console.print(table)
        
    except Exception as e:
        logger.error(f"获取集群信息时发生错误: {str(e)}")
        raise typer.Exit(1)

def main():
    try:
        app(sys.argv[1:] if len(sys.argv) > 1 else ['--help'])
    except typer.Exit:
        raise
    except typer.BadParameter as e:
        # 参数错误时显示帮助
        console.print(f"\n[bold red]错误: {str(e)}[/bold red]")
        console.print("\n使用帮助:")
        app(['--help'])
    except Exception as e:
        # 捕获所有其他异常，显示帮助信息
        console.print("\n[bold red]错误: 无效的参数或命令[/bold red]")
        console.print("\n使用帮助:")
        app(['--help']) 