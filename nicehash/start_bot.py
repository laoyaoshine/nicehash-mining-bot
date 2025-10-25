# 启动脚本
# 用于启动NiceHash挖矿机器人

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
    print("NiceHash 自动化挖矿机器人")
    print("=" * 60)
    print()
    
    # 检查配置文件
    config_file = "config.ini"
    if not os.path.exists(config_file):
        print(f"❌ 配置文件 {config_file} 不存在")
        print("请先运行程序创建默认配置文件，然后编辑配置文件")
        return
    
    # 检查依赖
    try:
        import requests
        import configparser
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install -r requirements.txt")
        return
    
    print("🚀 正在启动机器人...")
    print()
    
    try:
        # 创建并运行机器人
        bot = NiceHashBot(config_file)
        bot.run()
    except KeyboardInterrupt:
        print("\n👋 机器人已停止")
    except Exception as e:
        print(f"❌ 机器人运行出错: {e}")
        logging.error(f"机器人运行出错: {e}")

if __name__ == "__main__":
    main()
