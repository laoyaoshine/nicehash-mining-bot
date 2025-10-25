# 缓存和并发工具模块
# 提供缓存、并发请求、重试等功能

import time
import logging
import asyncio
import aiohttp
import threading
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from functools import wraps
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class TTLCache:
    """带TTL的缓存"""
    
    def __init__(self, default_ttl: int = 60):
        self.default_ttl = default_ttl
        self._cache = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        with self._lock:
            if key in self._cache:
                value, expire_time = self._cache[key]
                if time.time() < expire_time:
                    return value
                else:
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        with self._lock:
            ttl = ttl or self.default_ttl
            expire_time = time.time() + ttl
            self._cache[key] = (value, expire_time)
    
    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self) -> None:
        """清理过期缓存"""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key for key, (_, expire_time) in self._cache.items()
                if current_time >= expire_time
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)

class RetryManager:
    """重试管理器"""
    
    def __init__(self, max_attempts: int = 3, backoff_factor: float = 2.0):
        self.max_attempts = max_attempts
        self.backoff_factor = backoff_factor
    
    def retry_with_backoff(self, func: Callable, *args, **kwargs) -> Any:
        """带指数退避的重试"""
        last_exception = None
        
        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    wait_time = self.backoff_factor ** attempt
                    logger.warning(f"重试 {attempt + 1}/{self.max_attempts}: {e}, 等待 {wait_time:.1f}秒")
                    time.sleep(wait_time)
                else:
                    logger.error(f"重试失败，已达到最大尝试次数: {e}")
        
        raise last_exception

class ConcurrentFetcher:
    """并发数据获取器"""
    
    def __init__(self, max_workers: int = 3, timeout: int = 30):
        self.max_workers = max_workers
        self.timeout = timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def fetch_market_data(self, session: requests.Session, headers: Dict[str, str], 
                         api_url: str) -> Optional[Dict[str, float]]:
        """获取市场价格数据"""
        try:
            response = session.get(
                f'{api_url}/public/orders/active',
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            prices = {}
            
            for order in data.get('list', []):
                algorithm = order.get('algorithm')
                price = float(order.get('price', 0))
                
                if algorithm and price > 0:
                    if algorithm not in prices or price < prices[algorithm]:
                        prices[algorithm] = price
            
            return prices
            
        except Exception as e:
            logger.error(f"获取市场价格失败: {e}")
            return None
    
    def fetch_nicehash_fees(self, session: requests.Session, headers: Dict[str, str], 
                           api_url: str) -> Optional[Dict[str, float]]:
        """获取NiceHash费率数据"""
        try:
            response = session.get(
                f'{api_url}/public/stats/global/current',
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            fees = {}
            
            for algorithm_data in data.get('algorithms', []):
                algorithm = algorithm_data.get('algorithm')
                if algorithm:
                    fee_rate = algorithm_data.get('fee', 0.02)
                    fees[algorithm] = float(fee_rate)
            
            return fees
            
        except Exception as e:
            logger.error(f"获取NiceHash费率失败: {e}")
            return None
    
    def fetch_pool_profits(self, session: requests.Session, pool_config: Dict[str, str]) -> Optional[Dict[str, float]]:
        """获取矿池收益数据"""
        try:
            # 这里需要根据实际矿池API调整
            pool_url = pool_config.get('pool_url', 'https://api.miningpool.com')
            pool_api_key = pool_config.get('pool_api_key', '')
            
            headers = {
                'Authorization': f'Bearer {pool_api_key}',
                'Content-Type': 'application/json'
            }
            
            response = session.get(
                f'{pool_url}/profitability',
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析收益数据（需要根据实际API响应格式调整）
            for algorithm, profit_data in data.items():
                if isinstance(profit_data, dict) and 'daily_profit' in profit_data:
                    profitability[algorithm] = float(profit_data['daily_profit'])
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取矿池收益失败: {e}")
            # 返回模拟数据用于测试
            return {
                'SHA256': 0.002,
                'Scrypt': 0.0015,
                'Ethash': 0.003
            }
    
    def fetch_all_data_concurrent(self, session: requests.Session, headers: Dict[str, str], 
                                api_url: str, pool_config: Dict[str, str]) -> Dict[str, Any]:
        """并发获取所有数据"""
        results = {
            'market_prices': None,
            'nicehash_fees': None,
            'pool_profits': None
        }
        
        # 创建任务
        tasks = [
            self.executor.submit(self.fetch_market_data, session, headers, api_url),
            self.executor.submit(self.fetch_nicehash_fees, session, headers, api_url),
            self.executor.submit(self.fetch_pool_profits, session, pool_config)
        ]
        
        # 等待所有任务完成
        for i, task in enumerate(as_completed(tasks, timeout=self.timeout + 10)):
            try:
                result = task.result()
                if i == 0:
                    results['market_prices'] = result
                elif i == 1:
                    results['nicehash_fees'] = result
                else:
                    results['pool_profits'] = result
            except Exception as e:
                logger.error(f"并发任务失败: {e}")
        
        return results
    
    def close(self):
        """关闭执行器"""
        self.executor.shutdown(wait=True)

def cached_with_ttl(ttl: int):
    """缓存装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 尝试从缓存获取
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"缓存命中: {func.__name__}")
                return cached_result
            
            # 执行函数并缓存结果
            result = func(self, *args, **kwargs)
            self.cache.set(cache_key, result, ttl)
            logger.debug(f"缓存设置: {func.__name__}")
            
            return result
        return wrapper
    return decorator

class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics = {
            'api_calls': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'retry_attempts': 0,
            'avg_response_time': 0.0
        }
        self._lock = threading.Lock()
    
    def record_api_call(self, response_time: float):
        """记录API调用"""
        with self._lock:
            self.metrics['api_calls'] += 1
            # 更新平均响应时间
            total_calls = self.metrics['api_calls']
            current_avg = self.metrics['avg_response_time']
            self.metrics['avg_response_time'] = (
                (current_avg * (total_calls - 1) + response_time) / total_calls
            )
    
    def record_cache_hit(self):
        """记录缓存命中"""
        with self._lock:
            self.metrics['cache_hits'] += 1
    
    def record_cache_miss(self):
        """记录缓存未命中"""
        with self._lock:
            self.metrics['cache_misses'] += 1
    
    def record_retry(self):
        """记录重试"""
        with self._lock:
            self.metrics['retry_attempts'] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        with self._lock:
            metrics = self.metrics.copy()
            total_cache_requests = metrics['cache_hits'] + metrics['cache_misses']
            if total_cache_requests > 0:
                metrics['cache_hit_rate'] = metrics['cache_hits'] / total_cache_requests
            else:
                metrics['cache_hit_rate'] = 0.0
            return metrics
    
    def reset_metrics(self):
        """重置指标"""
        with self._lock:
            self.metrics = {
                'api_calls': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'retry_attempts': 0,
                'avg_response_time': 0.0
            }

# 使用示例
if __name__ == "__main__":
    # 创建缓存
    cache = TTLCache(default_ttl=60)
    
    # 创建重试管理器
    retry_manager = RetryManager(max_attempts=3, backoff_factor=2.0)
    
    # 创建并发获取器
    fetcher = ConcurrentFetcher(max_workers=3, timeout=30)
    
    # 创建性能监控器
    monitor = PerformanceMonitor()
    
    # 测试缓存
    cache.set("test_key", "test_value", ttl=10)
    print(f"缓存值: {cache.get('test_key')}")
    
    # 测试性能指标
    monitor.record_api_call(0.5)
    monitor.record_cache_hit()
    print(f"性能指标: {monitor.get_metrics()}")
    
    # 清理
    fetcher.close()
