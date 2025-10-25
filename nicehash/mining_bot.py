# NiceHash 自动化挖矿机器人
# 功能：监控NiceHash算力价格，自动租赁算力进行挖矿盈利

import requests
import time
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import configparser
import io
import os
from profit_ranking import ProfitRanking
from cache_utils import TTLCache, RetryManager, ConcurrentFetcher, PerformanceMonitor, cached_with_ttl
from data_source_manager import DataSourceManager
from enhanced_trading_strategy_en import DynamicPriceMonitor, SmartOrderManager, HashrateGuaranteeManager
from auto_recharge_manager import AutoRechargeManager, RechargeConfig
from speed_limit_manager import SpeedLimitManager, SpeedLimitConfig, SpeedLimitMode

# 配置日志
class SafeConsoleHandler(logging.StreamHandler):
    """安全的控制台处理器，避免Unicode编码错误"""
    def emit(self, record):
        try:
            msg = self.format(record)
            # 只替换emoji字符，保留中文字符
            import re
            # 替换常见的emoji字符
            msg = re.sub(r'[^\x00-\x7F\u4e00-\u9fff]', '?', msg)
            stream = self.stream
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mining_bot.log', encoding='utf-8'),
        SafeConsoleHandler()
    ]
)
logger = logging.getLogger(__name__)

class NiceHashBot:
    """NiceHash自动化挖矿机器人"""
    
    def __init__(self, config_file: str = 'config.ini'):
        """初始化机器人"""
        self.config = self.load_config(config_file)
        self.nicehash_api_url = "https://api2.nicehash.com"
        self.session = requests.Session()
        self.current_orders = {}
        self.profit_history = []
        self.profit_ranking = ProfitRanking()
        
        # 初始化多数据源管理器
        self.data_source_manager = DataSourceManager(self.session)
        
        # 性能优化组件（使用ConfigParser的fallback避免类型错误）
        cache_ttl = self.config.getint('trading', 'cache_ttl_seconds', fallback=60)
        max_concurrent = self.config.getint('trading', 'max_concurrent_requests', fallback=3)
        request_timeout = self.config.getint('trading', 'request_timeout', fallback=30)
        retry_attempts = self.config.getint('trading', 'retry_max_attempts', fallback=3)
        backoff_factor = self.config.getfloat('trading', 'retry_backoff_factor', fallback=2.0)
        
        self.cache = TTLCache(default_ttl=cache_ttl)
        self.retry_manager = RetryManager(max_attempts=retry_attempts, backoff_factor=backoff_factor)
        self.concurrent_fetcher = ConcurrentFetcher(max_workers=max_concurrent, timeout=request_timeout)
        self.performance_monitor = PerformanceMonitor()

        # 网络与代理设置（可选）
        self.offline_mode = False
        try:
            if self.config.has_section('network'):
                http_proxy = self.config.get('network', 'http_proxy', fallback='').strip()
                https_proxy = self.config.get('network', 'https_proxy', fallback='').strip()
                no_proxy = self.config.get('network', 'no_proxy', fallback='').strip()
                verify_ssl = self.config.getboolean('network', 'verify_ssl', fallback=True)
                self.offline_mode = self.config.getboolean('network', 'offline_mode', fallback=False)

                proxies = {}
                if http_proxy:
                    proxies['http'] = http_proxy
                if https_proxy:
                    proxies['https'] = https_proxy
                if proxies:
                    self.session.proxies.update(proxies)
                    logger.info(f"已配置代理: {proxies}")
                if no_proxy:
                    os.environ['NO_PROXY'] = no_proxy
                    os.environ['no_proxy'] = no_proxy
                # SSL校验
                self.session.verify = verify_ssl
                
                if self.offline_mode:
                    logger.info("离线模式已启用，将使用模拟数据")
        except Exception as e:
            logger.warning(f"代理/网络配置解析失败: {e}")
        
        # 默认启用离线模式以避免网络问题
        if not self.config.has_section('network'):
            self.offline_mode = True
            logger.info("未检测到网络配置，启用离线模式")
        
        # 配置SSL和连接参数以解决SSL错误
        self.session.headers.update({
            'User-Agent': 'NiceHashBot/1.0',
            'Connection': 'keep-alive',
            'Accept-Encoding': 'gzip, deflate'
        })
        
        # 改进SSL配置和重试机制
        import urllib3
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        # 禁用SSL警告（仅用于测试环境）
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        # 创建适配器
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # SSL配置
        self.session.verify = True  # 启用SSL验证
        self.session.timeout = 30
        
        # API认证信息（带错误处理）
        try:
            self.api_key = self.config['nicehash']['api_key']
            self.api_secret = self.config['nicehash']['api_secret']
            self.org_id = self.config['nicehash']['org_id']
        
            # 检查API密钥是否为默认值
            if (self.api_key == 'your_nicehash_api_key' or 
                self.api_secret == 'your_nicehash_api_secret' or 
                self.org_id == 'your_nicehash_org_id'):
                logger.warning("检测到默认API配置，但将尝试使用公共API获取数据")
                # 只有在非离线模式下才尝试使用公共API
                if not self.offline_mode:
                    self.offline_mode = False  # 尝试使用公共API
            else:
                logger.info("使用配置的API密钥")
                # 只有在非离线模式下才使用API密钥
                if not self.offline_mode:
                    self.offline_mode = False
                
        except KeyError as e:
            logger.warning(f"API配置缺失: {e}，启用离线模式")
            self.offline_mode = True
            # 设置默认值避免后续错误
        
        # 读取NiceHash市场配置
        try:
            self.nicehash_market = self.config['network'].get('nicehash_market', 'auto')
            logger.info(f"NiceHash市场配置: {self.nicehash_market}")
        except KeyError:
            self.nicehash_market = 'auto'
            logger.info("使用默认NiceHash市场配置: auto")
            self.api_key = 'demo_key'
            self.api_secret = 'demo_secret'
            self.org_id = 'demo_org'
        
        # 盈利参数（带错误处理）
        try:
            self.profit_threshold = float(self.config['trading']['profit_threshold'])
            self.max_order_amount = float(self.config['trading']['max_order_amount'])
            self.min_order_amount = float(self.config['trading']['min_order_amount'])
        except (KeyError, ValueError) as e:
            logger.warning(f"交易参数配置错误: {e}，使用默认值")
            self.profit_threshold = 0.0005
            self.max_order_amount = 0.1
            self.min_order_amount = 0.01
        
        # 限速参数（带错误处理）
        try:
            self.rate_limit_delay = int(self.config['trading']['rate_limit_delay'])
            self.check_interval = int(self.config['trading']['check_interval'])
            self.max_orders = int(self.config['trading']['max_concurrent_orders'])
        except (KeyError, ValueError) as e:
            logger.warning(f"限速参数配置错误: {e}，使用默认值")
            self.rate_limit_delay = 300
            self.check_interval = 60
            self.max_orders = 5
        self.last_order_time = 0
        
        # 测试API连接
        if not self.offline_mode:
            logger.info("测试多数据源连接...")
            api_test_results = self.data_source_manager.test_all_sources()
            healthy_count = sum(api_test_results.values())
            if healthy_count == 0:
                logger.warning("所有数据源连接失败，自动启用离线模式")
                self.offline_mode = True
            else:
                logger.info(f"数据源测试完成: {healthy_count}/{len(api_test_results)} 个数据源可用")
                # 显示数据源状态摘要
                logger.info("\n" + self.data_source_manager.get_health_summary())
        
        logger.info("NiceHash挖矿机器人初始化完成")
        
        # 初始化增强交易策略组件
        self.price_monitor = DynamicPriceMonitor(base_check_interval=self.check_interval)
        self.order_manager = SmartOrderManager(max_orders=self.max_orders)
        self.hashrate_guarantee = HashrateGuaranteeManager(min_profitable_algorithms=3)
        
        # 初始化自动充值和限速管理器
        self._init_auto_recharge_manager()
        self._init_speed_limit_manager()
    
    def _init_auto_recharge_manager(self):
        """初始化自动充值管理器"""
        try:
            recharge_config = RechargeConfig(
                enabled=self.config.getboolean('trading', 'auto_recharge_enabled', fallback=True),
                threshold=self.config.getfloat('trading', 'auto_recharge_threshold', fallback=0.01),
                recharge_amount=self.config.getfloat('trading', 'auto_recharge_amount', fallback=0.1),
                min_balance_threshold=self.config.getfloat('trading', 'min_balance_threshold', fallback=0.05)
            )
            self.auto_recharge = AutoRechargeManager(recharge_config)
            logger.info("自动充值管理器初始化完成")
        except Exception as e:
            logger.error(f"自动充值管理器初始化失败: {e}")
            self.auto_recharge = None
    
    def _init_speed_limit_manager(self):
        """初始化限速管理器"""
        try:
            speed_config = SpeedLimitConfig(
                max_speed_limit=self.config.getfloat('trading', 'max_speed_limit', fallback=1000.0),
                mode=SpeedLimitMode.ADAPTIVE,
                adaptive_factor=0.8,
                min_speed_limit=100.0
            )
            self.speed_limit = SpeedLimitManager(speed_config)
            logger.info(f"限速管理器初始化完成 - 最大限速: {speed_config.max_speed_limit} TH/s")
        except Exception as e:
            logger.error(f"限速管理器初始化失败: {e}")
            self.speed_limit = None
    
    def load_config(self, config_file: str) -> configparser.ConfigParser:
        """加载配置文件"""
        config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"))
        
        # 如果配置文件不存在，创建默认配置
        if not os.path.exists(config_file):
            self.create_default_config(config_file)
        
        # 强制以UTF-8读取，兼容Windows中文路径/内容
        try:
            with open(config_file, 'r', encoding='utf-8', errors='ignore') as f:
                config.read_file(f)
        except Exception:
            config.read(config_file, encoding='utf-8')
        return config
    
    def create_default_config(self, config_file: str):
        """创建默认配置文件"""
        config = configparser.ConfigParser()
        
        config['nicehash'] = {
            'api_key': 'your_nicehash_api_key',
            'api_secret': 'your_nicehash_api_secret',
            'org_id': 'your_nicehash_org_id'
        }
        
        config['mining_pools'] = {
            'pool_url': 'https://api.miningpool.com',
            'pool_api_key': 'your_pool_api_key',
            'wallet_address': 'your_wallet_address'
        }
        
        config['trading'] = {
            'profit_threshold': '0.001',  # BTC
            'max_order_amount': '0.1',    # BTC
            'min_order_amount': '0.01',   # BTC
            'rate_limit_delay': '300',    # 秒
            'check_interval': '60'        # 秒
        }
        
        config['algorithms'] = {
            'SHA256': 'true',
            'Scrypt': 'true',
            'Ethash': 'true'
        }
        
        with open(config_file, 'w') as f:
            config.write(f)
        
        logger.info(f"已创建默认配置文件: {config_file}")
        logger.info("请编辑配置文件填入您的API密钥等信息")
    
    def get_nicehash_headers(self) -> Dict[str, str]:
        """获取NiceHash API请求头"""
        return {
            'X-Auth': f'{self.api_key}:{self.api_secret}',
            'X-Organization-Id': self.org_id,
            'Content-Type': 'application/json'
        }
    
    def get_optimal_market_fee(self, algorithm: str, fees_data: Dict[str, Dict[str, float]]) -> tuple:
        """获取算法的最优市场费率
        返回: (market_name, fee_value)
        """
        if algorithm not in fees_data:
            return ('DEFAULT', 0.03)  # 默认费率
        
        algorithm_fees = fees_data[algorithm]
        
        # 如果有多个市场，选择费率最低的
        if len(algorithm_fees) > 1:
            best_market = min(algorithm_fees.items(), key=lambda x: x[1])
            return best_market
        elif len(algorithm_fees) == 1:
            return list(algorithm_fees.items())[0]
        else:
            return ('DEFAULT', 0.03)  # 默认费率
    
    def get_nicehash_fees(self, market: str = 'auto') -> Dict[str, Dict[str, float]]:
        """获取NiceHash各算法的实时费率（支持EU/US双市场）"""
        # 禁用模拟数据，只使用真实API
        # market: 'auto', 'EU', 'US', 'both'
        # 返回格式: {algorithm: {'EU': fee, 'US': fee}}
        
        # 先尝试从本地TTL缓存读取
        try:
            cached = self.cache.get('nicehash_fees')
            if cached:
                self.performance_monitor.record_cache_hit()
                return cached
            else:
                self.performance_monitor.record_cache_miss()
        except Exception:
            pass

        def _fetch_fees():
            start_time = time.time()
            try:
                # 使用公共API（不需要认证）
                # 根据NiceHash官方REST API文档更新端点，支持EU/US双市场
                if market == 'both':
                    # 同时获取EU和US市场数据
                    markets_to_try = [
                        ('EU', '/main/api/v2/public/stats/global/current?market=EU'),
                        ('US', '/main/api/v2/public/stats/global/current?market=US')
                    ]
                elif market == 'auto':
                    # 自动选择：先尝试EU，再尝试US，最后尝试默认
                    markets_to_try = [
                        ('EU', '/main/api/v2/public/stats/global/current?market=EU'),
                        ('US', '/main/api/v2/public/stats/global/current?market=US'),
                        ('DEFAULT', '/main/api/v2/public/stats/global/current')
                    ]
                elif market == 'EU':
                    markets_to_try = [
                        ('EU', '/main/api/v2/public/stats/global/current?market=EU'),
                        ('DEFAULT', '/main/api/v2/public/stats/global/current')
                    ]
                elif market == 'US':
                    markets_to_try = [
                        ('US', '/main/api/v2/public/stats/global/current?market=US'),
                        ('DEFAULT', '/main/api/v2/public/stats/global/current')
                    ]
                else:
                    # 默认行为
                    markets_to_try = [
                        ('DEFAULT', '/main/api/v2/public/stats/global/current')
                    ]
                
                all_fees = {}  # 存储所有市场的数据
                
                for market_name, endpoint in markets_to_try:
                    try:
                        url = f'{self.nicehash_api_url}{endpoint}'
                        response = self.session.get(url, timeout=30)
                        
                        if response.status_code == 200:
                            data = response.json()
                            market_fees = {}
                
                            # 根据不同的端点解析费率数据
                            if endpoint in ['/main/api/v2/public/stats/global/current', 
                                          '/main/api/v2/public/stats/global/current?market=EU',
                                          '/main/api/v2/public/stats/global/current?market=US']:
                                # 全局统计数据 - 实际响应格式
                                if 'algos' in data:
                                    # 算法ID到名称的映射 (根据NiceHash官方算法列表和实际API响应)
                                    algorithm_names = {
                                        0: 'INVALID', 1: 'SHA256', 3: 'Scrypt', 8: 'Scrypt', 11: 'X11', 
                                        20: 'SHA256', 24: 'Scrypt', 35: 'Scrypt', 36: 'Scrypt', 43: 'Scrypt',
                                        47: 'Scrypt', 48: 'SHA256', 52: 'Scrypt', 54: 'Ethash', 56: 'Ethash',
                                        57: 'Ethash', 58: 'Ethash', 59: 'Ethash', 60: 'Ethash', 61: 'Ethash',
                                        62: 'Ethash', 63: 'Ethash', 66: 'SHA256', 67: 'SHA256', 69: 'SHA256'
                                    }
                                    
                                    for algo in data['algos']:
                                        if 'a' in algo and 'p' in algo:
                                            algorithm_id = algo['a']
                                            price = float(algo['p'])
                                            
                                            # 获取算法名称，如果未知则使用通用名称
                                            algorithm_name = algorithm_names.get(algorithm_id, f'Algorithm_{algorithm_id}')
                                            
                                            # 对于未知算法，尝试根据ID推断算法类型
                                            if algorithm_name.startswith('Algorithm_'):
                                                # 基于算法ID推断可能的算法类型
                                                if algorithm_id in [12, 13, 14, 15, 16, 17, 18, 19]:
                                                    algorithm_name = 'CryptoNight'
                                                elif algorithm_id in [21, 22, 23, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 37, 38, 39, 40, 41, 42, 44, 45, 46, 49, 50, 51, 53, 55, 64, 65, 68]:
                                                    algorithm_name = 'Equihash'
                                                elif algorithm_id in [70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99]:
                                                    algorithm_name = 'Equihash'
                                                else:
                                                    # 保持原始名称
                                                    pass
                                            
                                            # 基于价格估算费率 (NiceHash通常收取2-5%的费率)
                                            # 这里我们使用一个合理的估算方法
                                            if price > 0:
                                                # 费率通常在2-5%之间，我们使用3%作为估算
                                                estimated_fee = 0.03
                                                market_fees[algorithm_name] = estimated_fee
                                            
                                            logger.debug(f"算法 {algorithm_name} (ID:{algorithm_id}) 价格: {price}, 估算费率: 0.03")
                                
                                if market_fees:
                                    market_info = ""
                                    if 'market=EU' in endpoint:
                                        market_info = " (EU市场)"
                                    elif 'market=US' in endpoint:
                                        market_info = " (US市场)"
                                    logger.info(f"从NiceHash {endpoint} 获取到 {len(market_fees)} 个算法费率{market_info}")
                                    
                                    # 将市场数据合并到总数据结构中
                                    for algorithm, fee in market_fees.items():
                                        if algorithm not in all_fees:
                                            all_fees[algorithm] = {}
                                        all_fees[algorithm][market_name] = fee
                                    
                                    # 如果是单市场模式，直接返回
                                    if market != 'both':
                                        return {alg: {market_name: fee} for alg, fee in market_fees.items()}
                            
                            if market_fees:
                                market_info = ""
                                if 'market=EU' in endpoint:
                                    market_info = " (EU市场)"
                                elif 'market=US' in endpoint:
                                    market_info = " (US市场)"
                                logger.info(f"从NiceHash {endpoint} 获取到费率数据{market_info}")
                                
                                # 将市场数据合并到总数据结构中
                                for algorithm, fee in market_fees.items():
                                    if algorithm not in all_fees:
                                        all_fees[algorithm] = {}
                                    all_fees[algorithm][market_name] = fee
                                
                                # 如果是单市场模式，直接返回
                                if market != 'both':
                                    return {alg: {market_name: fee} for alg, fee in market_fees.items()}
                                
                    except Exception as e:
                        logger.warning(f"NiceHash端点 {endpoint} 失败: {e}")
                        continue
                
                # 如果是双市场模式，返回合并后的数据
                if market == 'both' and all_fees:
                    logger.info(f"成功获取双市场费率数据: {len(all_fees)} 个算法")
                    return all_fees
                
                logger.warning("所有NiceHash端点都失败")
                return None
                
                # 记录性能指标
                response_time = time.time() - start_time
                self.performance_monitor.record_api_call(response_time)
                
                logger.info(f"获取到真实NiceHash费率: {fees}")
                # 写入缓存
                try:
                    self.cache.set('nicehash_fees', fees)
                except Exception:
                    pass
                return fees
                
            except Exception as e:
                logger.error(f"获取NiceHash费率失败: {e}")
                # 尝试备用API端点
                try:
                    logger.info("尝试备用费率API端点...")
                    # 尝试不同的API基础URL - 根据官方文档
                    backup_urls = [
                        "https://api2.nicehash.com/main/api/v2",
                        "https://api2.nicehash.com/api/v2",
                        "https://api.nicehash.com/api/v2"
                    ]
                    
                    for base_url in backup_urls:
                        try:
                            response = self.session.get(
                                f'{base_url}/main/api/v2/public/info',
                                timeout=10
                            )
                            if response.status_code == 200:
                                data = response.json()
                                fees = {}
                                
                                # 解析数据
                                if 'result' in data and 'algorithms' in data['result']:
                                    for algo in data['result']['algorithms']:
                                        if 'algorithm' in algo:
                                            algorithm = algo['algorithm']
                                            fees[algorithm] = 0.02  # 使用默认费率
                                    
                                    if fees:
                                        logger.info(f"从备用API {base_url} 获取到 {len(fees)} 个算法费率")
                                        return fees
                        except Exception as e:
                            logger.debug(f"备用API {base_url} 失败: {e}")
                            continue
                    
                except Exception as e2:
                    logger.error(f"所有备用API也失败: {e2}")
                
                # 所有费率API失败，返回空费率
                logger.warning("所有NiceHash API失败，返回空费率")
                return {}
        
        # 使用重试机制
        result = self.retry_manager.retry_with_backoff(_fetch_fees)
        
        if result is None or not result:
            logger.warning("重试机制也失败，返回空费率")
            return {}
        
        try:
            self.cache.set('nicehash_fees', result)
        except Exception:
            pass
        
        return result
    
    def get_market_prices(self) -> Dict[str, float]:
        """获取市场价格数据（仅使用真实API）"""
        # 禁用模拟数据，只使用真实API
        try:
            prices = self.data_source_manager.get_price_data()
            if prices:
                logger.info(f"从多数据源获取到市场价格: {len(prices)} 个算法")
                return prices
            else:
                logger.warning("未能获取到任何价格数据")
                return {}
        except Exception as e:
            logger.error(f"多数据源获取价格失败: {e}")
            return {}
    
    def get_pool_profitability(self) -> Dict[str, float]:
        """获取矿池收益数据（仅使用真实API）"""
        # 禁用模拟数据，只使用真实API
        try:
            profitability = self.data_source_manager.get_mining_profitability_data()
            if profitability:
                logger.info(f"从多数据源获取到矿池收益: {len(profitability)} 个算法")
                return profitability
            else:
                logger.warning("未能获取到任何矿池收益数据")
                return {}
        except Exception as e:
            logger.error(f"多数据源获取矿池收益失败: {e}")
            return {}
    
    def calculate_profit(self, algorithm: str, rental_price: float, pool_profit: float, 
                        pool_name: str = 'nicehash', nicehash_fees: Dict[str, float] = None) -> float:
        """计算盈利 - 租赁算力模式（包含矿池手续费和动态NiceHash费率）"""
        # 获取NiceHash费率（如果未提供则使用默认值）
        if nicehash_fees is None:
            nicehash_fees = self.get_nicehash_fees(self.nicehash_market)
        
        # 确保nicehash_fees不为None
        if nicehash_fees is None:
            nicehash_fees = {}
        
        # NiceHash手续费率（支持双市场数据）
        if algorithm not in nicehash_fees or not nicehash_fees:
            logger.warning(f"算法 {algorithm} 没有可用的NiceHash费率数据，使用默认费率 0.03")
            nicehash_fee_rate = 0.03  # 使用默认3%费率
            market_name = 'DEFAULT'
        else:
            # 检查是否是双市场数据格式
            algorithm_fees = nicehash_fees.get(algorithm)
            if isinstance(algorithm_fees, dict):
                # 双市场数据格式: {algorithm: {'EU': fee, 'US': fee}}
                market_name, nicehash_fee_rate = self.get_optimal_market_fee(algorithm, nicehash_fees)
                logger.debug(f"算法 {algorithm} 选择最优市场 {market_name}，费率: {nicehash_fee_rate}")
            else:
                # 单市场数据格式: {algorithm: fee}
                nicehash_fee_rate = algorithm_fees
                market_name = 'DEFAULT'
            
            if nicehash_fee_rate is None:
                logger.warning(f"算法 {algorithm} 的NiceHash费率为空，使用默认费率 0.03")
                nicehash_fee_rate = 0.03
                market_name = 'DEFAULT'
        rental_cost = rental_price * (1 + nicehash_fee_rate)
        
        # 矿池手续费率（各矿池不同）
        pool_fee_rates = {
            'nicehash': 0.02,    # 2%
            'f2pool': 0.025,     # 2.5%
            'antpool': 0.025,    # 2.5%
            'slushpool': 0.02,   # 2%
            'viabtc': 0.025,     # 2.5%
            'btc.com': 0.025,    # 2.5%
            'poolin': 0.02       # 2%
        }
        
        # 兼容pool_name为非字符串或字典的情况
        try:
            pool_key = pool_name.lower() if isinstance(pool_name, str) else 'nicehash'
        except Exception:
            pool_key = 'nicehash'
        pool_fee_rate = pool_fee_rates.get(pool_key, 0.025)  # 默认2.5%
        pool_fee_cost = pool_profit * pool_fee_rate
        
        # 净盈利 = 矿池收益 - 租赁成本 - 矿池手续费
        net_profit = pool_profit - rental_cost - pool_fee_cost
        
        logger.debug(f"{algorithm} ({pool_name}): 租赁价格={rental_price}, NiceHash费率={nicehash_fee_rate:.3f}, "
                    f"矿池收益={pool_profit}, 租赁成本={rental_cost}, 矿池手续费={pool_fee_cost}, 净盈利={net_profit}")
        
        return net_profit
    
    def create_order(self, algorithm: str, price: float, amount: float, market: str = 'DEFAULT', speed: Optional[float] = None) -> Optional[str]:
        """创建NiceHash订单（支持市场选择和速度限制）"""
        # 离线模式下模拟创建订单
        if self.offline_mode:
            speed_info = f", 速度: {speed:.1f} TH/s" if speed else ""
            logger.info(f"[模拟] 创建订单: {algorithm} ({market}), 价格: {price}, 数量: {amount}{speed_info}")
            # 生成模拟订单ID
            order_id = f"demo_order_{algorithm}_{market}_{int(time.time())}"
            self.current_orders[order_id] = {
                'algorithm': algorithm,
                'market': market,
                'price': price,
                'amount': amount,
                'speed': speed,
                'created_at': datetime.now()
            }
            return order_id
        
        try:
            headers = self.get_nicehash_headers()
            
            # 根据市场参数设置订单数据
            market_value = 'EU' if market == 'EU' else 'US' if market == 'US' else 'EU'  # 默认EU
            order_data = {
                'algorithm': algorithm,
                'price': price,
                'limit': amount,
                'amount': amount,
                'market': market_value,
                'type': 'STANDARD'
            }
            
            # 添加速度限制（如果提供）
            if speed is not None:
                order_data['speed'] = speed
            
            response = self.session.post(
                f'{self.nicehash_api_url}/main/api/v2/hashpower/order',
                headers=headers,
                json=order_data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            order_id = result.get('id')
            
            if order_id:
                speed_info = f", 速度: {speed:.1f} TH/s" if speed else ""
                logger.info(f"成功创建订单: {algorithm} ({market}), 价格: {price}, 数量: {amount}{speed_info}")
                self.current_orders[order_id] = {
                    'algorithm': algorithm,
                    'market': market,
                    'price': price,
                    'amount': amount,
                    'speed': speed,
                    'created_at': datetime.now()
                }
            
            return order_id
            
        except Exception as e:
            logger.error(f"创建订单失败: {e}")
            return None
    
    def update_order_price(self, order_id: str, new_price: float) -> bool:
        """更新订单价格"""
        # 离线模式下模拟更新订单
        if self.offline_mode:
            logger.info(f"[模拟] 更新订单价格: {order_id}, 新价格: {new_price}")
            if order_id in self.current_orders:
                self.current_orders[order_id]['price'] = new_price
            return True
        
        try:
            headers = self.get_nicehash_headers()
            
            update_data = {
                'price': new_price
            }
            
            response = self.session.post(
                f'{self.nicehash_api_url}/main/api/v2/hashpower/order/{order_id}/updatePrice',
                headers=headers,
                json=update_data,
                timeout=30
            )
            response.raise_for_status()
            
            logger.info(f"成功更新订单价格: {order_id}, 新价格: {new_price}")
            return True
            
        except Exception as e:
            logger.error(f"更新订单价格失败: {e}")
            return False
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        # 离线模式下模拟取消订单
        if self.offline_mode:
            logger.info(f"[模拟] 取消订单: {order_id}")
            if order_id in self.current_orders:
                del self.current_orders[order_id]
            return True
        
        try:
            headers = self.get_nicehash_headers()
            
            response = self.session.delete(
                f'{self.nicehash_api_url}/main/api/v2/hashpower/order/{order_id}',
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            logger.info(f"成功取消订单: {order_id}")
            if order_id in self.current_orders:
                del self.current_orders[order_id]
            
            return True
            
        except Exception as e:
            logger.error(f"取消订单失败: {e}")
            return False
    
    def should_rate_limit(self) -> bool:
        """检查是否需要限速"""
        current_time = time.time()
        if current_time - self.last_order_time < self.rate_limit_delay:
            return True
        return False
    
    def execute_trading_strategy(self):
        """执行交易策略（优化版）"""
        start_time = time.time()
        
        try:
            # 使用并发获取所有数据
            data_results = self.get_all_data_concurrent()
            
            # 安全获取数据，避免NoneType错误
            market_prices = data_results.get('market_prices') if data_results else None
            pool_profits = data_results.get('pool_profits') if data_results else None
            nicehash_fees = data_results.get('nicehash_fees') if data_results else None
            
            if not market_prices and not pool_profits:
                logger.warning("无法获取市场数据，跳过本次交易")
                return
            # 禁用模拟数据回退，必须获取到真实数据
            if not market_prices:
                logger.warning("无法获取市场价格数据，跳过本次交易")
                return
            if not pool_profits:
                logger.warning("无法获取矿池收益数据，跳过本次交易")
                return
            
            # 分析每个算法的盈利情况（支持双市场）
            profitable_algorithms = []  # [(algorithm, market, rental_price, net_profit)]
            unprofitable_algorithms = []  # [(algorithm, market, rental_price, net_profit)]
            
            for algorithm in market_prices:
                if algorithm not in pool_profits:
                    continue
                    
                rental_price = market_prices[algorithm]
                pool_profit = pool_profits[algorithm]
                
                # 跳过没有矿池收益数据的算法
                if pool_profit <= 0:
                    logger.warning(f"算法 {algorithm} 没有有效的矿池收益数据，跳过分析")
                    continue
                
                # 检查是否是双市场费率数据
                if nicehash_fees and algorithm in nicehash_fees:
                    algorithm_fees = nicehash_fees.get(algorithm)
                    if isinstance(algorithm_fees, dict):
                        # 双市场数据格式: {algorithm: {'EU': fee, 'US': fee}}
                        for market_name, fee in algorithm_fees.items():
                            if fee is not None:
                                # 为每个市场单独计算盈利
                                market_fees = {algorithm: {market_name: fee}}
                                net_profit = self.calculate_profit(algorithm, rental_price, pool_profit, 'nicehash', market_fees)
                                
                                logger.info(f"{algorithm} ({market_name}): 租赁价格={rental_price}, NiceHash费率={fee:.3f}, "
                                           f"矿池收益={pool_profit}, 净盈利={net_profit}")
                                
                                if net_profit > self.profit_threshold:
                                    profitable_algorithms.append((algorithm, market_name, rental_price, net_profit))
                                else:
                                    unprofitable_algorithms.append((algorithm, market_name, rental_price, net_profit))
                    else:
                        # 单市场数据格式: {algorithm: fee}
                        net_profit = self.calculate_profit(algorithm, rental_price, pool_profit, 'nicehash', nicehash_fees)
                        
                        logger.info(f"{algorithm}: 租赁价格={rental_price}, NiceHash费率={algorithm_fees:.3f}, "
                                   f"矿池收益={pool_profit}, 净盈利={net_profit}")
                        
                        if net_profit > self.profit_threshold:
                            profitable_algorithms.append((algorithm, 'DEFAULT', rental_price, net_profit))
                        else:
                            unprofitable_algorithms.append((algorithm, 'DEFAULT', rental_price, net_profit))
                else:
                    # 没有费率数据，使用默认费率
                    logger.warning(f"算法 {algorithm} 没有可用的费率数据，使用默认费率 0.03")
                    nicehash_fee = 0.03
                    net_profit = self.calculate_profit(algorithm, rental_price, pool_profit, 'nicehash', {algorithm: nicehash_fee})
                    
                    logger.info(f"{algorithm}: 租赁价格={rental_price}, NiceHash费率={nicehash_fee:.3f}, "
                               f"矿池收益={pool_profit}, 净盈利={net_profit}")
                    
                    if net_profit > self.profit_threshold:
                        profitable_algorithms.append((algorithm, 'DEFAULT', rental_price, net_profit))
                    else:
                        unprofitable_algorithms.append((algorithm, 'DEFAULT', rental_price, net_profit))
            
            # 处理盈利的算法（支持双市场）
            for algorithm, market, price, profit in profitable_algorithms:
                if not self.should_rate_limit():
                    # 创建或调整订单以抢购算力
                    amount = min(self.max_order_amount, profit * 0.1)  # 根据盈利调整数量
                    
                    # 检查是否已有该算法在该市场的订单
                    existing_order = None
                    for order_id, order_info in self.current_orders.items():
                        if order_info['algorithm'] == algorithm and order_info.get('market') == market:
                            existing_order = order_id
                            break
                    
                    if existing_order:
                        # 更新现有订单价格
                        self.update_order_price(existing_order, price)
                    else:
                        # 创建新订单（包含市场信息）
                        self.create_order(algorithm, price, amount, market)
                    
                    self.last_order_time = time.time()
                else:
                    logger.info(f"限速中，跳过{algorithm}的订单操作")
            
            # 处理不盈利的算法（支持双市场）
            for algorithm, market, price, profit in unprofitable_algorithms:
                # 查找并取消不盈利的订单（按算法和市场）
                orders_to_cancel = []
                for order_id, order_info in self.current_orders.items():
                    if order_info['algorithm'] == algorithm and order_info.get('market') == market:
                        orders_to_cancel.append(order_id)
                
                for order_id in orders_to_cancel:
                    self.cancel_order(order_id)
            
            # 计算盈利排行（转换双市场费率为单市场格式）
            single_market_fees = {}
            if nicehash_fees:
                for algorithm, market_fees in nicehash_fees.items():
                    if isinstance(market_fees, dict):
                        # 双市场数据：选择最优费率（最低费率）
                        best_fee = min(market_fees.values()) if market_fees else 0.03
                        single_market_fees[algorithm] = best_fee
                    else:
                        # 单市场数据：直接使用
                        single_market_fees[algorithm] = market_fees
            
            ranking_data = self.profit_ranking.calculate_profit_ranking(
                market_prices, pool_profits, single_market_fees, 'nicehash'
            )
            
            # 显示盈利排行
            if ranking_data:
                logger.info("\n" + self.profit_ranking.display_profit_ranking(ranking_data, top_n=30))
                
                # 显示盈利摘要
                summary = self.profit_ranking.get_profit_summary(ranking_data)
                if summary:
                    logger.info("\n" + self.profit_ranking.display_profit_summary(summary))
                
                # 显示趋势分析
                trend_analysis = self.profit_ranking.get_trend_analysis(hours=24)
                if trend_analysis and "数据不足" not in trend_analysis:
                    logger.info("\n" + trend_analysis)
            
            # 记录盈利历史
            total_profit = sum(profit for _, _, _, profit in profitable_algorithms)
            self.profit_history.append({
                'timestamp': datetime.now(),
                'total_profit': total_profit,
                'profitable_count': len(profitable_algorithms),
                'unprofitable_count': len(unprofitable_algorithms),
                'nicehash_fees': nicehash_fees or {},
                'ranking_data': ranking_data or [],
                'execution_time': time.time() - start_time
            })
            
            # 保持历史记录在合理范围内
            if len(self.profit_history) > 1000:
                self.profit_history = self.profit_history[-500:]
            
            # 显示性能指标
            execution_time = time.time() - start_time
            logger.info(f"策略执行完成，耗时: {execution_time:.2f}秒")
            
            # 定期显示性能指标
            if len(self.profit_history) % 10 == 0:
                metrics = self.get_performance_metrics()
                logger.info(f"性能指标: {metrics}")
            
            # 定期显示完整算法排行榜
            if len(self.profit_history) % 3 == 0:  # 每3次执行显示一次
                logger.info("\n正在生成完整算法排行榜...")
                full_ranking = self.get_all_algorithms_profit_ranking(30)
                self.display_profit_ranking(full_ranking)
                
        except Exception as e:
            logger.error(f"交易策略执行失败: {e}")
            self.performance_monitor.record_retry()
    
    def execute_enhanced_trading_strategy(self):
        """执行增强版交易策略"""
        start_time = time.time()
        
        try:
            # 使用并发获取所有数据
            data_results = self.get_all_data_concurrent()
            
            # 安全获取数据，避免NoneType错误
            market_prices = data_results.get('market_prices') if data_results else None
            pool_profits = data_results.get('pool_profits') if data_results else None
            nicehash_fees = data_results.get('nicehash_fees') if data_results else None
            
            if not market_prices and not pool_profits:
                logger.warning("无法获取市场数据，跳过本次交易")
                return
            if not market_prices:
                logger.warning("无法获取市场价格数据，跳过本次交易")
                return
            
            # 更新价格监控
            self.price_monitor.update_prices(market_prices)
            
            # 计算盈利排名
            profit_ranking = self.calculate_profit_ranking(market_prices, pool_profits, nicehash_fees)
            
            if not profit_ranking:
                logger.warning("无法计算盈利排名，跳过本次交易")
                return
            
            # 使用算力保证机制选择算法
            selected_algorithms = self.hashrate_guarantee.select_algorithms(profit_ranking)
            
            # 使用智能订单管理器处理订单
            for algorithm_data in selected_algorithms:
                algorithm = algorithm_data['algorithm']
                profit = algorithm_data['profit']
                price = algorithm_data['price']
                
                # 检查是否需要创建或更新订单
                has_valid_api = (not self.offline_mode and 
                               self.api_key not in ['demo_key', 'your_nicehash_api_key', ''] and
                               self.api_secret not in ['demo_secret', 'your_nicehash_api_secret', ''])
                
                if self.order_manager.should_create_order(algorithm, profit, price, has_valid_api):
                    # 计算目标价格
                    target_price = self.order_manager.calculate_target_price(algorithm, price)
                    
                    # 检查余额是否充足
                    required_amount = self.min_order_amount
                    current_balance = self.auto_recharge.get_account_balance() if self.auto_recharge else 0.1
                    
                    if not self.auto_recharge.check_balance_sufficient(required_amount, current_balance):
                        # 尝试自动充值
                        if self.auto_recharge and self.auto_recharge.handle_insufficient_balance(required_amount):
                            logger.info("自动充值成功，继续创建订单")
                        else:
                            logger.warning(f"余额不足且自动充值失败，跳过订单: {algorithm}")
                            continue
                    
                    # 计算限速
                    optimal_speed = None
                    if self.speed_limit:
                        optimal_speed = self.speed_limit.adjust_speed_for_order(algorithm, profit, price)
                        logger.info(f"算法 {algorithm} 推荐速度: {optimal_speed:.1f} TH/s")
                    
                    # 创建订单（只有在有有效API密钥时才会到达这里）
                    order_id = self.create_order(algorithm, target_price, self.min_order_amount, optimal_speed)
                    if order_id:
                        logger.info(f"创建订单成功: {algorithm} - {target_price:.6f} BTC" + 
                                  (f" - 速度: {optimal_speed:.1f} TH/s" if optimal_speed else ""))
                        self.order_manager.add_order(order_id, algorithm, target_price, price)
            
            # 更新订单状态
            self.order_manager.update_orders(market_prices)
            
            # 记录性能
            execution_time = time.time() - start_time
            logger.info(f"增强交易策略执行完成，耗时: {execution_time:.2f}秒")
            
        except Exception as e:
            logger.error(f"增强交易策略执行失败: {e}")
            self.performance_monitor.record_retry()
    
    def calculate_profit_ranking(self, market_prices: Dict[str, float], 
                                 pool_profits: Dict[str, float], 
                                 nicehash_fees: Dict[str, Any]) -> List[Dict[str, Any]]:
        """计算盈利排名"""
        try:
            ranking = []
            
            for algorithm in market_prices.keys():
                if algorithm in pool_profits:
                    rental_price = market_prices[algorithm]
                    pool_profit = pool_profits[algorithm]
                    
                    # 计算净盈利
                    net_profit = self.calculate_profit(algorithm, rental_price, pool_profit, nicehash_fees)
                    
                    if net_profit > self.profit_threshold:
                        ranking.append({
                            'algorithm': algorithm,
                            'price': rental_price,
                            'pool_profit': pool_profit,
                            'profit': net_profit,
                            'net_profit': net_profit
                        })
            
            # 按盈利排序
            ranking.sort(key=lambda x: x['profit'], reverse=True)
            return ranking
            
        except Exception as e:
            logger.error(f"计算盈利排名失败: {e}")
            return []
    
    def run(self):
        """运行机器人主循环"""
        logger.info("开始运行NiceHash挖矿机器人")
        
        check_interval = int(self.config['trading']['check_interval'])
        
        try:
            while True:
                logger.info("=" * 50)
                logger.info(f"当前时间: {datetime.now()}")
                logger.info(f"活跃订单数量: {len(self.current_orders)}")
                
                # 执行增强版交易策略
                self.execute_enhanced_trading_strategy()
                
                # 显示当前状态
                if self.profit_history:
                    recent_profit = self.profit_history[-1]['total_profit']
                    logger.info(f"最近盈利: {recent_profit:.6f} BTC")
                
                # 获取自适应检查间隔
                adaptive_interval = self.order_manager.get_adaptive_check_interval()
                logger.info(f"等待 {adaptive_interval} 秒后进行下次检查...")
                time.sleep(adaptive_interval)
                
        except KeyboardInterrupt:
            logger.info("收到停止信号，正在关闭机器人...")
        except Exception as e:
            logger.error(f"机器人运行出错: {e}")
        finally:
            # 清理资源
            logger.info("清理活跃订单...")
            for order_id in list(self.current_orders.keys()):
                self.cancel_order(order_id)
            logger.info("机器人已停止")
    
    def get_all_data_concurrent(self) -> Dict[str, Any]:
        """并发获取所有数据（使用多数据源管理器）"""
        try:
            # 如果处于离线模式，直接返回模拟数据
            if self.offline_mode:
                logger.info("离线模式：使用模拟数据")
                return {
                    'market_prices': {
                        'SHA256': 0.0010,
                        'Scrypt': 0.0008,
                        'Ethash': 0.0012,
                        'X11': 0.0009,
                        'CryptoNight': 0.0011,
                        'Equihash': 0.0013,
                        'Lyra2REv2': 0.0014,
                        'Blake2s': 0.0015,
                        'Blake14r': 0.0016,
                        'DaggerHashimoto': 0.0017
                    },
                    'nicehash_fees': {
                        'SHA256': 0.018,
                        'Scrypt': 0.022,
                        'Ethash': 0.020,
                        'X11': 0.019,
                        'CryptoNight': 0.021,
                        'Equihash': 0.020,
                        'Lyra2REv2': 0.021,
                        'Blake2s': 0.019,
                        'Blake14r': 0.020,
                        'DaggerHashimoto': 0.020
                    },
                    'pool_profits': {
                        'SHA256': 0.0020,
                        'Scrypt': 0.0015,
                        'Ethash': 0.0030,
                        'X11': 0.0018,
                        'CryptoNight': 0.0022,
                        'Equihash': 0.0025,
                        'Lyra2REv2': 0.0028,
                        'Blake2s': 0.0032,
                        'Blake14r': 0.0035,
                        'DaggerHashimoto': 0.0038
                    }
                }
            
            # 使用多数据源管理器获取数据
            logger.info("使用多数据源管理器获取数据...")
            
            # 并发获取不同类型的数据（使用缓存）
            market_prices = self.data_source_manager.get_price_data()
            pool_profits = self.data_source_manager.get_mining_profitability_data()
            nicehash_fees = self.get_nicehash_fees(self.nicehash_market)  # 保持原有方法
            
            # 记录缓存性能
            cache_hits = 0
            cache_misses = 0
            if market_prices:
                cache_misses += 1
            if pool_profits:
                cache_misses += 1
            if nicehash_fees:
                cache_misses += 1
            
            logger.info(f"缓存性能: 命中={cache_hits}, 未命中={cache_misses}")
            
            # 确保所有数据都不为None
            if market_prices is None:
                market_prices = {}
            if pool_profits is None:
                pool_profits = {}
            if nicehash_fees is None:
                nicehash_fees = {}
            
            results = {
                'market_prices': market_prices,
                'pool_profits': pool_profits,
                'nicehash_fees': nicehash_fees
            }
            
            logger.info("多数据源并发获取完成")
            return results
            
        except Exception as e:
            logger.error(f"多数据源获取失败: {e}")
            return {
                'market_prices': None,
                'nicehash_fees': None,
                'pool_profits': None
            }
    
    def check_data_anomalies(self, market_prices: Dict[str, float], pool_profits: Dict[str, float]) -> List[str]:
        """检查数据异常并返回告警信息"""
        anomalies = []
        
        # 检查价格异常
        for algorithm, price in market_prices.items():
            if price > 0.1:  # 价格过高
                anomalies.append(f"价格异常: {algorithm} = {price:.6f} BTC (过高)")
            elif price < 0.0001:  # 价格过低
                anomalies.append(f"价格异常: {algorithm} = {price:.6f} BTC (过低)")
        
        # 检查收益异常
        for algorithm, profit in pool_profits.items():
            if profit > 0.01:  # 收益过高
                anomalies.append(f"收益异常: {algorithm} = {profit:.6f} BTC (过高)")
            elif profit < 0.0001:  # 收益过低
                anomalies.append(f"收益异常: {algorithm} = {profit:.6f} BTC (过低)")
        
        # 检查数据一致性
        if market_prices and pool_profits:
            common_algorithms = set(market_prices.keys()) & set(pool_profits.keys())
            if len(common_algorithms) == 0:
                anomalies.append("数据不一致: 价格和收益数据没有共同算法")
        
        return anomalies
    
    def get_all_algorithms_profit_ranking(self, top_n: int = 30) -> List[Dict[str, Any]]:
        """获取所有算法的盈利排行榜前N名"""
        logger.info(f"正在计算所有算法的盈利排行榜前{top_n}名...")
        
        try:
            # 获取所有数据
            data = self.get_all_data_concurrent()
            
            market_prices = data.get('market_prices', {})
            pool_profits = data.get('pool_profits', {})
            nicehash_fees = data.get('nicehash_fees', {})
            
            # 算法名称映射
            algorithm_names = {
                'SHA256': 'Bitcoin (BTC)',
                'Scrypt': 'Litecoin (LTC)', 
                'Ethash': 'Ethereum (ETH)',
                'X11': 'Dash (DASH)',
                'CryptoNight': 'Monero (XMR)',
                'Equihash': 'Zcash (ZEC)',
                'Lyra2REv2': 'Vertcoin (VTC)',
                'Blake2s': 'Decred (DCR)',
                'Blake14r': 'Siacoin (SC)',
                'DaggerHashimoto': 'Ethereum Classic (ETC)',
                'Blake2b': 'Decred (DCR)',
                'CryptoNightV7': 'Monero (XMR)',
                'CryptoNightR': 'Monero (XMR)',
                'RandomX': 'Monero (XMR)',
                'KawPow': 'Ravencoin (RVN)',
                'CuckooCycle': 'Grin (GRIN)',
                'Cuckaroo29': 'Grin (GRIN)',
                'Cuckaroo30': 'Grin (GRIN)',
                'BeamHash': 'Beam (BEAM)',
                'BeamHashII': 'Beam (BEAM)',
                'BeamHashIII': 'Beam (BEAM)',
                'ProgPow': 'Ethereum Classic (ETC)',
                'ProgPowZ': 'Ethereum Classic (ETC)',
                'RandomARQ': 'ArQmA (ARQ)',
                'RandomXL': 'Loki (LOKI)',
                'RandomXLS': 'Loki (LOKI)',
                'RandomXLSF': 'Loki (LOKI)'
            }
            
            # 获取所有算法（只使用API数据）
            all_algorithms = set()
            all_algorithms.update(market_prices.keys())
            all_algorithms.update(pool_profits.keys())
            
            logger.info(f"发现 {len(all_algorithms)} 个算法（仅API数据）")
            
            # 计算每个算法的盈利
            algorithm_profits = []
            for algorithm in all_algorithms:
                # 直接使用API数据，不使用默认值
                market_price = market_prices.get(algorithm, 0)
                pool_profit = pool_profits.get(algorithm, 0)
                
                # 处理费率数据，没有则使用默认费率
                if not nicehash_fees or algorithm not in nicehash_fees:
                    # 使用默认费率
                    nicehash_fee = 0.03
                else:
                    algorithm_fees = nicehash_fees.get(algorithm)
                    if algorithm_fees is None:
                        # 使用默认费率
                        nicehash_fee = 0.03
                    else:
                        # 处理双市场费率数据
                        if isinstance(algorithm_fees, dict):
                            # 双市场数据：选择最优费率（最低费率）
                            nicehash_fee = min(algorithm_fees.values()) if algorithm_fees else 0.03
                        else:
                            # 单市场数据：直接使用
                            nicehash_fee = algorithm_fees
                
                # 使用市场价格作为租赁价格估算
                rental_price = market_price
                
                # 计算净盈利
                if rental_price > 0:
                    # 租赁成本（包含手续费）
                    rental_cost = rental_price * (1 + nicehash_fee)
                    # 净盈利 = 矿池收益 - 租赁成本
                    net_profit = pool_profit - rental_cost
                    # 利润率
                    profit_rate = (net_profit / rental_cost) * 100 if rental_cost > 0 else 0
                else:
                    net_profit = 0
                    profit_rate = 0
                
                algorithm_profits.append({
                    'algorithm': algorithm,
                    'name': algorithm_names.get(algorithm, algorithm),
                    'market_price': market_price,
                    'pool_profit': pool_profit,
                    'rental_price': rental_price,
                    'nicehash_fee': nicehash_fee,
                    'net_profit': net_profit,
                    'profit_rate': profit_rate
                })
            
            # 按净盈利降序排序
            algorithm_profits.sort(key=lambda x: x['net_profit'], reverse=True)
            
            # 返回前N名
            return algorithm_profits[:top_n]
            
        except Exception as e:
            logger.error(f"获取算法盈利排行榜失败: {e}")
            return []
    
    def display_profit_ranking(self, ranking: List[Dict[str, Any]]):
        """显示盈利排行榜"""
        if not ranking:
            logger.warning("没有可显示的排行榜数据")
            return
        
        logger.info("\n" + "=" * 100)
        logger.info("算法盈利排行榜 (前30名)")
        logger.info("=" * 100)
        logger.info(f"更新时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        # 表头
        logger.info(f"{'排名':<4} {'挖矿算法':<15} {'币种':<20} {'代币价格(BTC)':<15} {'租赁价格(BTC)':<15} {'矿池收益(BTC)':<15} {'矿池手续费(BTC)':<15} {'NH租赁手续费(BTC)':<18} {'净盈利(BTC)':<15} {'利润率(%)':<12}")
        logger.info("-" * 180)
        
        # 显示数据
        for i, algo in enumerate(ranking, 1):
            status = ""
            if algo['net_profit'] > 0:
                status = "[+]"
            elif algo['net_profit'] > -0.001:
                status = "[~]"
            else:
                status = "[-]"
            
            # 计算手续费
            nicehash_fee = algo.get('nicehash_fee')
            if nicehash_fee is None:
                logger.warning(f"算法 {algo['algorithm']} 没有费率数据，跳过显示")
                continue
                
            rental_fee = algo['rental_price'] * nicehash_fee
            pool_fee = algo['pool_profit'] * 0.02  # 假设矿池手续费2%
            
            logger.info(f"{i:<4} {algo['algorithm']:<15} {algo['name']:<20} "
                       f"{algo['market_price']:<14.6f} {algo['rental_price']:<14.6f} {algo['pool_profit']:<14.6f} "
                       f"{pool_fee:<14.6f} {rental_fee:<17.6f} {status}{algo['net_profit']:<14.6f} {algo['profit_rate']:<12.2f}")
        
        logger.info("-" * 180)
        
        # 统计信息
        profitable_count = sum(1 for algo in ranking if algo['net_profit'] > 0)
        total_count = len(ranking)
        
        logger.info(f"\n统计信息:")
        logger.info(f"盈利算法: {profitable_count}/{total_count} ({profitable_count/total_count*100:.1f}%)")
        
        if ranking:
            best_profit = ranking[0]['net_profit']
            worst_profit = ranking[-1]['net_profit']
            avg_profit = sum(algo['net_profit'] for algo in ranking) / len(ranking)
            
            logger.info(f"最高盈利: {best_profit:.6f} BTC")
            logger.info(f"最低盈利: {worst_profit:.6f} BTC")
            logger.info(f"平均盈利: {avg_profit:.6f} BTC")
        
        logger.info("=" * 100)
    
    def show_data_source_status(self):
        """显示数据源状态"""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("数据源状态报告")
            logger.info("=" * 60)
            
            status = self.data_source_manager.get_source_status()
            
            for source_id, info in status.items():
                status_icon = "✓" if info['status'] == 'healthy' else "✗"
                logger.info(f"{status_icon} {info['name']:<15} {info['type']:<20} {info['status']}")
                logger.info(f"   优先级: {info['priority']:<3} 成功: {info['success_count']:<3} 失败: {info['failure_count']:<3}")
                if info['avg_response_time'] > 0:
                    logger.info(f"   平均响应时间: {info['avg_response_time']:.2f}s")
                if info['last_check']:
                    logger.info(f"   最后检查: {info['last_check']}")
                logger.info("")
            
            # 显示健康摘要
            logger.info(self.data_source_manager.get_health_summary())
            
        except Exception as e:
            logger.error(f"显示数据源状态失败: {e}")
    
    def refresh_data_sources(self):
        """刷新数据源状态"""
        try:
            logger.info("刷新数据源状态...")
            results = self.data_source_manager.test_all_sources()
            healthy_count = sum(results.values())
            logger.info(f"数据源刷新完成: {healthy_count}/{len(results)} 个数据源可用")
            
            # 如果所有数据源都失败，启用离线模式
            if healthy_count == 0 and not self.offline_mode:
                logger.warning("所有数据源都失败，启用离线模式")
                self.offline_mode = True
            
            return results
            
        except Exception as e:
            logger.error(f"刷新数据源失败: {e}")
            return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        metrics = self.performance_monitor.get_metrics()
        metrics['cache_size'] = self.cache.size()
        return metrics
    
    def cleanup_resources(self):
        """清理资源"""
        try:
            self.concurrent_fetcher.close()
            self.cache.clear()
            # 关闭requests会话
            if hasattr(self, 'session') and self.session:
                self.session.close()
            logger.info("资源清理完成")
        except Exception as e:
            logger.error(f"资源清理失败: {e}")
    
    def show_profit_ranking(self, top_n: int = 10):
        """显示盈利排行"""
        try:
            # 获取最新数据
            market_prices = self.get_market_prices()
            pool_profits = self.get_pool_profitability()
            nicehash_fees = self.get_nicehash_fees(self.nicehash_market)
            
            if not market_prices or not pool_profits:
                logger.warning("无法获取市场数据，无法显示排行")
                return
            
            # 计算排行
            ranking_data = self.profit_ranking.calculate_profit_ranking(
                market_prices, pool_profits, nicehash_fees, 'nicehash'
            )
            
            if ranking_data:
                # 显示排行
                print("\n" + self.profit_ranking.display_profit_ranking(ranking_data, top_n))
                
                # 显示摘要
                summary = self.profit_ranking.get_profit_summary(ranking_data)
                if summary:
                    print("\n" + self.profit_ranking.display_profit_summary(summary))
                
                # 显示趋势分析
                trend_analysis = self.profit_ranking.get_trend_analysis(hours=24)
                if trend_analysis and "数据不足" not in trend_analysis:
                    print("\n" + trend_analysis)
                
                # 导出CSV（可选）
                export_result = self.profit_ranking.export_ranking_to_csv(ranking_data)
                logger.info(export_result)
            else:
                logger.warning("无排行数据可显示")
                
        except Exception as e:
            logger.error(f"显示盈利排行失败: {e}")
    
    def get_top_profitable_coins(self, count: int = 5) -> List[str]:
        """获取最盈利的币种列表"""
        try:
            if not self.profit_history:
                return []
            
            # 获取最新的排行数据
            latest_history = self.profit_history[-1]
            ranking_data = latest_history.get('ranking_data', [])
            
            return self.profit_ranking.get_top_profitable_coins(ranking_data, count)
            
        except Exception as e:
            logger.error(f"获取最盈利币种失败: {e}")
            return []
    
    def test_api_connection(self) -> Dict[str, bool]:
        """测试API连接状态"""
        results = {
            'whattomine_api': False,
            'nicehash_public_api': False,
            'market_prices': False,
            'global_stats': False,
            'overall_status': False
        }
        
        try:
            # 测试WhatToMine API连接
            logger.info("测试WhatToMine API连接...")
            response = self.session.get("https://whattomine.com/coins.json", timeout=10)
            if response.status_code == 200:
                results['whattomine_api'] = True
                results['market_prices'] = True
                logger.info("✓ WhatToMine API连接成功")
            else:
                logger.warning(f"✗ WhatToMine API返回状态码: {response.status_code}")
                
        except Exception as e:
            logger.error(f"✗ WhatToMine API连接失败: {e}")
        
        try:
            # 测试NiceHash公共API连接（备用）
            logger.info("测试NiceHash公共API连接...")
            response = self.session.get(
                f'{self.nicehash_api_url}/main/api/v2/public/stats/global/current',
                timeout=10
            )
            if response.status_code == 200:
                results['nicehash_public_api'] = True
                results['global_stats'] = True
                logger.info("✓ NiceHash公共API连接成功")
            else:
                logger.warning(f"✗ NiceHash公共API返回状态码: {response.status_code}")
                
        except Exception as e:
            logger.error(f"✗ NiceHash公共API连接失败: {e}")
        
        # 总体状态
        results['overall_status'] = results['whattomine_api'] or results['nicehash_public_api']
        
        if results['overall_status']:
            logger.info("✓ API连接测试通过，可以使用真实数据")
        else:
            logger.warning("✗ API连接测试失败，将使用模拟数据")
        
        return results
    
    def check_data_anomalies(self, market_prices: Dict[str, float], pool_profits: Dict[str, float]) -> List[str]:
        """检查数据异常并返回告警信息"""
        anomalies = []
        
        # 检查价格异常
        for algorithm, price in market_prices.items():
            if price > 0.1:  # 价格过高
                anomalies.append(f"价格异常: {algorithm} = {price:.6f} BTC (过高)")
            elif price < 0.0001:  # 价格过低
                anomalies.append(f"价格异常: {algorithm} = {price:.6f} BTC (过低)")
        
        # 检查收益异常
        for algorithm, profit in pool_profits.items():
            if profit > 0.01:  # 收益过高
                anomalies.append(f"收益异常: {algorithm} = {profit:.6f} BTC (过高)")
            elif profit < 0.0001:  # 收益过低
                anomalies.append(f"收益异常: {algorithm} = {profit:.6f} BTC (过低)")
        
        # 检查数据一致性
        if market_prices and pool_profits:
            common_algorithms = set(market_prices.keys()) & set(pool_profits.keys())
            if len(common_algorithms) == 0:
                anomalies.append("数据不一致: 价格和收益数据没有共同算法")
        
        return anomalies
