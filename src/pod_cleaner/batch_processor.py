from typing import List, Dict, Any, Callable, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import BATCH_SIZE
from .logger import setup_logger

T = TypeVar('T')
R = TypeVar('R')

logger = setup_logger(__name__)

class BatchProcessor(Generic[T, R]):
    """
    批量处理器，用于高效处理大量数据
    
    可以将大量数据分批处理，并支持并行执行
    """
    
    def __init__(self, items: List[T], batch_size: int = BATCH_SIZE, max_workers: int = 5):
        """
        初始化批量处理器
        
        Args:
            items: 要处理的项目列表
            batch_size: 每批处理的项目数量
            max_workers: 最大并行工作线程数
        """
        self.items = items
        self.batch_size = batch_size
        self.max_workers = max_workers
        
    def _create_batches(self) -> List[List[T]]:
        """
        将项目列表分割成批次
        
        Returns:
            List[List[T]]: 批次列表
        """
        batches = []
        for i in range(0, len(self.items), self.batch_size):
            batches.append(self.items[i:i + self.batch_size])
        return batches
        
    def process(self, processor_func: Callable[[List[T]], Dict[str, R]]) -> Dict[str, R]:
        """
        处理所有项目
        
        Args:
            processor_func: 处理函数，接受一个批次并返回结果字典
            
        Returns:
            Dict[str, R]: 处理结果
        """
        batches = self._create_batches()
        logger.info(f"将 {len(self.items)} 个项目分为 {len(batches)} 个批次进行处理")
        
        results: Dict[str, R] = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_batch = {
                executor.submit(processor_func, batch): batch
                for batch in batches
            }
            
            for future in as_completed(future_to_batch):
                try:
                    batch_result = future.result()
                    # 合并结果
                    for key, value in batch_result.items():
                        if key in results:
                            if isinstance(value, dict) and isinstance(results[key], dict):
                                # 如果是字典，合并它们
                                for k, v in value.items():
                                    if k in results[key]:
                                        if isinstance(v, int) and isinstance(results[key][k], int):
                                            results[key][k] += v
                                    else:
                                        results[key][k] = v
                            elif isinstance(value, list) and isinstance(results[key], list):
                                # 如果是列表，扩展它
                                results[key].extend(value)
                        else:
                            results[key] = value
                except Exception as e:
                    logger.error(f"处理批次时发生错误: {str(e)}")
        
        return results 