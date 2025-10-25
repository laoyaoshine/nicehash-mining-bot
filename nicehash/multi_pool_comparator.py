# 多矿池收益对比模块
# 用于比较不同矿池的收益，选择最优矿池

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import requests
import time

logger = logging.getLogger(__name__)

class MultiPoolComparator:
    """多矿池收益对比器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.pool_apis = {}
        self.pool_profits_history = {}
        self.best_pool_cache = {}
        self.cache_duration = 300  # 5分钟缓存
        
    def initialize_pools(self):
        """初始化所有配置的矿池API"""
        try:
            from pool_api_adapter import PoolAPIFactory
            
            # 主矿池
            main_pool_type = self.config.get('pool_type', 'nicehash')
            if main_pool_type == 'nicehash':
                self.pool_apis['nicehash'] = PoolAPIFactory.create_pool_api(
                    'nicehash',
                    api_key=self.config['nicehash']['api_key'],
                    api_secret=self.config['nicehash']['api_secret'],
                    org_id=self.config['nicehash']['org_id']
                )
            else:
                self.pool_apis[main_pool_type] = PoolAPIFactory.create_pool_api(
                    main_pool_type,
                    api_key=self.config['mining_pools']['pool_api_key'],
                    user_id=self.config['mining_pools']['pool_user_id']
                )
            
            # 辅助矿池
            secondary_pools = self.config.get('secondary_pools', '').split(',')
            for pool_type in secondary_pools:
                pool_type = pool_type.strip()
                if pool_type and pool_type != main_pool_type:
                    try:
                        if pool_type == 'f2pool':
                            self.pool_apis['f2pool'] = PoolAPIFactory.create_pool_api(
                                'f2pool',
                                api_key=self.config['mining_pools']['f2pool_api_key'],
                                user_id=self.config['mining_pools']['f2pool_user_id']
                            )
                        elif pool_type == 'antpool':
                            self.pool_apis['antpool'] = PoolAPIFactory.create_pool_api(
                                'antpool',
                                api_key=self.config['mining_pools']['antpool_api_key'],
                                user_id=self.config['mining_pools']['antpool_user_id']
                            )
                        elif pool_type == 'slushpool':
                            self.pool_apis['slushpool'] = PoolAPIFactory.create_pool_api(
                                'slushpool',
                                api_key=self.config['mining_pools']['slushpool_api_key'],
                                user_id=self.config['mining_pools']['slushpool_user_id']
                            )
                        elif pool_type == 'viabtc':
                            self.pool_apis['viabtc'] = PoolAPIFactory.create_pool_api(
                                'viabtc',
                                api_key=self.config['mining_pools']['viabtc_api_key'],
                                user_id=self.config['mining_pools']['viabtc_user_id']
                            )
                        elif pool_type == 'btc.com':
                            self.pool_apis['btc.com'] = PoolAPIFactory.create_pool_api(
                                'btc.com',
                                api_key=self.config['mining_pools']['btc_com_api_key'],
                                user_id=self.config['mining_pools']['btc_com_user_id']
                            )
                        elif pool_type == 'poolin':
                            self.pool_apis['poolin'] = PoolAPIFactory.create_pool_api(
                                'poolin',
                                api_key=self.config['mining_pools']['poolin_api_key'],
                                user_id=self.config['mining_pools']['poolin_user_id']
                            )
                    except Exception as e:
                        logger.warning(f"初始化矿池 {pool_type} 失败: {e}")
            
            logger.info(f"成功初始化 {len(self.pool_apis)} 个矿池: {list(self.pool_apis.keys())}")
            
        except Exception as e:
            logger.error(f"初始化矿池失败: {e}")
    
    def get_all_pool_profits(self) -> Dict[str, Dict[str, float]]:
        """获取所有矿池的收益数据"""
        all_profits = {}
        
        for pool_name, pool_api in self.pool_apis.items():
            try:
                profits = pool_api.get_profitability()
                if profits:
                    all_profits[pool_name] = profits
                    logger.debug(f"{pool_name} 收益数据: {profits}")
                else:
                    logger.warning(f"{pool_name} 未返回收益数据")
            except Exception as e:
                logger.error(f"获取 {pool_name} 收益失败: {e}")
        
        return all_profits
    
    def find_best_pool_for_algorithm(self, algorithm: str) -> Tuple[str, float]:
        """为特定算法找到最佳矿池（考虑矿池手续费）"""
        try:
            # 检查缓存
            cache_key = f"{algorithm}_{int(time.time() // self.cache_duration)}"
            if cache_key in self.best_pool_cache:
                return self.best_pool_cache[cache_key]
            
            all_profits = self.get_all_pool_profits()
            
            best_pool = None
            best_net_profit = 0.0
            
            # 模拟租赁价格（实际应该从NiceHash获取）
            rental_price = 0.001  # 示例价格
            
            for pool_name, profits in all_profits.items():
                if algorithm in profits:
                    pool_profit = profits[algorithm]
                    
                    # 计算净盈利（包含矿池手续费）
                    net_profit = self.calculate_net_profit_with_pool_fee(
                        algorithm, rental_price, pool_profit, pool_name
                    )
                    
                    if net_profit > best_net_profit:
                        best_net_profit = net_profit
                        best_pool = pool_name
            
            if best_pool:
                result = (best_pool, best_net_profit)
                self.best_pool_cache[cache_key] = result
                logger.info(f"{algorithm} 最佳矿池: {best_pool}, 净盈利: {best_net_profit}")
                return result
            else:
                logger.warning(f"未找到 {algorithm} 的矿池收益数据")
                return ("", 0.0)
                
        except Exception as e:
            logger.error(f"查找最佳矿池失败: {e}")
            return ("", 0.0)
    
    def calculate_net_profit_with_pool_fee(self, algorithm: str, rental_price: float, 
                                         pool_profit: float, pool_name: str, 
                                         nicehash_fee_rate: float = None) -> float:
        """计算包含矿池手续费的净盈利（支持动态NiceHash费率）"""
        try:
            # NiceHash手续费率（动态获取或使用默认值）
            if nicehash_fee_rate is None:
                nicehash_fee_rate = 0.02  # 默认2%
            
            # NiceHash手续费
            rental_cost = rental_price * (1 + nicehash_fee_rate)
            
            # 矿池手续费
            pool_fee_rates = {
                'nicehash': 0.02,    # 2%
                'f2pool': 0.025,     # 2.5%
                'antpool': 0.025,    # 2.5%
                'slushpool': 0.02,   # 2%
                'viabtc': 0.025,     # 2.5%
                'btc.com': 0.025,    # 2.5%
                'poolin': 0.02       # 2%
            }
            
            try:
                pool_key = pool_name.lower() if isinstance(pool_name, str) else 'nicehash'
            except Exception:
                pool_key = 'nicehash'
            pool_fee_rate = pool_fee_rates.get(pool_key, 0.025)
            pool_fee_cost = pool_profit * pool_fee_rate
            
            # 净盈利 = 矿池收益 - 租赁成本 - 矿池手续费
            net_profit = pool_profit - rental_cost - pool_fee_cost
            
            return net_profit
            
        except Exception as e:
            logger.error(f"计算净盈利失败: {e}")
            return 0.0
    
    def get_optimal_pool_strategy(self, algorithms: List[str]) -> Dict[str, Tuple[str, float]]:
        """获取所有算法的最优矿池策略"""
        strategy = {}
        
        for algorithm in algorithms:
            best_pool, best_profit = self.find_best_pool_for_algorithm(algorithm)
            if best_pool:
                strategy[algorithm] = (best_pool, best_profit)
        
        return strategy
    
    def compare_pool_performance(self, algorithm: str) -> Dict[str, float]:
        """比较各矿池在特定算法上的表现"""
        all_profits = self.get_all_pool_profits()
        performance = {}
        
        for pool_name, profits in all_profits.items():
            if algorithm in profits:
                performance[pool_name] = profits[algorithm]
        
        # 按收益排序
        sorted_performance = dict(sorted(performance.items(), key=lambda x: x[1], reverse=True))
        
        logger.info(f"{algorithm} 矿池收益排名: {sorted_performance}")
        return sorted_performance
    
    def get_pool_reliability_score(self, pool_name: str) -> float:
        """计算矿池可靠性评分"""
        try:
            if pool_name not in self.pool_profits_history:
                return 50.0  # 默认中等可靠性
            
            history = self.pool_profits_history[pool_name]
            if len(history) < 10:
                return 50.0  # 数据不足
            
            # 计算成功率（非零收益的比例）
            success_rate = sum(1 for profit in history if profit > 0) / len(history)
            
            # 计算稳定性（收益波动率）
            import numpy as np
            profits_array = np.array(history)
            stability = 1.0 - (np.std(profits_array) / np.mean(profits_array)) if np.mean(profits_array) > 0 else 0.0
            
            # 综合评分
            reliability_score = (success_rate * 0.6 + stability * 0.4) * 100
            
            return min(reliability_score, 100.0)
            
        except Exception as e:
            logger.error(f"计算矿池可靠性评分失败: {e}")
            return 50.0
    
    def update_pool_history(self, pool_name: str, algorithm: str, profit: float):
        """更新矿池历史数据"""
        if pool_name not in self.pool_profits_history:
            self.pool_profits_history[pool_name] = []
        
        self.pool_profits_history[pool_name].append(profit)
        
        # 保持历史记录在合理范围内
        if len(self.pool_profits_history[pool_name]) > 1000:
            self.pool_profits_history[pool_name] = self.pool_profits_history[pool_name][-500:]
    
    def get_recommended_pools(self, algorithm: str, min_profit_threshold: float = 0.001) -> List[Tuple[str, float, float]]:
        """获取推荐矿池列表（包含收益和可靠性评分）"""
        try:
            all_profits = self.get_all_pool_profits()
            recommendations = []
            
            for pool_name, profits in all_profits.items():
                if algorithm in profits and profits[algorithm] >= min_profit_threshold:
                    profit = profits[algorithm]
                    reliability = self.get_pool_reliability_score(pool_name)
                    recommendations.append((pool_name, profit, reliability))
            
            # 按综合评分排序（收益权重70%，可靠性权重30%）
            recommendations.sort(key=lambda x: x[1] * 0.7 + x[2] * 0.3, reverse=True)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"获取推荐矿池失败: {e}")
            return []
    
    def generate_pool_report(self) -> str:
        """生成矿池对比报告"""
        try:
            report = []
            report.append("=" * 60)
            report.append("矿池收益对比报告")
            report.append("=" * 60)
            report.append(f"生成时间: {datetime.now()}")
            report.append("")
            
            all_profits = self.get_all_pool_profits()
            
            # 获取所有算法
            all_algorithms = set()
            for profits in all_profits.values():
                all_algorithms.update(profits.keys())
            
            for algorithm in sorted(all_algorithms):
                report.append(f"算法: {algorithm}")
                report.append("-" * 40)
                
                performance = self.compare_pool_performance(algorithm)
                for pool_name, profit in performance.items():
                    reliability = self.get_pool_reliability_score(pool_name)
                    report.append(f"  {pool_name}: {profit:.6f} BTC (可靠性: {reliability:.1f}%)")
                
                report.append("")
            
            return "\n".join(report)
            
        except Exception as e:
            logger.error(f"生成矿池报告失败: {e}")
            return f"生成报告失败: {e}"

# 使用示例
if __name__ == "__main__":
    # 模拟配置
    config = {
        'pool_type': 'nicehash',
        'nicehash': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'org_id': 'test_org'
        },
        'mining_pools': {
            'pool_api_key': 'test_key',
            'pool_user_id': 'test_user',
            'f2pool_api_key': 'test_key',
            'f2pool_user_id': 'test_user',
            'antpool_api_key': 'test_key',
            'antpool_user_id': 'test_user'
        },
        'secondary_pools': 'f2pool,antpool'
    }
    
    # 创建对比器
    comparator = MultiPoolComparator(config)
    comparator.initialize_pools()
    
    # 获取最佳矿池策略
    algorithms = ['SHA256', 'Scrypt', 'Ethash']
    strategy = comparator.get_optimal_pool_strategy(algorithms)
    
    print("最佳矿池策略:")
    for algorithm, (pool, profit) in strategy.items():
        print(f"  {algorithm}: {pool} ({profit:.6f} BTC)")
    
    # 生成报告
    report = comparator.generate_pool_report()
    print("\n" + report)
