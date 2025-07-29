#!/usr/bin/env python3
"""
深度诊断脚本 - 详细分析显示器配置和截图问题
"""

import sys
import os
import time
import traceback

try:
    import win32api
    import win32con
    import win32gui
    import win32ui
    from PIL import Image, ImageGrab
    import ctypes
    from ctypes import windll
except ImportError as e:
    print(f"缺少依赖: {e}")
    print("请安装: pip install pywin32 pillow")
    sys.exit(1)

def get_detailed_system_info():
    """获取详细的系统显示信息"""
    print("=== 系统显示信息 ===")
    
    # 基本系统指标
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
    
    # 获取桌面窗口句柄
    hwin = win32gui.GetDesktopWindow()
    print(f"桌面窗口句柄: {hwin}")
    
    # 获取桌面窗口矩形
    try:
        rect = win32gui.GetWindowRect(hwin)
        print(f"桌面窗口矩形: {rect}")
    except Exception as e:
        print(f"获取桌面窗口矩形失败: {e}")
    
    return {
        'virtual_width': virtual_width,
        'virtual_height': virtual_height,
        'virtual_left': virtual_left,
        'virtual_top': virtual_top,
        'primary_width': primary_width,
        'primary_height': primary_height,
        'monitor_count': monitor_count,
        'hwin': hwin
    }

def enum_display_devices():
    """枚举所有显示设备"""
    print("\n=== 显示设备枚举 ===")
    
    devices = []
    i = 0
    
    while True:
        try:
            device = win32api.EnumDisplayDevices(None, i)
            if not device.DeviceName:
                break
                
            print(f"设备 {i}: {device.DeviceName}")
            print(f"  描述: {device.DeviceString}")
            print(f"  状态: {device.StateFlags}")
            print(f"  激活: {'是' if device.StateFlags & 0x1 else '否'}")  # DISPLAY_DEVICE_ACTIVE = 0x1
            
            if device.StateFlags & 0x1:  # DISPLAY_DEVICE_ACTIVE
                try:
                    settings = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                    print(f"  分辨率: {settings.PelsWidth}x{settings.PelsHeight}")
                    print(f"  位置: ({settings.Position_x},{settings.Position_y})")
                    print(f"  频率: {settings.DisplayFrequency}Hz")
                    print(f"  色深: {settings.BitsPerPel}位")
                    
                    devices.append({
                        'device_name': device.DeviceName,
                        'device_string': device.DeviceString,
                        'width': settings.PelsWidth,
                        'height': settings.PelsHeight,
                        'position_x': settings.Position_x,
                        'position_y': settings.Position_y,
                        'frequency': settings.DisplayFrequency,
                        'bits_per_pel': settings.BitsPerPel
                    })
                except Exception as e:
                    print(f"  获取设置失败: {e}")
            
            print()
            i += 1
        except Exception as e:
            print(f"枚举设备 {i} 失败: {e}")
            break
    
    return devices

def test_bitblt_capture(monitor_info, test_name):
    """测试BitBlt截图方法"""
    print(f"\n=== 测试 {test_name} ===")
    print(f"区域: {monitor_info['left']},{monitor_info['top']},{monitor_info['right']},{monitor_info['bottom']}")
    print(f"尺寸: {monitor_info['width']}x{monitor_info['height']}")
    
    try:
        # 获取桌面窗口句柄
        hwin = win32gui.GetDesktopWindow()
        
        # 创建设备上下文
        hwindc = win32gui.GetWindowDC(hwin)
        srcdc = win32ui.CreateDCFromHandle(hwindc)
        memdc = srcdc.CreateCompatibleDC()
        
        # 创建位图
        bmp = win32ui.CreateBitmap()
        bmp.CreateCompatibleBitmap(srcdc, monitor_info['width'], monitor_info['height'])
        memdc.SelectObject(bmp)
        
        # 执行BitBlt
        left = monitor_info['left']
        top = monitor_info['top']
        width = monitor_info['width']
        height = monitor_info['height']
        
        print(f"执行BitBlt: 目标(0,0,{width},{height}) 源({left},{top})")
        
        result = memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
        
        if result == 0:
            error_code = win32api.GetLastError()
            print(f"BitBlt失败，错误代码: {error_code}")
            return None
        else:
            print("BitBlt成功")
            
            # 获取位图信息
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)
            
            # 转换为PIL图像
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            print(f"截图尺寸: {img.width}x{img.height}")
            
            # 保存测试图片
            filename = f"test_{test_name}.png"
            img.save(filename)
            print(f"已保存到: {filename}")
            
            # 清理资源
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)
            
            return img
            
    except Exception as e:
        print(f"BitBlt测试失败: {e}")
        traceback.print_exc()
        return None

def test_pil_capture(monitor_info, test_name):
    """测试PIL截图方法"""
    print(f"\n=== 测试PIL {test_name} ===")
    print(f"区域: {monitor_info['left']},{monitor_info['top']},{monitor_info['right']},{monitor_info['bottom']}")
    
    try:
        # 使用ImageGrab捕获指定区域
        bbox = (monitor_info['left'], monitor_info['top'], monitor_info['right'], monitor_info['bottom'])
        print(f"PIL bbox: {bbox}")
        
        img = ImageGrab.grab(bbox=bbox)
        print(f"PIL截图尺寸: {img.width}x{img.height}")
        
        # 保存测试图片
        filename = f"test_pil_{test_name}.png"
        img.save(filename)
        print(f"已保存到: {filename}")
        
        return img
        
    except Exception as e:
        print(f"PIL测试失败: {e}")
        traceback.print_exc()
        return None

def analyze_monitor_arrangement(devices):
    """分析显示器排列"""
    print("\n=== 显示器排列分析 ===")
    
    if len(devices) < 2:
        print("只有一个显示器，无需分析排列")
        return
    
    # 按位置排序
    devices.sort(key=lambda x: (x['position_y'], x['position_x']))
    
    for i, device in enumerate(devices):
        print(f"显示器 {i + 1}: {device['width']}x{device['height']} 位置({device['position_x']},{device['position_y']})")
    
    # 检查重叠
    for i in range(len(devices)):
        for j in range(i + 1, len(devices)):
            device1 = devices[i]
            device2 = devices[j]
            
            # 计算重叠区域
            overlap_left = max(device1['position_x'], device2['position_x'])
            overlap_right = min(device1['position_x'] + device1['width'], device2['position_x'] + device2['width'])
            overlap_top = max(device1['position_y'], device2['position_y'])
            overlap_bottom = min(device1['position_y'] + device1['height'], device2['position_y'] + device2['height'])
            
            if overlap_left < overlap_right and overlap_top < overlap_bottom:
                print(f"警告: 显示器 {i + 1} 和显示器 {j + 1} 有重叠!")
                print(f"重叠区域: ({overlap_left},{overlap_top},{overlap_right},{overlap_bottom})")
            else:
                print(f"显示器 {i + 1} 和显示器 {j + 1} 无重叠")

def main():
    """主函数"""
    print("=== 深度诊断显示器截图问题 ===")
    print()
    
    # 获取系统信息
    sys_info = get_detailed_system_info()
    
    # 枚举显示设备
    devices = enum_display_devices()
    
    if not devices:
        print("未找到激活的显示设备!")
        return
    
    # 分析显示器排列
    analyze_monitor_arrangement(devices)
    
    # 测试每个显示器的截图
    print("\n=== 开始截图测试 ===")
    
    for i, device in enumerate(devices):
        monitor_info = {
            'left': device['position_x'],
            'top': device['position_y'],
            'right': device['position_x'] + device['width'],
            'bottom': device['position_y'] + device['height'],
            'width': device['width'],
            'height': device['height']
        }
        
        print(f"\n{'='*50}")
        print(f"测试显示器 {i + 1}: {device['device_name']}")
        print(f"{'='*50}")
        
        # 测试BitBlt方法
        bitblt_img = test_bitblt_capture(monitor_info, f"bitblt_monitor_{i+1}")
        
        # 测试PIL方法
        pil_img = test_pil_capture(monitor_info, f"pil_monitor_{i+1}")
        
        # 比较两种方法的结果
        if bitblt_img and pil_img:
            if bitblt_img.size == pil_img.size:
                print(f"两种方法截图尺寸相同: {bitblt_img.size}")
            else:
                print(f"两种方法截图尺寸不同: BitBlt={bitblt_img.size}, PIL={pil_img.size}")
    
    print("\n=== 诊断完成 ===")
    print("请检查生成的测试图片，比较不同方法的截图结果。")
    print("如果BitBlt和PIL的截图不同，说明显示器配置检测有问题。")

if __name__ == "__main__":
    main() 