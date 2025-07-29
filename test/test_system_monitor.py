#!/usr/bin/env python3
"""
系统监控功能测试脚本
"""

import sys
import os

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import psutil
    from server import SystemMonitor
    
    print("=== 系统监控功能测试 ===")
    print()
    
    # 创建系统监控器
    monitor = SystemMonitor()
    
    print("正在测试系统资源监控...")
    
    # 测试系统资源检查
    monitor.check_system_resources()
    
    # 获取系统信息
    system_info = monitor.get_system_info()
    
    print(f"内存使用率: {system_info['memory_usage']}%")
    print(f"CPU使用率: {system_info['cpu_usage']}%")
    print(f"磁盘使用率: {system_info['disk_usage']}%")
    print(f"最后检查时间: {system_info['last_check']}")
    
    # 获取更详细的系统信息
    print("\n=== 详细系统信息 ===")
    
    # 内存信息
    memory = psutil.virtual_memory()
    print(f"内存:")
    print(f"  总内存: {memory.total / (1024**3):.2f} GB")
    print(f"  可用内存: {memory.available / (1024**3):.2f} GB")
    print(f"  已用内存: {memory.used / (1024**3):.2f} GB")
    print(f"  使用率: {memory.percent:.1f}%")
    
    # CPU信息
    print(f"\nCPU:")
    print(f"  核心数: {psutil.cpu_count()}")
    print(f"  逻辑核心数: {psutil.cpu_count(logical=True)}")
    cpu_freq = psutil.cpu_freq()
    if cpu_freq:
        print(f"  当前频率: {cpu_freq.current:.0f} MHz")
        print(f"  最大频率: {cpu_freq.max:.0f} MHz")
    print(f"  使用率: {psutil.cpu_percent(interval=1):.1f}%")
    
    # 磁盘信息
    print(f"\n磁盘:")
    disk = psutil.disk_usage('/')
    print(f"  总容量: {disk.total / (1024**3):.2f} GB")
    print(f"  已用空间: {disk.used / (1024**3):.2f} GB")
    print(f"  可用空间: {disk.free / (1024**3):.2f} GB")
    print(f"  使用率: {(disk.used / disk.total) * 100:.1f}%")
    
    print("\n=== 测试完成 ===")
    print("系统监控功能正常工作！")
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所需依赖: pip install psutil")
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc() 