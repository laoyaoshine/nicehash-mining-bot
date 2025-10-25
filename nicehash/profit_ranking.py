# 盈利代币排行模块
# 用于计算和显示各币种的盈利排名

import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class ProfitRanking:
    """盈利代币排行器"""
    
    def __init__(self):
        self.ranking_history = []
        self.algorithm_names = {
            'SHA256': 'Bitcoin (BTC)',
            'Scrypt': 'Litecoin (LTC)',
            'Ethash': 'Ethereum (ETH)',
            'X11': 'Dash (DASH)',
            'CryptoNight': 'Monero (XMR)',
            'Equihash': 'Zcash (ZEC)',
            'Lyra2REv2': 'Vertcoin (VTC)',
            'Blake2s': 'Decred (DCR)',
            'Blake14r': 'Siacoin (SC)',
            'DaggerHashimoto': 'Ethereum Classic (ETC)'
        }
        
        # 币种标识（用于显示，避免Unicode编码问题）
        self.coin_colors = {
            'Bitcoin (BTC)': '[BTC]',
            'Litecoin (LTC)': '[LTC]',
            'Ethereum (ETH)': '[ETH]',
            'Dash (DASH)': '[DASH]',
            'Monero (XMR)': '[XMR]',
            'Zcash (ZEC)': '[ZEC]',
            'Vertcoin (VTC)': '[VTC]',
            'Decred (DCR)': '[DCR]',
            'Siacoin (SC)': '[SC]',
            'Ethereum Classic (ETC)': '[ETC]'
        }
    
    def calculate_profit_ranking(self, market_prices: Dict[str, float], 
                               pool_profits: Dict[str, float], 
                               nicehash_fees: Dict[str, float],
                               pool_name: str = 'nicehash') -> List[Tuple[str, str, float, float, float, float, float, float, float]]:
        """计算盈利排行"""
        try:
            ranking_data = []
            
            for algorithm in market_prices:
                if algorithm not in pool_profits:
                    continue
                
                rental_price = market_prices[algorithm]
                pool_profit = pool_profits[algorithm]
                
                # 跳过没有矿池收益数据的算法
                if pool_profit <= 0:
                    continue
                
                # 检查是否有费率数据，没有则使用默认费率
                if not nicehash_fees or algorithm not in nicehash_fees:
                    nicehash_fee_rate = 0.03  # 使用默认3%费率
                else:
                    nicehash_fee_rate = nicehash_fees.get(algorithm)
                    if nicehash_fee_rate is None:
                        nicehash_fee_rate = 0.03  # 使用默认3%费率
                
                # 计算净盈利
                rental_cost = rental_price * (1 + nicehash_fee_rate)
                
                # 矿池手续费
                pool_fee_rates = {
                    'nicehash': 0.02,
                    'f2pool': 0.025,
                    'antpool': 0.025,
                    'slushpool': 0.02,
                    'viabtc': 0.025,
                    'btc.com': 0.025,
                    'poolin': 0.02
                }
                
                # 兼容pool_name传入非字符串的情况
                try:
                    pool_key = pool_name.lower() if isinstance(pool_name, str) else 'nicehash'
                except Exception:
                    pool_key = 'nicehash'
                pool_fee_rate = pool_fee_rates.get(pool_key, 0.025)
                pool_fee_cost = pool_profit * pool_fee_rate
                
                net_profit = pool_profit - rental_cost - pool_fee_cost
                
                # 计算利润率
                profit_margin = (net_profit / pool_profit * 100) if pool_profit > 0 else 0
                
                # 获取币种名称
                coin_name = self.algorithm_names.get(algorithm, algorithm)
                
                # 计算手续费
                rental_fee = rental_price * nicehash_fee_rate
                pool_fee = pool_profit * pool_fee_rate
                
                ranking_data.append((
                    algorithm,           # 挖矿算法
                    coin_name,          # 币种
                    rental_price,       # 代币价格 (市场价格)
                    rental_price,       # 租赁价格 (市场价格)
                    pool_profit,        # 矿池收益
                    pool_fee,           # 矿池手续费
                    rental_fee,         # NH租赁手续费
                    net_profit,         # 净盈利
                    profit_margin       # 利润率
                ))
            
            # 按净盈利排序
            ranking_data.sort(key=lambda x: x[7], reverse=True)
            
            # 记录排行历史
            self.ranking_history.append({
                'timestamp': datetime.now(),
                'ranking': ranking_data,
                'pool_name': pool_name
            })
            
            # 保持历史记录在合理范围内
            if len(self.ranking_history) > 1000:
                self.ranking_history = self.ranking_history[-500:]
            
            return ranking_data
            
        except Exception as e:
            logger.error(f"计算盈利排行失败: {e}")
            return []
    
    def display_profit_ranking(self, ranking_data: List[Tuple[str, str, float, float, float, float, float, float, float]], 
                             top_n: int = 10) -> str:
        """显示盈利排行"""
        try:
            if not ranking_data:
                return "暂无盈利数据"
            
            display_lines = []
            display_lines.append("=" * 80)
            display_lines.append("盈利代币排行榜")
            display_lines.append("=" * 80)
            display_lines.append(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            display_lines.append("")
            
            # 表头
            header = f"{'排名':<4} {'挖矿算法':<15} {'币种':<20} {'代币价格(BTC)':<15} {'租赁价格(BTC)':<15} {'矿池收益(BTC)':<15} {'矿池手续费(BTC)':<15} {'NH租赁手续费(BTC)':<18} {'净盈利(BTC)':<15} {'利润率(%)':<12}"
            display_lines.append(header)
            display_lines.append("-" * 180)
            
            # 显示前N名
            for i, (algorithm, coin_name, token_price, rental_price, pool_profit, pool_fee, rental_fee, net_profit, profit_margin) in enumerate(ranking_data[:top_n]):
                rank = i + 1
                color = self.coin_colors.get(coin_name, '⚪')
                
                # 格式化数据
                token_price_str = f"{token_price:.6f}"
                rental_price_str = f"{rental_price:.6f}"
                pool_profit_str = f"{pool_profit:.6f}"
                pool_fee_str = f"{pool_fee:.6f}"
                rental_fee_str = f"{rental_fee:.6f}"
                net_profit_str = f"{net_profit:.6f}"
                profit_margin_str = f"{profit_margin:.2f}"
                
                # 添加盈利状态标识
                if net_profit > 0:
                    status = "[+]"
                elif net_profit > -0.0001:
                    status = "[~]"
                else:
                    status = "[-]"
                
                line = f"{rank:<4} {algorithm:<15} {color}{coin_name:<19} {token_price_str:<14} {rental_price_str:<14} {pool_profit_str:<14} {pool_fee_str:<14} {rental_fee_str:<17} {status}{net_profit_str:<14} {profit_margin_str:<12}"
                display_lines.append(line)
            
            display_lines.append("")
            display_lines.append("图例: [+]盈利 [~]微亏 [-]亏损")
            display_lines.append("=" * 80)
            
            return "\n".join(display_lines)
            
        except Exception as e:
            logger.error(f"显示盈利排行失败: {e}")
            return f"显示排行失败: {e}"
    
    def get_profit_summary(self, ranking_data: List[Tuple[str, str, float, float, float, float]]) -> Dict[str, float]:
        """获取盈利摘要"""
        try:
            if not ranking_data:
                return {}
            
            total_profit = sum(item[2] for item in ranking_data)
            profitable_count = sum(1 for item in ranking_data if item[2] > 0)
            unprofitable_count = sum(1 for item in ranking_data if item[2] <= 0)
            
            avg_profit_margin = np.mean([item[3] for item in ranking_data])
            max_profit = max(item[2] for item in ranking_data)
            min_profit = min(item[2] for item in ranking_data)
            
            return {
                'total_profit': total_profit,
                'profitable_count': profitable_count,
                'unprofitable_count': unprofitable_count,
                'total_count': len(ranking_data),
                'avg_profit_margin': avg_profit_margin,
                'max_profit': max_profit,
                'min_profit': min_profit,
                'profitability_rate': profitable_count / len(ranking_data) * 100
            }
            
        except Exception as e:
            logger.error(f"获取盈利摘要失败: {e}")
            return {}
    
    def display_profit_summary(self, summary: Dict[str, float]) -> str:
        """显示盈利摘要"""
        try:
            if not summary:
                return "暂无摘要数据"
            
            display_lines = []
            display_lines.append("盈利摘要")
            display_lines.append("-" * 40)
            display_lines.append(f"总净盈利: {summary['total_profit']:.6f} BTC")
            display_lines.append(f"盈利币种: {summary['profitable_count']}/{summary['total_count']} ({summary['profitability_rate']:.1f}%)")
            display_lines.append(f"平均利润率: {summary['avg_profit_margin']:.2f}%")
            display_lines.append(f"最高盈利: {summary['max_profit']:.6f} BTC")
            display_lines.append(f"最低盈利: {summary['min_profit']:.6f} BTC")
            
            return "\n".join(display_lines)
            
        except Exception as e:
            logger.error(f"显示盈利摘要失败: {e}")
            return f"显示摘要失败: {e}"
    
    def get_trend_analysis(self, hours: int = 24) -> str:
        """获取趋势分析"""
        try:
            if len(self.ranking_history) < 2:
                return "数据不足，无法进行趋势分析"
            
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_history = [h for h in self.ranking_history if h['timestamp'] > cutoff_time]
            
            if len(recent_history) < 2:
                return "最近数据不足，无法进行趋势分析"
            
            # 分析趋势
            trends = []
            
            # 获取最新的排行
            latest_ranking = {item[0]: item[2] for item in recent_history[-1]['ranking']}
            
            # 获取之前的排行
            previous_ranking = {item[0]: item[2] for item in recent_history[0]['ranking']}
            
            for algorithm in latest_ranking:
                if algorithm in previous_ranking:
                    current_profit = latest_ranking[algorithm]
                    previous_profit = previous_ranking[algorithm]
                    change = current_profit - previous_profit
                    change_pct = (change / previous_profit * 100) if previous_profit != 0 else 0
                    
                    coin_name = self.algorithm_names.get(algorithm, algorithm)
                    trends.append((coin_name, change, change_pct))
            
            # 按变化幅度排序
            trends.sort(key=lambda x: x[1], reverse=True)
            
            display_lines = []
            display_lines.append("趋势分析 (最近24小时)")
            display_lines.append("-" * 50)
            
            for coin_name, change, change_pct in trends[:5]:  # 显示前5名
                if change > 0:
                    trend_icon = "[+]"
                elif change < 0:
                    trend_icon = "[-]"
                else:
                    trend_icon = "[=]"
                
                display_lines.append(f"{trend_icon} {coin_name}: {change:+.6f} BTC ({change_pct:+.2f}%)")
            
            return "\n".join(display_lines)
            
        except Exception as e:
            logger.error(f"趋势分析失败: {e}")
            return f"趋势分析失败: {e}"
    
    def get_top_profitable_coins(self, ranking_data: List[Tuple[str, str, float, float, float, float]], 
                               count: int = 5) -> List[str]:
        """获取最盈利的币种列表"""
        try:
            if not ranking_data:
                return []
            
            profitable_coins = [item[1] for item in ranking_data if item[2] > 0]
            return profitable_coins[:count]
            
        except Exception as e:
            logger.error(f"获取最盈利币种失败: {e}")
            return []
    
    def export_ranking_to_csv(self, ranking_data: List[Tuple[str, str, float, float, float, float]], 
                            filename: str = None) -> str:
        """导出排行数据到CSV文件"""
        try:
            if not ranking_data:
                return "无数据可导出"
            
            if filename is None:
                filename = f"profit_ranking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            # 创建DataFrame
            df = pd.DataFrame(ranking_data, columns=[
                'Algorithm', 'Coin_Name', 'Net_Profit', 'Profit_Margin', 'Rental_Price', 'Pool_Profit'
            ])
            
            # 添加排名
            df['Rank'] = range(1, len(df) + 1)
            
            # 重新排列列顺序
            df = df[['Rank', 'Algorithm', 'Coin_Name', 'Net_Profit', 'Profit_Margin', 'Rental_Price', 'Pool_Profit']]
            
            # 导出到CSV
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            return f"排行数据已导出到: {filename}"
            
        except Exception as e:
            logger.error(f"导出CSV失败: {e}")
            return f"导出失败: {e}"

# 使用示例
if __name__ == "__main__":
    # 创建排行器
    ranking = ProfitRanking()
    
    # 模拟数据
    market_prices = {
        'SHA256': 0.001,
        'Scrypt': 0.0008,
        'Ethash': 0.0012,
        'X11': 0.0009,
        'CryptoNight': 0.0011
    }
    
    pool_profits = {
        'SHA256': 0.002,
        'Scrypt': 0.0015,
        'Ethash': 0.003,
        'X11': 0.0018,
        'CryptoNight': 0.0022
    }
    
    nicehash_fees = {
        'SHA256': 0.018,
        'Scrypt': 0.022,
        'Ethash': 0.020,
        'X11': 0.019,
        'CryptoNight': 0.021
    }
    
    # 计算排行
    ranking_data = ranking.calculate_profit_ranking(market_prices, pool_profits, nicehash_fees)
    
    # 显示排行
    print(ranking.display_profit_ranking(ranking_data))
    print()
    
    # 显示摘要
    summary = ranking.get_profit_summary(ranking_data)
    print(ranking.display_profit_summary(summary))
    print()
    
    # 获取最盈利币种
    top_coins = ranking.get_top_profitable_coins(ranking_data, 3)
    print(f"最盈利的3个币种: {', '.join(top_coins)}")
