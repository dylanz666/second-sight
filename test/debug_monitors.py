#!/usr/bin/env python3
"""
详细的显示器诊断工具
使用多种方法检测Windows显示器配置
"""

import sys
import os

try:
    import win32api
    import win32con
    import win32gui
    import win32ui
    from ctypes import windll, byref, c_int, c_uint, c_char_p, Structure, POINTER
    from ctypes.wintypes import RECT, DWORD, BOOL, HMONITOR, HDC, HWND, LPARAM
    
    print("=== Windows显示器详细诊断 ===")
    print()
    
    # 方法1: 使用GetSystemMetrics获取基本信息
    print("=== 方法1: GetSystemMetrics ===")
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
    print()
    
    # 方法2: 使用EnumDisplayMonitors获取详细信息
    print("=== 方法2: EnumDisplayMonitors ===")
    
    try:
        # 尝试使用win32gui.EnumDisplayMonitors
        if hasattr(win32gui, 'EnumDisplayMonitors'):
            def enum_monitor_callback(hMonitor, hdcMonitor, lprcMonitor, dwData):
                monitor_info = {
                    'handle': hMonitor,
                    'left': lprcMonitor[0],
                    'top': lprcMonitor[1],
                    'right': lprcMonitor[2],
                    'bottom': lprcMonitor[3],
                    'width': lprcMonitor[2] - lprcMonitor[0],
                    'height': lprcMonitor[3] - lprcMonitor[1],
                    'primary': (lprcMonitor[0] == 0 and lprcMonitor[1] == 0)
                }
                
                # 获取显示器设备名称
                try:
                    info = win32gui.GetMonitorInfo(hMonitor)
                    monitor_info['device_name'] = info.get('Device', 'Unknown')
                    monitor_info['monitor_name'] = info.get('Monitor', 'Unknown')
                    monitor_info['work_area'] = info.get('Work', None)
                except:
                    monitor_info['device_name'] = 'Unknown'
                    monitor_info['monitor_name'] = 'Unknown'
                    monitor_info['work_area'] = None
                
                print(f"显示器 {len(enum_monitor_callback.monitors) + 1}:")
                print(f"  句柄: {hMonitor}")
                print(f"  位置: ({monitor_info['left']}, {monitor_info['top']}, {monitor_info['right']}, {monitor_info['bottom']})")
                print(f"  尺寸: {monitor_info['width']}x{monitor_info['height']}")
                print(f"  主显示器: {'是' if monitor_info['primary'] else '否'}")
                print(f"  设备名: {monitor_info['device_name']}")
                print(f"  显示器名: {monitor_info['monitor_name']}")
                if monitor_info['work_area']:
                    print(f"  工作区: {monitor_info['work_area']}")
                print()
                
                enum_monitor_callback.monitors.append(monitor_info)
                return True
            
            enum_monitor_callback.monitors = []
            win32gui.EnumDisplayMonitors(None, None, enum_monitor_callback, 0)
        else:
            print("EnumDisplayMonitors不可用，跳过此方法")
    except Exception as e:
        print(f"EnumDisplayMonitors失败: {e}")
        print("跳过此方法")
    
    print()
    
    # 方法3: 使用EnumDisplaySettings获取每个显示器的详细信息
    print("=== 方法3: EnumDisplaySettings ===")
    
    def get_display_settings():
        try:
            # 获取主显示器的设备名称
            device_name = win32api.EnumDisplayDevices(None, 0)
            print(f"主显示器设备: {device_name.DeviceName}")
            
            # 获取所有显示器设备
            i = 0
            while True:
                try:
                    device = win32api.EnumDisplayDevices(None, i)
                    if not device.DeviceName:
                        break
                    
                    print(f"显示器设备 {i}: {device.DeviceName}")
                    print(f"  描述: {device.DeviceString}")
                    print(f"  状态: {device.StateFlags}")
                    
                    # 获取该显示器的设置
                    try:
                        settings = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                        print(f"  当前设置: {settings.PelsWidth}x{settings.PelsHeight} @ {settings.DisplayFrequency}Hz")
                        print(f"  颜色深度: {settings.BitsPerPel}")
                        print(f"  位置: ({settings.Position_x}, {settings.Position_y})")
                    except:
                        print(f"  无法获取设置信息")
                    
                    print()
                    i += 1
                except:
                    break
        except Exception as e:
            print(f"获取显示器设置失败: {e}")
    
    get_display_settings()
    
    # 方法4: 测试截图区域
    print("=== 方法4: 测试截图区域 ===")
    
    def test_screenshot_area(left, top, width, height, name):
        try:
            hwin = win32gui.GetDesktopWindow()
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)
            
            result = memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
            
            if result:
                print(f"  {name}: 成功 - {width}x{height} 位置({left},{top})")
            else:
                error = win32api.GetLastError()
                print(f"  {name}: 失败 - 错误代码 {error}")
            
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)
            
        except Exception as e:
            print(f"  {name}: 异常 - {e}")
    
    # 测试主显示器区域
    test_screenshot_area(0, 0, primary_width, primary_height, "主显示器")
    
    # 测试每个检测到的显示器
    monitors = []
    try:
        # 尝试使用EnumDisplaySettings获取显示器信息
        i = 0
        while True:
            try:
                device = win32api.EnumDisplayDevices(None, i)
                if not device.DeviceName:
                    break
                
                if device.StateFlags & win32con.DISPLAY_DEVICE_ACTIVE:
                    try:
                        settings = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                        monitors.append({
                            'index': i,
                            'left': settings.Position_x,
                            'top': settings.Position_y,
                            'width': settings.PelsWidth,
                            'height': settings.PelsHeight,
                            'device_name': device.DeviceName
                        })
                    except:
                        pass
                
                i += 1
            except:
                break
    except:
        pass
    
    for i, monitor in enumerate(monitors):
        test_screenshot_area(
            monitor['left'], 
            monitor['top'], 
            monitor['width'], 
            monitor['height'], 
            f"显示器 {i + 1}"
        )
    
    # 测试虚拟桌面区域
    test_screenshot_area(virtual_left, virtual_top, virtual_width, virtual_height, "虚拟桌面")
    
    print("\n=== 诊断完成 ===")
    print("请根据上述信息分析显示器配置是否正确。")
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装 pywin32: pip install pywin32")
except Exception as e:
    print(f"诊断失败: {e}")
    import traceback
    traceback.print_exc() 