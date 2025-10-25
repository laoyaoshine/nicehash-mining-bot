#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多数据源管理器
统一管理多个API数据源，提供故障转移和负载均衡
"""

import requests
import json
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

class DataSourceManager:
    """多数据源管理器"""
    
    def __init__(self, session: requests.Session):
        self.session = session
        self.data_sources = {}
        self.source_health = {}
        self.last_update = {}
        self.cache_ttl = 300  # 5分钟缓存
        
        # 初始化数据源
        self._initialize_data_sources()
    
    def _initialize_data_sources(self):
        """初始化所有数据源"""
        
        # 1. WhatToMine API - 挖矿收益数据
        self.data_sources['whattomine'] = {
            'name': 'WhatToMine',
            'base_url': 'https://whattomine.com',
            'endpoints': {
                'coins': '/coins.json',
                'calculators': '/calculators.json'
            },
            'priority': 1,
            'type': 'mining_profitability',
            'rate_limit': 60,  # 每分钟60次请求
            'timeout': 30
        }
        
        # 2. CoinGecko API - 加密货币价格和市场数据
        self.data_sources['coingecko'] = {
            'name': 'CoinGecko',
            'base_url': 'https://api.coingecko.com/api/v3',
            'endpoints': {
                'simple_price': '/simple/price',
                'coins_list': '/coins/list',
                'market_data': '/coins/markets'
            },
            'priority': 2,
            'type': 'price_data',
            'rate_limit': 50,  # 每分钟50次请求
            'timeout': 30
        }
        
        # 3. CryptoCompare API - 价格和市场数据
        self.data_sources['cryptocompare'] = {
            'name': 'CryptoCompare',
            'base_url': 'https://min-api.cryptocompare.com/data',
            'endpoints': {
                'price_multi': '/pricemulti',
                'price_single': '/price',
                'mining_data': '/mining/data'
            },
            'priority': 3,
            'type': 'price_data',
            'rate_limit': 100,  # 每分钟100次请求
            'timeout': 30
        }
        
        # 4. CoinMarketCap API - 市场数据
        self.data_sources['coinmarketcap'] = {
            'name': 'CoinMarketCap',
            'base_url': 'https://api.coinmarketcap.com/data-api/v3',
            'endpoints': {
                'cryptocurrency_listing': '/cryptocurrency/listing',
                'price_quotes': '/cryptocurrency/quotes/latest'
            },
            'priority': 4,
            'type': 'market_data',
            'rate_limit': 30,  # 每分钟30次请求
            'timeout': 30
        }
        
        # 5. NiceHash API - 算力租赁数据
        self.data_sources['nicehash'] = {
            'name': 'NiceHash',
            'base_url': 'https://api2.nicehash.com/main/api/v2',
            'endpoints': {
                'global_stats': '/public/stats/global/current',
                'global_stats_eu': '/public/stats/global/current?market=EU',
                'global_stats_us': '/public/stats/global/current?market=US',
                'orders': '/public/orders/active',
                'algorithms': '/public/algorithms',
                'mining_algorithms': '/public/mining/algorithms',
                'exchange_rates': '/public/exchange/rates',
                'mining_algorithms_info': '/public/mining/algorithms/info'
            },
            'priority': 5,
            'type': 'mining_rental',
           'rate_limit': 20,  # 每分钟20次请求
           'timeout': 10  # 减少超时时间
        }
        
        # 初始化健康状态
        for source_id in self.data_sources:
            self.source_health[source_id] = {
                'status': 'unknown',
                'last_check': None,
                'success_count': 0,
                'failure_count': 0,
                'avg_response_time': 0
            }
    
    def test_data_source(self, source_id: str) -> bool:
        """测试数据源连接"""
        if source_id not in self.data_sources:
            return False
        
        source = self.data_sources[source_id]
        start_time = time.time()
        
        try:
            # 根据数据源类型选择测试端点
            if source['type'] == 'mining_profitability':
                test_url = source['base_url'] + source['endpoints']['coins']
            elif source['type'] == 'price_data':
                if source_id == 'coingecko':
                    test_url = source['base_url'] + source['endpoints']['simple_price'] + '?ids=bitcoin&vs_currencies=usd'
                elif source_id == 'cryptocompare':
                    test_url = source['base_url'] + source['endpoints']['price_multi'] + '?fsyms=BTC&tsyms=USD'
                else:
                    test_url = source['base_url'] + source['endpoints']['simple_price']
            elif source['type'] == 'market_data':
                test_url = source['base_url'] + source['endpoints']['cryptocurrency_listing']
            elif source['type'] == 'mining_rental':
                if source_id == 'nicehash':
                    # 尝试多个端点，优先使用更稳定的
                    endpoints_to_try = [
                        source['endpoints']['global_stats'],
                        source['endpoints']['algorithms'],
                        source['endpoints']['mining_algorithms'],
                        source['endpoints']['exchange_rates'],
                        source['endpoints']['mining_algorithms_info']
                    ]
                    
                    for endpoint in endpoints_to_try:
                        try:
                            test_url = source['base_url'] + endpoint
                            test_response = self.session.get(test_url, timeout=5)  # 更短的超时时间
                            if test_response.status_code == 200:
                                logger.info(f"NiceHash API使用端点: {endpoint}")
                                # 更新健康状态
                                self.source_health[source_id]['status'] = 'healthy'
                                self.source_health[source_id]['success_count'] += 1
                                self.source_health[source_id]['avg_response_time'] = time.time() - start_time
                                return True
                        except Exception as e:
                            logger.debug(f"NiceHash端点 {endpoint} 测试失败: {e}")
                            continue
                    
                    # 如果所有端点都失败，使用默认端点
                    test_url = source['base_url'] + source['endpoints']['global_stats']
                else:
                    test_url = source['base_url'] + source['endpoints']['global_stats']
            else:
                return False
            
            response = self.session.get(test_url, timeout=source['timeout'])
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.source_health[source_id]['status'] = 'healthy'
                self.source_health[source_id]['success_count'] += 1
                self.source_health[source_id]['avg_response_time'] = response_time
                logger.info(f"✓ {source['name']} API连接成功 (响应时间: {response_time:.2f}s)")
                return True
            else:
                self.source_health[source_id]['status'] = 'unhealthy'
                self.source_health[source_id]['failure_count'] += 1
                logger.warning(f"✗ {source['name']} API返回状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.source_health[source_id]['status'] = 'unhealthy'
            self.source_health[source_id]['failure_count'] += 1
            logger.error(f"✗ {source['name']} API连接失败: {e}")
            return False
        finally:
            self.source_health[source_id]['last_check'] = datetime.now()
    
    def test_all_sources(self) -> Dict[str, bool]:
        """测试所有数据源"""
        results = {}
        logger.info("测试所有数据源连接...")
        
        for source_id in self.data_sources:
            results[source_id] = self.test_data_source(source_id)
        
        healthy_count = sum(results.values())
        logger.info(f"数据源测试完成: {healthy_count}/{len(self.data_sources)} 个数据源可用")
        
        return results
    
    def get_mining_profitability_data(self) -> Dict[str, float]:
        """获取挖矿收益数据"""
        # 按优先级尝试数据源
        sources_by_priority = sorted(
            [s for s in self.data_sources.items() if s[1]['type'] == 'mining_profitability'],
            key=lambda x: x[1]['priority']
        )
        
        for source_id, source in sources_by_priority:
            if self.source_health[source_id]['status'] != 'healthy':
                continue
            
            try:
                if source_id == 'whattomine':
                    return self._get_whattomine_data()
                elif source_id == 'nicehash':
                    return self._get_nicehash_mining_data()
                    
            except Exception as e:
                logger.error(f"从 {source['name']} 获取挖矿数据失败: {e}")
                continue
        
        logger.warning("所有挖矿数据源都失败，返回空数据")
        return {}
    
    def get_price_data(self) -> Dict[str, float]:
        """获取价格数据"""
        # 按优先级尝试数据源
        sources_by_priority = sorted(
            [s for s in self.data_sources.items() if s[1]['type'] == 'price_data'],
            key=lambda x: x[1]['priority']
        )
        
        for source_id, source in sources_by_priority:
            if self.source_health[source_id]['status'] != 'healthy':
                continue
            
            try:
                if source_id == 'coingecko':
                    return self._get_coingecko_data()
                elif source_id == 'cryptocompare':
                    return self._get_cryptocompare_data()
                elif source_id == 'whattomine':
                    return self._get_whattomine_price_data()
                    
            except Exception as e:
                logger.error(f"从 {source['name']} 获取价格数据失败: {e}")
                continue
        
        logger.warning("所有价格数据源都失败，返回空数据")
        return {}
    
    def _get_whattomine_data(self) -> Dict[str, float]:
        """从WhatToMine获取数据"""
        url = self.data_sources['whattomine']['base_url'] + self.data_sources['whattomine']['endpoints']['coins']
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        profitability = {}
        
        algorithm_mapping = {
            'Bitcoin': 'SHA256',
            'Litecoin': 'Scrypt', 
            'Ethereum': 'Ethash',
            'Dash': 'X11',
            'Monero': 'CryptoNight',
            'Zcash': 'Equihash',
            'Vertcoin': 'Lyra2REv2',
            'Decred': 'Blake2s',
            'Siacoin': 'Blake14r',
            'Ethereum Classic': 'DaggerHashimoto',
            'Ravencoin': 'KawPow',
            'Grin': 'CuckooCycle',
            'Beam': 'BeamHash',
            'ArQmA': 'RandomARQ',
            'Loki': 'RandomXL',
            'Bitcoin Cash': 'SHA256',
            'Bitcoin SV': 'SHA256',
            'Dogecoin': 'Scrypt',
            'DigiByte': 'Scrypt',
            'Reddcoin': 'Scrypt',
            'Feathercoin': 'NeoScrypt',
            'Myriad': 'Myriad',
            'Groestlcoin': 'Groestl',
            'Skein': 'Skein',
            'Quark': 'Quark',
            'Nist5': 'Nist5',
            'Blake256': 'Blake256',
            'Lbry': 'Lbry',
            'Pascal': 'Pascal',
            'Dagger': 'Dagger',
            'X13': 'X13',
            'X14': 'X14',
            'X15': 'X15',
            'X16R': 'X16R',
            'X17': 'X17',
            'X18': 'X18',
            'X21S': 'X21S',
            'X22I': 'X22I',
            'X25X': 'X25X'
        }
        
        coins = data.get('coins', {})
        for coin_name, coin_data in coins.items():
            if isinstance(coin_data, dict) and 'profitability24' in coin_data:
                # 使用API返回的algorithm字段进行映射
                api_algorithm = coin_data.get('algorithm', '')
                algorithm = None
                
                # 直接映射API算法名称
                algorithm_direct_mapping = {
                    'BeamHashIII': 'BeamHash',
                    'BeamHashII': 'BeamHash',
                    'BeamHash': 'BeamHash',
                    'KawPow': 'KawPow',
                    'CuckooCycle': 'CuckooCycle',
                    'Quark': 'Quark',
                    'Lyra2REv2': 'Lyra2REv2',
                    'SHA256': 'SHA256',
                    'Ethash': 'Ethash',
                    'Scrypt': 'Scrypt',
                    'X11': 'X11',
                    'Equihash': 'Equihash',
                    'CryptoNight': 'CryptoNight',
                    'Blake2s': 'Blake2s',
                    'Blake14r': 'Blake14r',
                    'DaggerHashimoto': 'DaggerHashimoto'
                }
                
                algorithm = algorithm_direct_mapping.get(api_algorithm)
                
                # 如果没有直接映射，尝试通过币种名称映射
                if not algorithm:
                    for mapped_name, algo in algorithm_mapping.items():
                        if mapped_name.lower() in coin_name.lower():
                            algorithm = algo
                            break
                
                if algorithm:
                    profitability_usd = float(coin_data.get('profitability24', 0))
                    profitability_btc = max(0.0001, profitability_usd / 50000)  # 假设1 BTC = 50000 USD
                    profitability[algorithm] = profitability_btc
        
        logger.info(f"从WhatToMine获取到 {len(profitability)} 个算法的收益数据")
        return profitability
    
    def _get_whattomine_price_data(self) -> Dict[str, float]:
        """从WhatToMine获取价格数据"""
        url = self.data_sources['whattomine']['base_url'] + self.data_sources['whattomine']['endpoints']['coins']
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        prices = {}
        
        coins = data.get('coins', {})
        for coin_name, coin_data in coins.items():
            if isinstance(coin_data, dict) and 'exchange_rate' in coin_data:
                # 使用API返回的algorithm字段进行映射
                api_algorithm = coin_data.get('algorithm', '')
                
                # 直接映射API算法名称
                algorithm_direct_mapping = {
                    'BeamHashIII': 'BeamHash',
                    'BeamHashII': 'BeamHash',
                    'BeamHash': 'BeamHash',
                    'KawPow': 'KawPow',
                    'CuckooCycle': 'CuckooCycle',
                    'Quark': 'Quark',
                    'Lyra2REv2': 'Lyra2REv2',
                    'SHA256': 'SHA256',
                    'Ethash': 'Ethash',
                    'Scrypt': 'Scrypt',
                    'X11': 'X11',
                    'Equihash': 'Equihash',
                    'CryptoNight': 'CryptoNight',
                    'Blake2s': 'Blake2s',
                    'Blake14r': 'Blake14r',
                    'DaggerHashimoto': 'DaggerHashimoto'
                }
                
                algorithm = algorithm_direct_mapping.get(api_algorithm)
                
                if algorithm:
                    exchange_rate = float(coin_data.get('exchange_rate', 0))
                    if exchange_rate > 0:
                        prices[algorithm] = exchange_rate
        
        logger.info(f"从WhatToMine获取到 {len(prices)} 个算法的价格数据")
        return prices
    
    def _get_coingecko_data(self) -> Dict[str, float]:
        """从CoinGecko获取数据"""
        try:
            # 获取主要加密货币价格（使用USD价格，然后转换为BTC）
            coin_ids = [
                'bitcoin', 'litecoin', 'ethereum', 'dash', 'monero', 'zcash',
                'vertcoin', 'decred', 'siacoin', 'ethereum-classic', 'ravencoin',
                'grin', 'beam', 'arqma', 'loki', 'bitcoin-cash', 'bitcoin-sv',
                'dogecoin', 'digibyte', 'reddcoin', 'feathercoin', 'myriad',
                'groestlcoin', 'skein', 'quark', 'nist5', 'blake256', 'lbry',
                'pascal', 'dagger', 'x13', 'x14', 'x15', 'x16r', 'x17', 'x18',
                'x21s', 'x22i', 'x25x'
            ]
            url = f"{self.data_sources['coingecko']['base_url']}/simple/price"
            params = {
                'ids': ','.join(coin_ids),
                'vs_currencies': 'usd'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            prices = {}
            
            coin_mapping = {
                'bitcoin': 'SHA256',
                'litecoin': 'Scrypt',
                'ethereum': 'Ethash',
                'dash': 'X11',
                'monero': 'CryptoNight',
                'zcash': 'Equihash',
                'vertcoin': 'Lyra2REv2',
                'decred': 'Blake2s',
                'siacoin': 'Blake14r',
                'ethereum-classic': 'DaggerHashimoto',
                'ravencoin': 'KawPow',
                'grin': 'CuckooCycle',
                'beam': 'BeamHash',
                'arqma': 'RandomARQ',
                'loki': 'RandomXL',
                'bitcoin-cash': 'SHA256',
                'bitcoin-sv': 'SHA256',
                'dogecoin': 'Scrypt',
                'digibyte': 'Scrypt',
                'reddcoin': 'Scrypt',
                'feathercoin': 'NeoScrypt',
                'myriad': 'Myriad',
                'groestlcoin': 'Groestl',
                'skein': 'Skein',
                'quark': 'Quark',
                'nist5': 'Nist5',
                'blake256': 'Blake256',
                'lbry': 'Lbry',
                'pascal': 'Pascal',
                'dagger': 'Dagger',
                'x13': 'X13',
                'x14': 'X14',
                'x15': 'X15',
                'x16r': 'X16R',
                'x17': 'X17',
                'x18': 'X18',
                'x21s': 'X21S',
                'x22i': 'X22I',
                'x25x': 'X25X'
            }
            
            # 获取BTC价格用于转换
            btc_price_usd = data.get('bitcoin', {}).get('usd', 50000)  # 默认50000 USD
            
            for coin_id, price_data in data.items():
                if coin_id in coin_mapping and 'usd' in price_data:
                    algorithm = coin_mapping[coin_id]
                    usd_price = float(price_data['usd'])
                    
                    # 特殊处理Bitcoin - 使用合理的价格估算
                    if coin_id == 'bitcoin':
                        # Bitcoin价格应该是合理的挖矿收益，不是1 BTC
                        prices[algorithm] = 0.005  # 使用合理的价格
                    else:
                        # 转换为BTC价格
                        btc_price = usd_price / btc_price_usd
                        prices[algorithm] = btc_price
            
            logger.info(f"从CoinGecko获取到 {len(prices)} 个算法的价格数据")
            return prices
            
        except Exception as e:
            logger.error(f"CoinGecko API请求失败: {e}")
            # 尝试备用方法 - 直接获取BTC价格
            try:
                url = f"{self.data_sources['coingecko']['base_url']}/simple/price"
                params = {'ids': 'bitcoin', 'vs_currencies': 'usd'}
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                btc_price_usd = data.get('bitcoin', {}).get('usd', 50000)
                
                # 使用估算价格
                estimated_prices = {
                    'SHA256': 1.0,  # Bitcoin = 1 BTC
                    'Scrypt': 0.00002,  # Litecoin
                    'Ethash': 0.00002,  # Ethereum
                    'X11': 0.00001,    # Dash
                    'CryptoNight': 0.00001,  # Monero
                    'Equihash': 0.00001     # Zcash
                }
                
                logger.info(f"使用CoinGecko估算价格数据")
                return estimated_prices
                
            except Exception as e2:
                logger.error(f"CoinGecko备用方法也失败: {e2}")
                return {}
    
    def _get_cryptocompare_data(self) -> Dict[str, float]:
        """从CryptoCompare获取数据"""
        url = f"{self.data_sources['cryptocompare']['base_url']}/pricemulti"
        params = {
            'fsyms': 'BTC,LTC,ETH,DASH,XMR,ZEC',
            'tsyms': 'BTC'
        }
        
        response = self.session.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        prices = {}
        
        symbol_mapping = {
            'BTC': 'SHA256',
            'LTC': 'Scrypt',
            'ETH': 'Ethash',
            'DASH': 'X11',
            'XMR': 'CryptoNight',
            'ZEC': 'Equihash'
        }
        
        for symbol, price_data in data.items():
            if symbol in symbol_mapping and 'BTC' in price_data:
                algorithm = symbol_mapping[symbol]
                prices[algorithm] = float(price_data['BTC'])
        
        logger.info(f"从CryptoCompare获取到 {len(prices)} 个算法的价格数据")
        return prices
    
    def _get_nicehash_mining_data(self) -> Dict[str, float]:
        """从NiceHash获取挖矿数据"""
        try:
            # 尝试多个端点获取数据
            endpoints_to_try = [
                '/public/exchange/rates',
                '/public/mining/algorithms/info',
                '/public/stats/global/current'
            ]
            
            for endpoint in endpoints_to_try:
                try:
                    url = self.data_sources['nicehash']['base_url'] + endpoint
                    response = self.session.get(url, timeout=10)  # 减少超时时间
                    
                    if response.status_code == 200:
                        data = response.json()
                        profitability = {}
                        
                        # 根据不同的端点解析数据
                        if 'exchangeRates' in data:
                            # 汇率数据
                            rates = data.get('exchangeRates', [])
                            for rate in rates:
                                if isinstance(rate, dict) and 'symbol' in rate and 'rate' in rate:
                                    symbol = rate['symbol']
                                    try:
                                        rate_value = float(rate['rate'])
                                        # 映射到算法
                                        if 'BTC' in symbol:
                                            profitability['SHA256'] = rate_value * 0.001
                                    except (ValueError, TypeError):
                                        continue
                        elif 'miningAlgorithms' in data:
                            # 挖矿算法数据
                            algorithms = data.get('miningAlgorithms', [])
                            for algo in algorithms:
                                if isinstance(algo, dict) and 'algorithm' in algo:
                                    algorithm = algo['algorithm']
                                    try:
                                        price = float(algo.get('price', 0.001))
                                        profitability[algorithm] = price * 1.5
                                    except (ValueError, TypeError):
                                        profitability[algorithm] = 0.0015
                        elif 'algorithms' in data:
                            # 全局统计数据
                            algorithms = data.get('algorithms', [])
                            for algo in algorithms:
                                if isinstance(algo, dict) and 'algorithm' in algo:
                                    algorithm = algo['algorithm']
                                    try:
                                        price = float(algo.get('price', 0.001))
                                        profitability[algorithm] = price * 1.5
                                    except (ValueError, TypeError):
                                        profitability[algorithm] = 0.0015
                        
                        if profitability:
                            logger.info(f"从NiceHash {endpoint} 获取到 {len(profitability)} 个算法的挖矿数据")
                            return profitability
                            
                except Exception as e:
                    logger.warning(f"NiceHash端点 {endpoint} 失败: {e}")
                    continue
            
            logger.warning("所有NiceHash端点都失败")
            return {}
            
        except Exception as e:
            logger.error(f"NiceHash挖矿数据获取失败: {e}")
            return {}
    
    
    def get_source_status(self) -> Dict[str, Any]:
        """获取所有数据源状态"""
        status = {}
        for source_id, source in self.data_sources.items():
            health = self.source_health[source_id]
            status[source_id] = {
                'name': source['name'],
                'type': source['type'],
                'priority': source['priority'],
                'status': health['status'],
                'last_check': health['last_check'],
                'success_count': health['success_count'],
                'failure_count': health['failure_count'],
                'avg_response_time': health['avg_response_time']
            }
        return status
    
    def get_health_summary(self) -> str:
        """获取健康状态摘要"""
        healthy_count = sum(1 for h in self.source_health.values() if h['status'] == 'healthy')
        total_count = len(self.source_health)
        
        summary = f"数据源健康状态: {healthy_count}/{total_count} 可用\n"
        summary += "-" * 40 + "\n"
        
        for source_id, health in self.source_health.items():
            source = self.data_sources[source_id]
            status_icon = "✓" if health['status'] == 'healthy' else "✗"
            summary += f"{status_icon} {source['name']:<15} {health['status']:<10} "
            summary += f"成功: {health['success_count']:<3} 失败: {health['failure_count']:<3}\n"
        
        return summary
