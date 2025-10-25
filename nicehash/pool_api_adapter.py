# 矿池API适配器
# 用于适配不同矿池的API接口

import requests
import json
import logging
from typing import Dict, List, Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class MiningPoolAPI(ABC):
    """矿池API抽象基类"""
    
    @abstractmethod
    def get_profitability(self) -> Dict[str, float]:
        """获取各算法的收益数据"""
        pass
    
    @abstractmethod
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        pass
    
    @abstractmethod
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        pass

class NiceHashPoolAPI(MiningPoolAPI):
    """NiceHash矿池API适配器"""
    
    def __init__(self, api_key: str, api_secret: str, org_id: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.org_id = org_id
        self.base_url = "https://api2.nicehash.com/main/api/v2"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'X-Auth': f'{self.api_key}:{self.api_secret}',
            'X-Organization-Id': self.org_id,
            'Content-Type': 'application/json'
        }
    
    def get_profitability(self) -> Dict[str, float]:
        """获取NiceHash各算法收益"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/public/stats/global/current',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析不同算法的收益数据
            for algorithm_data in data.get('algorithms', []):
                algorithm = algorithm_data.get('algorithm')
                if algorithm:
                    # 计算收益（需要根据实际API响应调整）
                    profitability[algorithm] = float(algorithm_data.get('profitability', 0))
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取NiceHash收益失败: {e}")
            return {}
    
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/mining/rigs2',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取矿工统计失败: {e}")
            return {}
    
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/public/stats/global/current',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取矿池统计失败: {e}")
            return {}

class F2PoolAPI(MiningPoolAPI):
    """F2Pool矿池API适配器"""
    
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://api.f2pool.com"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_profitability(self) -> Dict[str, float]:
        """获取F2Pool各算法收益"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/profitability',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析F2Pool的收益数据格式
            for coin_data in data.get('coins', []):
                algorithm = coin_data.get('algorithm')
                if algorithm:
                    profitability[algorithm] = float(coin_data.get('daily_profit', 0))
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取F2Pool收益失败: {e}")
            return {}
    
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/miner/{self.user_id}/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取F2Pool矿工统计失败: {e}")
            return {}
    
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/pool/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取F2Pool矿池统计失败: {e}")
            return {}

class AntPoolAPI(MiningPoolAPI):
    """AntPool矿池API适配器"""
    
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://antpool.com/api"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_profitability(self) -> Dict[str, float]:
        """获取AntPool各算法收益"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/profitability',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析AntPool的收益数据格式
            for algorithm_data in data.get('algorithms', []):
                algorithm = algorithm_data.get('name')
                if algorithm:
                    profitability[algorithm] = float(algorithm_data.get('profit', 0))
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取AntPool收益失败: {e}")
            return {}
    
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/miner/{self.user_id}/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取AntPool矿工统计失败: {e}")
            return {}
    
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/pool/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取AntPool矿池统计失败: {e}")
            return {}

class SlushPoolAPI(MiningPoolAPI):
    """SlushPool矿池API适配器"""
    
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://slushpool.com/api"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_profitability(self) -> Dict[str, float]:
        """获取SlushPool各算法收益"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/profitability',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析SlushPool的收益数据格式
            for algorithm_data in data.get('algorithms', []):
                algorithm = algorithm_data.get('name')
                if algorithm:
                    profitability[algorithm] = float(algorithm_data.get('daily_profit', 0))
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取SlushPool收益失败: {e}")
            return {}
    
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/miner/{self.user_id}/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取SlushPool矿工统计失败: {e}")
            return {}
    
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/pool/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取SlushPool矿池统计失败: {e}")
            return {}

class ViaBTCPoolAPI(MiningPoolAPI):
    """ViaBTC矿池API适配器"""
    
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://pool.viabtc.com/api"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_profitability(self) -> Dict[str, float]:
        """获取ViaBTC各算法收益"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/profitability',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析ViaBTC的收益数据格式
            for coin_data in data.get('coins', []):
                algorithm = coin_data.get('algorithm')
                if algorithm:
                    profitability[algorithm] = float(coin_data.get('daily_profit', 0))
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取ViaBTC收益失败: {e}")
            return {}
    
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/miner/{self.user_id}/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取ViaBTC矿工统计失败: {e}")
            return {}
    
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/pool/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取ViaBTC矿池统计失败: {e}")
            return {}

class BTCComPoolAPI(MiningPoolAPI):
    """BTC.com矿池API适配器"""
    
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://pool.btc.com/api"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_profitability(self) -> Dict[str, float]:
        """获取BTC.com各算法收益"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/profitability',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析BTC.com的收益数据格式
            for algorithm_data in data.get('algorithms', []):
                algorithm = algorithm_data.get('name')
                if algorithm:
                    profitability[algorithm] = float(algorithm_data.get('profit', 0))
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取BTC.com收益失败: {e}")
            return {}
    
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/miner/{self.user_id}/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取BTC.com矿工统计失败: {e}")
            return {}
    
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/pool/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取BTC.com矿池统计失败: {e}")
            return {}

class PoolinPoolAPI(MiningPoolAPI):
    """Poolin矿池API适配器"""
    
    def __init__(self, api_key: str, user_id: str):
        self.api_key = api_key
        self.user_id = user_id
        self.base_url = "https://api.poolin.com"
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_profitability(self) -> Dict[str, float]:
        """获取Poolin各算法收益"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/profitability',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            profitability = {}
            
            # 解析Poolin的收益数据格式
            for algorithm_data in data.get('algorithms', []):
                algorithm = algorithm_data.get('name')
                if algorithm:
                    profitability[algorithm] = float(algorithm_data.get('daily_profit', 0))
            
            return profitability
            
        except Exception as e:
            logger.error(f"获取Poolin收益失败: {e}")
            return {}
    
    def get_miner_stats(self) -> Dict:
        """获取矿工统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/miner/{self.user_id}/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取Poolin矿工统计失败: {e}")
            return {}
    
    def get_pool_stats(self) -> Dict:
        """获取矿池统计信息"""
        try:
            headers = self._get_headers()
            response = requests.get(
                f'{self.base_url}/pool/stats',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"获取Poolin矿池统计失败: {e}")
            return {}

class PoolAPIFactory:
    """矿池API工厂类"""
    
    @staticmethod
    def create_pool_api(pool_type: str, **kwargs) -> MiningPoolAPI:
        """创建矿池API实例"""
        pool_type_lower = pool_type.lower()
        
        if pool_type_lower == 'nicehash':
            return NiceHashPoolAPI(
                api_key=kwargs['api_key'],
                api_secret=kwargs['api_secret'],
                org_id=kwargs['org_id']
            )
        elif pool_type_lower == 'f2pool':
            return F2PoolAPI(
                api_key=kwargs['api_key'],
                user_id=kwargs['user_id']
            )
        elif pool_type_lower == 'antpool':
            return AntPoolAPI(
                api_key=kwargs['api_key'],
                user_id=kwargs['user_id']
            )
        elif pool_type_lower == 'slushpool':
            return SlushPoolAPI(
                api_key=kwargs['api_key'],
                user_id=kwargs['user_id']
            )
        elif pool_type_lower == 'viabtc':
            return ViaBTCPoolAPI(
                api_key=kwargs['api_key'],
                user_id=kwargs['user_id']
            )
        elif pool_type_lower == 'btc.com':
            return BTCComPoolAPI(
                api_key=kwargs['api_key'],
                user_id=kwargs['user_id']
            )
        elif pool_type_lower == 'poolin':
            return PoolinPoolAPI(
                api_key=kwargs['api_key'],
                user_id=kwargs['user_id']
            )
        else:
            raise ValueError(f"不支持的矿池类型: {pool_type}")
    
    @staticmethod
    def get_supported_pools() -> List[str]:
        """获取支持的矿池列表"""
        return [
            'nicehash',
            'f2pool', 
            'antpool',
            'slushpool',
            'viabtc',
            'btc.com',
            'poolin'
        ]

# 使用示例
if __name__ == "__main__":
    # 创建NiceHash API实例
    nicehash_api = PoolAPIFactory.create_pool_api(
        'nicehash',
        api_key='your_api_key',
        api_secret='your_api_secret',
        org_id='your_org_id'
    )
    
    # 获取收益数据
    profitability = nicehash_api.get_profitability()
    print(f"NiceHash收益数据: {profitability}")
    
    # 创建F2Pool API实例
    f2pool_api = PoolAPIFactory.create_pool_api(
        'f2pool',
        api_key='your_api_key',
        user_id='your_user_id'
    )
    
    # 获取收益数据
    profitability = f2pool_api.get_profitability()
    print(f"F2Pool收益数据: {profitability}")
