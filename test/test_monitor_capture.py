#!/usr/bin/env python3
"""
显示器截图测试脚本
专门用于测试和验证多显示器截图功能
"""

import sys
import os
import time

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from server import DesktopScreenshotGenerator
    import win32api
    import win32con
    
    print("=== 显示器截图测试 ===")
    print()
    
    # 创建截图生成器
    generator = DesktopScreenshotGenerator()
    
    # 更新显示器信息
    print("正在检测显示器...")
    generator.update_monitor_info()
    
    print(f"\n检测到 {len(generator.monitors)} 个显示器:")
    for i, monitor in enumerate(generator.monitors):
        print(f"  显示器 {i + 1}: {monitor['width']}x{monitor['height']} 位置({monitor['left']},{monitor['top']}) {'(主显示器)' if monitor['primary'] else ''}")
    
    print("\n=== 系统信息 ===")
    virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    
    primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
    
    monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)
    
    print(f"显示器数量: {monitor_count}")
    print(f"虚拟桌面: {virtual_width}x{virtual_height} 位置({virtual_left},{virtual_top})")
    print(f"主显示器: {primary_width}x{primary_height}")
    
    print("\n=== 测试截图 ===")
    
    # 测试每个显示器
    for i in range(len(generator.monitors)):
        print(f"\n正在测试显示器 {i + 1}...")
        monitor = generator.monitors[i]
        
        print(f"  配置: {monitor['width']}x{monitor['height']} 位置({monitor['left']},{monitor['top']})")
        print(f"  区域: ({monitor['left']},{monitor['top']},{monitor['right']},{monitor['bottom']})")
        
        try:
            # 捕获截图
            start_time = time.time()
            img = generator.capture_single_monitor(i)
            end_time = time.time()
            
            print(f"  截图成功: {img.width}x{img.height}")
            print(f"  耗时: {(end_time - start_time) * 1000:.2f}ms")
            
            # 保存测试图片
            test_filename = f"test_monitor_{i + 1}.png"
            img.save(test_filename)
            print(f"  已保存到: {test_filename}")
            
        except Exception as e:
            print(f"  截图失败: {e}")
    
    print("\n=== 测试完成 ===")
    print("请检查生成的测试图片，确认每个显示器的截图是否正确。")
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所需依赖: pip install fastapi uvicorn pillow pywin32")
except Exception as e:
    print(f"测试失败: {e}")
    import traceback
    traceback.print_exc() 