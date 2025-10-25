# 性能优化演示脚本
# 展示缓存、并发、重试等优化功能

import sys
import time
from pathlib import Path

# 添加当前目录到Python路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from cache_utils import TTLCache, RetryManager, ConcurrentFetcher, PerformanceMonitor
from mining_bot import NiceHashBot

def demo_cache_performance():
    """演示缓存性能"""
    print("=" * 60)
    print("🚀 缓存性能演示")
    print("=" * 60)
    
    # 创建缓存
    cache = TTLCache(default_ttl=5)
    
    # 测试缓存设置和获取
    print("1. 设置缓存数据...")
    cache.set("market_data", {"BTC": 0.001, "ETH": 0.002})
    cache.set("fee_data", {"SHA256": 0.02, "Ethash": 0.02})
    
    print("2. 获取缓存数据...")
    market_data = cache.get("market_data")
    fee_data = cache.get("fee_data")
    
    print(f"   市场数据: {market_data}")
    print(f"   费率数据: {fee_data}")
    
    # 测试缓存过期
    print("3. 测试缓存过期...")
    cache.set("temp_data", "临时数据", ttl=2)
    print(f"   立即获取: {cache.get('temp_data')}")
    
    print("   等待3秒...")
    time.sleep(3)
    print(f"   过期后获取: {cache.get('temp_data')}")
    
    print(f"4. 当前缓存大小: {cache.size()}")
    print("✅ 缓存演示完成\n")

def demo_retry_mechanism():
    """演示重试机制"""
    print("=" * 60)
    print("🔄 重试机制演示")
    print("=" * 60)
    
    # 创建重试管理器
    retry_manager = RetryManager(max_attempts=3, backoff_factor=1.0)
    
    # 测试成功的情况
    print("1. 测试成功情况...")
    def success_func():
        return "API调用成功"
    
    result = retry_manager.retry_with_backoff(success_func)
    print(f"   结果: {result}")
    
    # 测试失败的情况
    print("2. 测试失败重试...")
    attempt_count = 0
    def fail_func():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise Exception(f"第{attempt_count}次失败")
        return "第3次成功"
    
    try:
        result = retry_manager.retry_with_backoff(fail_func)
        print(f"   最终结果: {result}")
        print(f"   总尝试次数: {attempt_count}")
    except Exception as e:
        print(f"   最终失败: {e}")
    
    print("✅ 重试机制演示完成\n")

def demo_performance_monitoring():
    """演示性能监控"""
    print("=" * 60)
    print("📊 性能监控演示")
    print("=" * 60)
    
    # 创建性能监控器
    monitor = PerformanceMonitor()
    
    # 模拟一些操作
    print("1. 模拟API调用...")
    for i in range(5):
        response_time = 0.1 + i * 0.05  # 模拟响应时间
        monitor.record_api_call(response_time)
        print(f"   API调用 {i+1}: {response_time:.3f}秒")
    
    print("2. 模拟缓存操作...")
    for i in range(8):
        if i % 3 == 0:
            monitor.record_cache_miss()
            print("   缓存未命中")
        else:
            monitor.record_cache_hit()
            print("   缓存命中")
    
    print("3. 模拟重试...")
    for i in range(2):
        monitor.record_retry()
        print(f"   重试 {i+1}")
    
    # 显示性能指标
    print("4. 性能指标:")
    metrics = monitor.get_metrics()
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.3f}")
        else:
            print(f"   {key}: {value}")
    
    print("✅ 性能监控演示完成\n")

def demo_concurrent_fetching():
    """演示并发获取"""
    print("=" * 60)
    print("⚡ 并发获取演示")
    print("=" * 60)
    
    # 创建并发获取器
    fetcher = ConcurrentFetcher(max_workers=2, timeout=10)
    
    print("1. 创建并发获取器...")
    print(f"   最大工作线程: 2")
    print(f"   超时时间: 10秒")
    
    print("2. 模拟并发数据获取...")
    print("   注意: 实际API调用需要网络连接")
    
    # 清理资源
    fetcher.close()
    print("✅ 并发获取演示完成\n")

def demo_optimized_bot():
    """演示优化后的机器人"""
    print("=" * 60)
    print("🤖 优化机器人演示")
    print("=" * 60)
    
    try:
        # 创建机器人实例
        print("1. 创建机器人实例...")
        bot = NiceHashBot("config.ini")
        print("   ✅ 机器人创建成功")
        
        # 显示性能指标
        print("2. 获取性能指标...")
        metrics = bot.get_performance_metrics()
        print("   性能指标:")
        for key, value in metrics.items():
            if isinstance(value, float):
                print(f"     {key}: {value:.3f}")
            else:
                print(f"     {key}: {value}")
        
        # 测试并发数据获取
        print("3. 测试并发数据获取...")
        print("   注意: 需要网络连接才能获取真实数据")
        data_results = bot.get_all_data_concurrent()
        print(f"   获取结果: {list(data_results.keys())}")
        
        # 清理资源
        print("4. 清理资源...")
        bot.cleanup_resources()
        print("   ✅ 资源清理完成")
        
    except Exception as e:
        print(f"   ❌ 机器人演示失败: {e}")
    
    print("✅ 优化机器人演示完成\n")

def main():
    """主函数"""
    print("🚀 NiceHash 挖矿机器人 - 性能优化演示")
    print("=" * 80)
    print()
    
    try:
        # 运行各个演示
        demo_cache_performance()
        demo_retry_mechanism()
        demo_performance_monitoring()
        demo_concurrent_fetching()
        demo_optimized_bot()
        
        print("=" * 80)
        print("🎉 所有演示完成！")
        print("=" * 80)
        print()
        print("💡 优化功能总结:")
        print("   • 缓存系统：减少API调用，提高响应速度")
        print("   • 重试机制：网络错误时自动重试，提高稳定性")
        print("   • 性能监控：实时监控系统性能指标")
        print("   • 并发处理：并行获取数据，减少等待时间")
        print("   • 资源管理：自动清理资源，防止内存泄漏")
        print()
        print("🔧 配置建议:")
        print("   • cache_ttl_seconds = 60 (缓存1分钟)")
        print("   • max_concurrent_requests = 3 (最多3个并发)")
        print("   • retry_max_attempts = 3 (最多重试3次)")
        print("   • log_level = INFO (记录重要信息)")
        
    except KeyboardInterrupt:
        print("\n👋 演示已停止")
    except Exception as e:
        print(f"❌ 演示出错: {e}")

if __name__ == "__main__":
    main()
