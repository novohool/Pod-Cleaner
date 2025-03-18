import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).parent.parent.parent

def get_kubeconfig_dir() -> str:
    """
    获取kubeconfig目录路径，优先使用环境变量KUBECONFIG_DIR，
    如果未设置则使用默认值
    """
    return os.environ.get('KUBECONFIG_DIR', os.path.join(BASE_DIR, "kubeconfig"))

# kubeconfig文件目录
KUBECONFIG_DIR = get_kubeconfig_dir()

# 日志配置
LOG_DIR = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "pod_cleaner.log")

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Pod状态
POD_ERROR_STATES = ["Error", "Unknown"]

# 批处理大小
BATCH_SIZE = 50 