#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
算法盈利排行榜测试脚本
"""

import sys
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from mining_bot import NiceHashBot

def main():
    """主函数"""
    print("算法盈利排行榜系统")
    print("=" * 60)
    
    try:
        # 创建机器人实例
        bot = NiceHashBot()
        
        # 获取排行榜
        print("正在获取算法盈利排行榜...")
        ranking = bot.get_all_algorithms_profit_ranking(30)
        
        # 显示排行榜
        bot.display_profit_ranking(ranking)
        
    except Exception as e:
        print(f"✗ 系统运行失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()