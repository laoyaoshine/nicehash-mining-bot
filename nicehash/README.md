# NiceHash 自动化挖矿机器人

一个智能的NiceHash挖矿机器人，支持多数据源、双市场（EU/US）费率获取、自动充值、智能限速和自动化交易策略。

## 🚀 功能特点

### 📊 多数据源支持
- **WhatToMine** - 矿池收益数据
- **CoinGecko** - 加密货币价格数据  
- **CryptoCompare** - 价格和交易数据
- **CoinMarketCap** - 市场数据
- **NiceHash** - 实时费率和订单数据

### 🌍 双市场支持
- **EU市场** - 欧洲市场费率
- **US市场** - 美国市场费率
- **自动选择** - 智能选择最优市场
- **双市场下单** - 同时在EU和US市场下单

### 💰 自动充值功能
- **智能检测** - 自动检测余额不足
- **自动充值** - 订单金额不足时自动充值
- **冷却机制** - 防止频繁充值
- **日限制** - 每日最大充值次数限制

### ⚡ 智能限速管理
- **自适应限速** - 根据盈利水平和市场波动性自动调整
- **动态计算** - 不同算法使用不同的速度策略
- **智能调整** - 高盈利时提高速度，低盈利时降低速度

### 📈 增强交易策略
- **动态价格监控** - 自适应检查间隔
- **智能订单管理** - 价格微调和优先级
- **算力保证机制** - 确保连续挖矿
- **风险控制** - 自动止损和盈利保护

### 🔧 自动化功能
- **智能下单** - 基于盈利分析自动创建订单
- **价格更新** - 实时调整订单价格
- **订单管理** - 自动取消不盈利订单
- **限速保护** - API调用频率控制

## 📋 系统要求

- Python 3.7+
- Windows/Linux/macOS
- 网络连接（用于API调用）

## 🛠️ 安装步骤

### 1. 克隆仓库

```bash
git clone https://github.com/laoyaoshine/nicehash-mining-bot.git
cd nicehash-mining-bot
```

### 2. 安装依赖

```bash
pip install -r nicehash/requirements.txt
```

### 3. 配置设置

复制并编辑配置文件：

```bash
cp nicehash/config.ini.example nicehash/config.ini
```

编辑 `config.ini` 文件：

```ini
# NiceHash API配置
api_key = your_nicehash_api_key
api_secret = your_nicehash_api_secret
org_id = your_nicehash_org_id

# 交易设置
profit_threshold = 0.01
max_orders = 5
order_amount = 0.001

# 市场选择
nicehash_market = both  # auto, EU, US, both

# 离线模式（测试用）
offline_mode = false
```

## 🚀 使用方法

### 启动基础版机器人

```bash
cd nicehash
python start_bot.py
```

### 启动增强版机器人（推荐）

```bash
cd nicehash
python start_enhanced_bot.py
```

### 启动演示版机器人（无需API密钥）

```bash
cd nicehash
python start_demo_bot.py
```

### 查看排行榜

```bash
python show_ranking.py
```

### 运行盈利分析

```bash
python profit_ranking.py
```

## 📊 功能模块

### 核心模块
- `mining_bot.py` - 主机器人逻辑
- `data_source_manager.py` - 数据源管理
- `profit_ranking.py` - 盈利排行计算
- `pool_api_adapter.py` - 矿池API适配器

### 增强功能模块
- `enhanced_trading_strategy_en.py` - 增强交易策略
- `auto_recharge_manager.py` - 自动充值管理器
- `speed_limit_manager.py` - 智能限速管理器

### 工具模块
- `cache_utils.py` - 缓存工具
- `console_encoding.py` - 控制台编码处理
- `multi_pool_comparator.py` - 多矿池比较

## 🔧 配置说明

### API配置

```ini
# NiceHash API密钥（必需）
api_key = your_api_key
api_secret = your_api_secret
org_id = your_org_id

# 数据源API密钥（可选）
coingecko_api_key = your_coingecko_key
cryptocompare_api_key = your_cryptocompare_key
coinmarketcap_api_key = your_coinmarketcap_key
```

### 交易设置

```ini
# 盈利阈值（BTC）
profit_threshold = 0.01

# 最大订单数
max_orders = 5

# 订单金额（BTC）
order_amount = 0.001

# 市场选择
nicehash_market = both  # auto, EU, US, both
```

### 增强功能配置

```ini
# 自动充值设置
auto_recharge_enabled = true
auto_recharge_threshold = 0.01
auto_recharge_amount = 0.1
min_balance_threshold = 0.05

# 限速设置
max_speed_limit = 1000
min_speed_limit = 100

# 增强策略设置
enable_enhanced_strategy = true
enable_dynamic_monitoring = true
enable_smart_orders = true
enable_hashrate_guarantee = true
```

## 📈 数据源优先级

1. **价格数据**: CoinGecko → CryptoCompare → CoinMarketCap → WhatToMine
2. **收益数据**: WhatToMine → NiceHash
3. **费率数据**: NiceHash EU/US → 默认3%

## 🛡️ 安全特性

- **API密钥保护** - 配置文件加密存储
- **限速控制** - 防止API调用过频
- **错误处理** - 完善的异常处理机制
- **资源清理** - 自动清理网络连接和缓存
- **余额保护** - 自动充值防止订单失败

## 📊 监控和日志

### 日志级别
- `INFO` - 一般信息
- `WARNING` - 警告信息
- `ERROR` - 错误信息
- `DEBUG` - 调试信息

### 性能指标
- API响应时间
- 缓存命中率
- 订单执行成功率
- 盈利统计
- 自动充值统计
- 限速调整记录

## 🔄 更新日志

### v2.0.0 (2025-10-24)

#### 🆕 新增功能
- ✅ **自动充值管理器** - 余额不足时自动充值
- ✅ **智能限速管理器** - 根据盈利情况调整速度
- ✅ **增强交易策略** - 动态价格监控和智能订单管理
- ✅ **算力保证机制** - 确保连续挖矿
- ✅ **演示模式** - 无需API密钥即可测试功能

#### 🔧 改进功能
- ✅ **多数据源优化** - 提高数据获取稳定性
- ✅ **缓存系统优化** - 提高性能
- ✅ **错误处理完善** - 更好的异常处理
- ✅ **配置文件增强** - 更多可配置选项

#### 📚 文档更新
- ✅ **增强功能文档** - 详细的功能说明
- ✅ **配置指南** - 完整的配置说明
- ✅ **使用示例** - 多种使用场景

### v1.0.0 (2025-10-23)

- ✅ 多数据源支持
- ✅ 双市场（EU/US）费率获取
- ✅ 30个算法排名功能
- ✅ 自动化交易策略
- ✅ 智能订单管理
- ✅ 实时盈利分析

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情。

## ⚠️ 免责声明

本软件仅供学习和研究使用。使用本软件进行实际交易的风险由用户自行承担。开发者不对任何损失负责。

## 📞 支持

如有问题或建议，请：

- 创建 Issue
- 发送邮件至 your-email@example.com
- 加入讨论群组

---

**⭐ 如果这个项目对您有帮助，请给它一个星标！**

## 快速开始

1. **克隆仓库**: `git clone https://github.com/laoyaoshine/nicehash-mining-bot.git`
2. **安装依赖**: `pip install -r nicehash/requirements.txt`
3. **配置API**: 编辑 `nicehash/config.ini` 文件
4. **启动机器人**: `python nicehash/start_enhanced_bot.py`

## 功能对比

| 功能 | 基础版 | 增强版 | 演示版 |
|------|--------|--------|--------|
| 多数据源 | ✅ | ✅ | ✅ |
| 双市场支持 | ✅ | ✅ | ✅ |
| 自动充值 | ❌ | ✅ | ❌ |
| 智能限速 | ❌ | ✅ | ❌ |
| 动态监控 | ❌ | ✅ | ❌ |
| 算力保证 | ❌ | ✅ | ❌ |
| 无需API | ❌ | ❌ | ✅ |