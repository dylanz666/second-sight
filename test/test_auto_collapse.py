#!/usr/bin/env python3
"""
测试自动收起功能
验证当检测到多个显示器时，系统是否正确自动收起非主显示器
"""

import json
import requests
import time

def test_auto_collapse():
    """测试自动收起功能"""
    base_url = "http://localhost:8000"
    
    print("🧪 开始测试自动收起功能...")
    
    try:
        # 1. 检查服务器状态
        print("1. 检查服务器状态...")
        response = requests.get(f"{base_url}/status")
        if response.status_code != 200:
            print("❌ 服务器未运行，请先启动服务器")
            return False
        print("✅ 服务器运行正常")
        
        # 2. 获取显示器配置
        print("2. 获取显示器配置...")
        response = requests.get(f"{base_url}/monitors/config")
        if response.status_code != 200:
            print("❌ 无法获取显示器配置")
            return False
            
        monitors_config = response.json()
        monitors = monitors_config.get("monitors", [])
        
        if len(monitors) <= 1:
            print(f"⚠️  只检测到 {len(monitors)} 个显示器，无法测试自动收起功能")
            return True
            
        print(f"✅ 检测到 {len(monitors)} 个显示器")
        
        # 3. 检查主显示器
        primary_monitor = None
        secondary_monitors = []
        
        for monitor in monitors:
            if monitor.get("primary", False):
                primary_monitor = monitor
            else:
                secondary_monitors.append(monitor)
                
        if not primary_monitor:
            print("❌ 未找到主显示器")
            return False
            
        print(f"✅ 主显示器: 索引 {primary_monitor['index']}, 分辨率 {primary_monitor['width']}x{primary_monitor['height']}")
        print(f"✅ 副显示器数量: {len(secondary_monitors)}")
        
        # 4. 重置收起状态（模拟页面刷新）
        print("3. 重置收起状态...")
        response = requests.post(f"{base_url}/collapsed-monitors", 
                               json={"collapsed_monitors": []})
        if response.status_code != 200:
            print("❌ 重置收起状态失败")
            return False
        print("✅ 收起状态已重置")
        
        # 5. 获取所有显示器截图（这会触发自动收起逻辑）
        print("4. 获取所有显示器截图（触发自动收起）...")
        response = requests.get(f"{base_url}/screenshots/all")
        if response.status_code != 200:
            print("❌ 获取显示器截图失败")
            return False
            
        screenshots_data = response.json()
        screenshots = screenshots_data.get("screenshots", [])
        
        # 6. 检查自动收起结果
        print("5. 检查自动收起结果...")
        collapsed_monitors = []
        active_monitors = []
        
        for screenshot in screenshots:
            if screenshot.get("collapsed", False):
                collapsed_monitors.append(screenshot)
            else:
                active_monitors.append(screenshot)
                
        print(f"✅ 活跃显示器数量: {len(active_monitors)}")
        print(f"✅ 收起显示器数量: {len(collapsed_monitors)}")
        
        # 验证只有主显示器是活跃的
        if len(active_monitors) == 1 and active_monitors[0].get("primary", False):
            print("✅ 自动收起功能正常：只有主显示器保持活跃")
        else:
            print("❌ 自动收起功能异常：主显示器未正确保持活跃")
            return False
            
        # 验证所有副显示器都被收起
        all_secondary_collapsed = all(
            screenshot.get("collapsed", False) 
            for screenshot in screenshots 
            if not screenshot.get("primary", False)
        )
        
        if all_secondary_collapsed:
            print("✅ 自动收起功能正常：所有副显示器都被收起")
        else:
            print("❌ 自动收起功能异常：部分副显示器未被收起")
            return False
            
        # 7. 检查后端收起状态
        print("6. 检查后端收起状态...")
        response = requests.get(f"{base_url}/collapsed-monitors")
        if response.status_code != 200:
            print("❌ 获取后端收起状态失败")
            return False
            
        backend_collapsed = response.json().get("collapsed_monitors", [])
        expected_collapsed = [monitor["index"] for monitor in secondary_monitors]
        
        if set(backend_collapsed) == set(expected_collapsed):
            print("✅ 后端收起状态正确")
        else:
            print(f"❌ 后端收起状态异常: 期望 {expected_collapsed}, 实际 {backend_collapsed}")
            return False
            
        print("🎉 自动收起功能测试通过！")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def test_manual_reset():
    """测试手动重置功能"""
    base_url = "http://localhost:8000"
    
    print("\n🧪 测试手动重置功能...")
    
    try:
        # 1. 重置收起状态
        print("1. 重置收起状态...")
        response = requests.post(f"{base_url}/collapsed-monitors", 
                               json={"collapsed_monitors": []})
        if response.status_code != 200:
            print("❌ 重置收起状态失败")
            return False
        print("✅ 收起状态已重置")
        
        # 2. 检查重置后的状态
        print("2. 检查重置后的状态...")
        response = requests.get(f"{base_url}/collapsed-monitors")
        if response.status_code != 200:
            print("❌ 获取后端收起状态失败")
            return False
            
        backend_collapsed = response.json().get("collapsed_monitors", [])
        
        if len(backend_collapsed) == 0:
            print("✅ 重置功能正常：所有显示器都已展开")
        else:
            print(f"❌ 重置功能异常：仍有 {len(backend_collapsed)} 个显示器被收起")
            return False
            
        print("🎉 手动重置功能测试通过！")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 自动收起功能测试")
    print("=" * 60)
    
    # 测试自动收起功能
    auto_collapse_result = test_auto_collapse()
    
    # 测试手动重置功能
    reset_result = test_manual_reset()
    
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    print(f"自动收起功能: {'✅ 通过' if auto_collapse_result else '❌ 失败'}")
    print(f"手动重置功能: {'✅ 通过' if reset_result else '❌ 失败'}")
    
    if auto_collapse_result and reset_result:
        print("\n🎉 所有测试通过！自动收起功能工作正常。")
    else:
        print("\n⚠️  部分测试失败，请检查实现。") 