# 盈利计算和风险管理模块

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class ProfitCalculator:
    """盈利计算器 - 专门用于租赁算力挖矿"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 租赁算力成本系数（只包含手续费，不包含电费）
        self.cost_factors = {
            'SHA256': 1.02,    # 2%手续费
            'Scrypt': 1.02,    # 2%手续费
            'Ethash': 1.02,    # 2%手续费
            'X11': 1.02,       # 2%手续费
            'CryptoNight': 1.02,  # 2%手续费
            'Equihash': 1.02,  # 2%手续费
            'Lyra2REv2': 1.02, # 2%手续费
            'Blake2s': 1.02,   # 2%手续费
            'Blake14r': 1.02,  # 2%手续费
            'DaggerHashimoto': 1.02  # 2%手续费
        }
        
        # NiceHash手续费率（根据官方文档）
        self.nicehash_fees = {
            'SHA256': 0.02,    # 2%
            'Scrypt': 0.02,    # 2%
            'Ethash': 0.02,    # 2%
            'X11': 0.02,       # 2%
            'CryptoNight': 0.02,  # 2%
            'Equihash': 0.02,  # 2%
            'Lyra2REv2': 0.02, # 2%
            'Blake2s': 0.02,   # 2%
            'Blake14r': 0.02,  # 2%
            'DaggerHashimoto': 0.02  # 2%
        }
        
        # 矿池手续费率（各矿池的典型手续费）
        self.pool_fees = {
            'nicehash': 0.02,    # 2%
            'f2pool': 0.025,     # 2.5%
            'antpool': 0.025,     # 2.5%
            'slushpool': 0.02,   # 2%
            'viabtc': 0.025,     # 2.5%
            'btc.com': 0.025,    # 2.5%
            'poolin': 0.02       # 2%
        }
    
    def calculate_net_profit(self, algorithm: str, rental_price: float, 
                           pool_profit: float, pool_name: str = 'nicehash', 
                           nicehash_fee_rate: float = None, hashrate: float = 1.0) -> float:
        """计算净盈利 - 租赁算力模式（包含矿池手续费和动态NiceHash费率）"""
        try:
            # NiceHash手续费率（动态获取或使用默认值）
            if nicehash_fee_rate is None:
                nicehash_fee_rate = self.nicehash_fees.get(algorithm, 0.02)
            
            # 租赁算力总成本（包含NiceHash手续费）
            rental_cost = rental_price * (1 + nicehash_fee_rate)
            
            # 矿池手续费
            try:
                pool_key = pool_name.lower() if isinstance(pool_name, str) else 'nicehash'
            except Exception:
                pool_key = 'nicehash'
            pool_fee_rate = self.pool_fees.get(pool_key, 0.025)  # 默认2.5%
            pool_fee_cost = pool_profit * pool_fee_rate
            
            # 净盈利 = 矿池收益 - 租赁成本 - 矿池手续费
            net_profit = pool_profit - rental_cost - pool_fee_cost
            
            logger.debug(f"{algorithm} ({pool_name}): 租赁价格={rental_price}, NiceHash费率={nicehash_fee_rate:.3f}, "
                        f"矿池收益={pool_profit}, 租赁成本={rental_cost}, 矿池手续费={pool_fee_cost}, 净盈利={net_profit}")
            
            return net_profit
            
        except Exception as e:
            logger.error(f"计算盈利失败: {e}")
            return 0.0
    
    def calculate_profit_margin(self, algorithm: str, rental_price: float, 
                              pool_profit: float, pool_name: str = 'nicehash', 
                              nicehash_fee_rate: float = None) -> float:
        """计算利润率"""
        try:
            net_profit = self.calculate_net_profit(algorithm, rental_price, pool_profit, pool_name, nicehash_fee_rate)
            if pool_profit > 0:
                return (net_profit / pool_profit) * 100
            return 0.0
        except Exception as e:
            logger.error(f"计算利润率失败: {e}")
            return 0.0
    
    def get_optimal_order_amount(self, algorithm: str, rental_price: float, 
                               pool_profit: float, max_amount: float, pool_name: str = 'nicehash',
                               nicehash_fee_rate: float = None) -> float:
        """计算最优订单金额 - 租赁算力模式"""
        try:
            net_profit = self.calculate_net_profit(algorithm, rental_price, pool_profit, pool_name, nicehash_fee_rate)
            
            if net_profit <= 0:
                return 0.0
            
            # 根据盈利程度调整订单金额（租赁算力模式更激进）
            profit_ratio = net_profit / pool_profit if pool_profit > 0 else 0
            
            if profit_ratio > 0.15:  # 利润率超过15%（租赁算力门槛更低）
                return max_amount
            elif profit_ratio > 0.08:  # 利润率8-15%
                return max_amount * 0.8
            elif profit_ratio > 0.03:  # 利润率3-8%
                return max_amount * 0.5
            else:  # 利润率低于3%
                return max_amount * 0.2
                
        except Exception as e:
            logger.error(f"计算最优订单金额失败: {e}")
            return 0.0
    
    def calculate_break_even_price(self, algorithm: str, pool_profit: float, 
                                 pool_name: str = 'nicehash', nicehash_fee_rate: float = None) -> float:
        """计算盈亏平衡价格（包含矿池手续费和动态NiceHash费率）"""
        try:
            # NiceHash手续费率
            if nicehash_fee_rate is None:
                nicehash_fee_rate = self.nicehash_fees.get(algorithm, 0.02)
            
            # 矿池手续费
            try:
                pool_key = pool_name.lower() if isinstance(pool_name, str) else 'nicehash'
            except Exception:
                pool_key = 'nicehash'
            pool_fee_rate = self.pool_fees.get(pool_key, 0.025)
            pool_fee_cost = pool_profit * pool_fee_rate
            
            # 扣除矿池手续费后的净收益
            net_pool_profit = pool_profit - pool_fee_cost
            
            # 盈亏平衡价格 = 净矿池收益 / (1 + NiceHash费率)
            break_even_price = net_pool_profit / (1 + nicehash_fee_rate)
            
            logger.debug(f"{algorithm} ({pool_name}): NiceHash费率={nicehash_fee_rate:.3f}, 盈亏平衡价格={break_even_price}")
            return break_even_price
            
        except Exception as e:
            logger.error(f"计算盈亏平衡价格失败: {e}")
            return 0.0
    
    def get_profitability_score(self, algorithm: str, rental_price: float, 
                              pool_profit: float, pool_name: str = 'nicehash',
                              nicehash_fee_rate: float = None) -> float:
        """计算盈利评分 (0-100)"""
        try:
            net_profit = self.calculate_net_profit(algorithm, rental_price, pool_profit, pool_name, nicehash_fee_rate)
            
            if net_profit <= 0:
                return 0.0
            
            # 基于净盈利和矿池收益计算评分
            profit_ratio = net_profit / pool_profit if pool_profit > 0 else 0
            
            # 评分计算：净盈利比例 * 100
            score = min(profit_ratio * 100, 100.0)
            
            return score
            
        except Exception as e:
            logger.error(f"计算盈利评分失败: {e}")
            return 0.0
    
    def get_total_cost_breakdown(self, algorithm: str, rental_price: float, 
                               pool_profit: float, pool_name: str = 'nicehash',
                               nicehash_fee_rate: float = None) -> Dict[str, float]:
        """获取总成本明细（包含动态NiceHash费率）"""
        try:
            # NiceHash手续费率
            if nicehash_fee_rate is None:
                nicehash_fee_rate = self.nicehash_fees.get(algorithm, 0.02)
            
            # 租赁成本
            rental_cost = rental_price * (1 + nicehash_fee_rate)
            nicehash_fee = rental_cost - rental_price
            
            # 矿池手续费
            try:
                pool_key = pool_name.lower() if isinstance(pool_name, str) else 'nicehash'
            except Exception:
                pool_key = 'nicehash'
            pool_fee_rate = self.pool_fees.get(pool_key, 0.025)
            pool_fee_cost = pool_profit * pool_fee_rate
            
            # 总成本
            total_cost = rental_cost + pool_fee_cost
            
            return {
                'rental_price': rental_price,
                'nicehash_fee_rate': nicehash_fee_rate,
                'nicehash_fee': nicehash_fee,
                'rental_cost': rental_cost,
                'pool_fee_rate': pool_fee_rate,
                'pool_fee_cost': pool_fee_cost,
                'total_cost': total_cost,
                'net_profit': pool_profit - total_cost
            }
            
        except Exception as e:
            logger.error(f"计算成本明细失败: {e}")
            return {}

class RiskManager:
    """风险管理器"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.max_daily_loss = float(config.get('max_daily_loss', 0.01))
        self.stop_loss_threshold = float(config.get('stop_loss_threshold', 0.005))
        self.max_concurrent_orders = int(config.get('max_concurrent_orders', 5))
        
        self.daily_loss = 0.0
        self.daily_trades = []
        self.last_reset_date = datetime.now().date()
    
    def reset_daily_stats(self):
        """重置每日统计"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_loss = 0.0
            self.daily_trades = []
            self.last_reset_date = current_date
            logger.info("重置每日统计")
    
    def check_daily_loss_limit(self) -> bool:
        """检查是否超过每日亏损限制"""
        self.reset_daily_stats()
        return self.daily_loss >= self.max_daily_loss
    
    def check_stop_loss(self, current_loss: float) -> bool:
        """检查是否触发止损"""
        return current_loss >= self.stop_loss_threshold
    
    def check_concurrent_orders(self, current_orders: int) -> bool:
        """检查并发订单数量"""
        return current_orders >= self.max_concurrent_orders
    
    def record_trade(self, algorithm: str, amount: float, profit: float):
        """记录交易"""
        trade = {
            'timestamp': datetime.now(),
            'algorithm': algorithm,
            'amount': amount,
            'profit': profit
        }
        self.daily_trades.append(trade)
        
        if profit < 0:
            self.daily_loss += abs(profit)
        
        logger.info(f"记录交易: {algorithm}, 金额: {amount}, 盈利: {profit}")
    
    def get_risk_score(self, algorithm: str, rental_price: float, 
                      pool_profit: float) -> float:
        """计算风险评分 (0-100, 越高风险越大)"""
        try:
            risk_score = 0.0
            
            # 价格波动风险
            if rental_price > pool_profit * 0.8:
                risk_score += 30
            
            # 每日亏损风险
            if self.daily_loss > self.max_daily_loss * 0.5:
                risk_score += 25
            
            # 并发订单风险
            if len(self.daily_trades) > self.max_concurrent_orders * 0.8:
                risk_score += 20
            
            # 算法特定风险
            if algorithm in ['CryptoNight', 'X11']:  # 相对不稳定的算法
                risk_score += 15
            
            # 时间风险（夜间交易风险更高）
            current_hour = datetime.now().hour
            if current_hour < 6 or current_hour > 22:
                risk_score += 10
            
            return min(risk_score, 100.0)
            
        except Exception as e:
            logger.error(f"计算风险评分失败: {e}")
            return 50.0  # 默认中等风险
    
    def should_proceed_with_trade(self, algorithm: str, rental_price: float, 
                                pool_profit: float, current_orders: int) -> Tuple[bool, str]:
        """判断是否应该进行交易"""
        try:
            # 检查每日亏损限制
            if self.check_daily_loss_limit():
                return False, "超过每日亏损限制"
            
            # 检查并发订单数量
            if self.check_concurrent_orders(current_orders):
                return False, "超过最大并发订单数"
            
            # 检查风险评分
            risk_score = self.get_risk_score(algorithm, rental_price, pool_profit)
            if risk_score > 80:
                return False, f"风险评分过高: {risk_score}"
            
            # 检查止损
            if pool_profit < rental_price:
                return False, "当前价格不盈利"
            
            return True, "风险检查通过"
            
        except Exception as e:
            logger.error(f"风险检查失败: {e}")
            return False, f"风险检查失败: {e}"

class MarketAnalyzer:
    """市场分析器"""
    
    def __init__(self):
        self.price_history = {}
        self.profit_history = {}
        self.volatility_cache = {}
    
    def update_price_history(self, algorithm: str, price: float):
        """更新价格历史"""
        if algorithm not in self.price_history:
            self.price_history[algorithm] = []
        
        self.price_history[algorithm].append({
            'timestamp': datetime.now(),
            'price': price
        })
        
        # 保持最近1000条记录
        if len(self.price_history[algorithm]) > 1000:
            self.price_history[algorithm] = self.price_history[algorithm][-500:]
    
    def update_profit_history(self, algorithm: str, profit: float):
        """更新盈利历史"""
        if algorithm not in self.profit_history:
            self.profit_history[algorithm] = []
        
        self.profit_history[algorithm].append({
            'timestamp': datetime.now(),
            'profit': profit
        })
        
        # 保持最近1000条记录
        if len(self.profit_history[algorithm]) > 1000:
            self.profit_history[algorithm] = self.profit_history[algorithm][-500:]
    
    def calculate_price_volatility(self, algorithm: str, hours: int = 24) -> float:
        """计算价格波动率"""
        try:
            if algorithm not in self.price_history:
                return 0.0
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_prices = [
                entry['price'] for entry in self.price_history[algorithm]
                if entry['timestamp'] > cutoff_time
            ]
            
            if len(recent_prices) < 2:
                return 0.0
            
            prices_array = np.array(recent_prices)
            volatility = np.std(prices_array) / np.mean(prices_array)
            
            return volatility
            
        except Exception as e:
            logger.error(f"计算价格波动率失败: {e}")
            return 0.0
    
    def get_price_trend(self, algorithm: str, hours: int = 6) -> str:
        """获取价格趋势"""
        try:
            if algorithm not in self.price_history:
                return "unknown"
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_prices = [
                entry['price'] for entry in self.price_history[algorithm]
                if entry['timestamp'] > cutoff_time
            ]
            
            if len(recent_prices) < 2:
                return "unknown"
            
            # 简单趋势分析
            first_half = recent_prices[:len(recent_prices)//2]
            second_half = recent_prices[len(recent_prices)//2:]
            
            first_avg = np.mean(first_half)
            second_avg = np.mean(second_half)
            
            if second_avg > first_avg * 1.05:
                return "rising"
            elif second_avg < first_avg * 0.95:
                return "falling"
            else:
                return "stable"
                
        except Exception as e:
            logger.error(f"获取价格趋势失败: {e}")
            return "unknown"
    
    def get_market_sentiment(self, algorithm: str) -> str:
        """获取市场情绪"""
        try:
            volatility = self.calculate_price_volatility(algorithm)
            trend = self.get_price_trend(algorithm)
            
            if volatility > 0.2:
                if trend == "rising":
                    return "bullish_volatile"
                elif trend == "falling":
                    return "bearish_volatile"
                else:
                    return "neutral_volatile"
            else:
                if trend == "rising":
                    return "bullish_stable"
                elif trend == "falling":
                    return "bearish_stable"
                else:
                    return "neutral_stable"
                    
        except Exception as e:
            logger.error(f"获取市场情绪失败: {e}")
            return "unknown"
    
    def get_optimal_timing(self, algorithm: str) -> bool:
        """判断是否为最佳交易时机"""
        try:
            sentiment = self.get_market_sentiment(algorithm)
            volatility = self.calculate_price_volatility(algorithm)
            
            # 高波动率时谨慎交易
            if volatility > 0.3:
                return False
            
            # 根据市场情绪判断
            if sentiment in ["bullish_stable", "neutral_stable"]:
                return True
            elif sentiment in ["bearish_volatile", "bearish_stable"]:
                return False
            else:
                return True  # 默认允许交易
                
        except Exception as e:
            logger.error(f"判断交易时机失败: {e}")
            return True

# 使用示例
if __name__ == "__main__":
    # 创建盈利计算器
    config = {
        'max_daily_loss': 0.01,
        'stop_loss_threshold': 0.005,
        'max_concurrent_orders': 5
    }
    
    profit_calc = ProfitCalculator(config)
    risk_manager = RiskManager(config)
    market_analyzer = MarketAnalyzer()
    
    # 示例计算
    algorithm = "SHA256"
    rental_price = 0.001
    pool_profit = 0.002
    
    net_profit = profit_calc.calculate_net_profit(algorithm, rental_price, pool_profit)
    print(f"净盈利: {net_profit}")
    
    profit_margin = profit_calc.calculate_profit_margin(algorithm, rental_price, pool_profit)
    print(f"利润率: {profit_margin}%")
    
    optimal_amount = profit_calc.get_optimal_order_amount(algorithm, rental_price, pool_profit, 0.1)
    print(f"最优订单金额: {optimal_amount}")
    
    should_proceed, reason = risk_manager.should_proceed_with_trade(algorithm, rental_price, pool_profit, 2)
    print(f"是否应该交易: {should_proceed}, 原因: {reason}")
    
    risk_score = risk_manager.get_risk_score(algorithm, rental_price, pool_profit)
    print(f"风险评分: {risk_score}")
