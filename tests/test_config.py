import unittest
import os
from pathlib import Path
from src.pod_cleaner.config import BASE_DIR, KUBECONFIG_DIR, LOG_DIR

class TestConfig(unittest.TestCase):
    def test_base_dir(self):
        """测试BASE_DIR是否是有效的目录"""
        self.assertTrue(os.path.isdir(BASE_DIR))
        
    def test_kubeconfig_dir(self):
        """测试KUBECONFIG_DIR是否是预期的路径"""
        expected_path = os.path.join(BASE_DIR, "kubeconfig")
        self.assertEqual(KUBECONFIG_DIR, expected_path)
        
    def test_log_dir(self):
        """测试LOG_DIR是否是预期的路径"""
        expected_path = os.path.join(BASE_DIR, "logs")
        self.assertEqual(LOG_DIR, expected_path)
        
if __name__ == "__main__":
    unittest.main() 