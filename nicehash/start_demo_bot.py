#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NiceHash 挖矿机器人演示模式启动脚本
此脚本使用演示配置，不会创建真实订单，仅用于展示功能
"""

import os
import sys
import logging
import time
from datetime import datetime

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """主函数"""
    print("=" * 60)
    print("NiceHash 挖矿机器人 - 演示模式")
    print("=" * 60)
    print("注意: 此模式不会创建真实订单，仅用于功能演示")
    print("=" * 60)
    print()
    
    # 检查配置文件
    config_file = "demo_config.ini"
    if not os.path.exists(config_file):
        print(f"演示配置文件 {config_file} 不存在")
        print("请确保配置文件存在")
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
    
    print("正在启动演示版机器人...")
    print()
    
    try:
        # 创建并运行机器人
        from mining_bot import NiceHashBot
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
        print("开始运行演示版机器人...")
        print("按 Ctrl+C 停止机器人")
        print()
        
        bot.run()
    except KeyboardInterrupt:
        print("\n演示版机器人已停止")
    except Exception as e:
        print(f"演示版机器人运行出错: {e}")
        logging.error(f"演示版机器人运行出错: {e}")

if __name__ == "__main__":
    main()
