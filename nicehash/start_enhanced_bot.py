# 增强版启动脚本
# 用于启动NiceHash增强版挖矿机器人

import sys
import os
import logging
from pathlib import Path
from console_encoding import fix_windows_console

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 先修复控制台编码，避免导入期间输出报错
fix_windows_console(prefer_utf8=True, ignore_errors=True)

from mining_bot import NiceHashBot

def main():
    """主启动函数"""
    # 修复Windows控制台编码，避免GBK报错
    fix_windows_console(prefer_utf8=True, ignore_errors=True)
    print("=" * 60)
    print("NiceHash 增强版自动化挖矿机器人")
    print("=" * 60)
    print("新功能:")
    print("  • 动态价格监控和自适应检查间隔")
    print("  • 智能订单策略和价格微调")
    print("  • 算力保证机制和备用算法")
    print("  • 算法性能跟踪和优化")
    print("=" * 60)
    print()
    
    # 检查配置文件
    config_file = "enhanced_config.ini"
    if not os.path.exists(config_file):
        print(f"增强版配置文件 {config_file} 不存在")
        print("请先创建增强版配置文件")
        return
    
    # 检查依赖
    try:
        import requests
        import configparser
        print("依赖检查通过")
    except ImportError as e:
        print(f"缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return
    
    print("正在启动增强版机器人...")
    print()
    
    try:
        # 创建并运行机器人
        bot = NiceHashBot(config_file)
        
        # 检查是否启用增强策略
        if bot.config.getboolean('trading', 'enable_enhanced_strategy', fallback=False):
            print("增强交易策略已启用")
        else:
            print("增强交易策略未启用，将使用标准策略")
        
        if bot.config.getboolean('trading', 'enable_dynamic_monitoring', fallback=False):
            print("动态价格监控已启用")
        else:
            print("动态价格监控未启用")
        
        if bot.config.getboolean('trading', 'enable_smart_orders', fallback=False):
            print("智能订单管理已启用")
        else:
            print("智能订单管理未启用")
        
        if bot.config.getboolean('trading', 'enable_hashrate_guarantee', fallback=False):
            print("算力保证机制已启用")
        else:
            print("算力保证机制未启用")
        
        print()
        print("开始运行增强版机器人...")
        print("按 Ctrl+C 停止机器人")
        print()
        
        bot.run()
    except KeyboardInterrupt:
        print("\n增强版机器人已停止")
    except Exception as e:
        print(f"增强版机器人运行出错: {e}")
        logging.error(f"增强版机器人运行出错: {e}")

if __name__ == "__main__":
    main()
