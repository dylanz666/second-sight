from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import base64
import io
import time
from datetime import datetime
import uvicorn
from typing import List
from PIL import Image, ImageDraw
import psutil  # 添加psutil用于系统监控

app = FastAPI(title="Remote Viewer Server", version="1.0.0")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 网络状态监控器
class NetworkMonitor:
    def __init__(self):
        self.last_check_time = None
        self.network_status = "unknown"
        self.ping_latency = 0
        
    def check_network_status(self):
        """检查网络连接状态，每2秒钟检查一次"""
        try:
            import socket
            import time
            
            # 测试连接到Google DNS (8.8.8.8)
            start_time = time.time()
            socket.create_connection(("8.8.8.8", 53), timeout=3)
            latency = (time.time() - start_time) * 2000  # 转换为毫秒
            
            if latency < 100:
                self.network_status = "excellent"
            elif latency < 300:
                self.network_status = "good"
            elif latency < 1000:
                self.network_status = "fair"
            else:
                self.network_status = "poor"
                
            self.ping_latency = int(latency)
            self.last_check_time = time.time()
            
        except Exception as e:
            self.network_status = "disconnected"
            self.ping_latency = 0
            self.last_check_time = time.time()
    
    def get_network_info(self):
        """获取网络状态信息"""
        # 每30秒检查一次网络状态
        if (self.last_check_time is None or 
            time.time() - self.last_check_time > 30):
            self.check_network_status()
            
        return {
            "status": self.network_status,
            "latency": self.ping_latency,
            "last_check": self.last_check_time
        }

# 系统资源监控器
class SystemMonitor:
    def __init__(self):
        self.last_check_time = None
        self.memory_usage = 0
        self.cpu_usage = 0
        self.disk_usage = 0
        
    def check_system_resources(self):
        """检查系统资源使用情况"""
        try:
            # 获取内存使用率
            memory = psutil.virtual_memory()
            self.memory_usage = round(memory.percent, 1)
            
            # 获取CPU使用率
            self.cpu_usage = round(psutil.cpu_percent(interval=1), 1)
            
            # 获取磁盘使用率
            disk = psutil.disk_usage('/')
            self.disk_usage = round((disk.used / disk.total) * 100, 1)
            
            self.last_check_time = time.time()
            
        except Exception as e:
            print(f"获取系统资源信息失败: {e}")
            self.memory_usage = 0
            self.cpu_usage = 0
            self.disk_usage = 0
            self.last_check_time = time.time()
    
    def get_system_info(self):
        """获取系统资源信息"""
        # 每5秒检查一次系统资源
        if (self.last_check_time is None or 
            time.time() - self.last_check_time > 5):
            self.check_system_resources()
            
        return {
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "disk_usage": self.disk_usage,
            "last_check": self.last_check_time
        }

# WebSocket连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            if websocket.client_state.value <= 2:  # 连接仍然活跃
                await websocket.send_text(message)
        except Exception as e:
            print(f"发送个人消息失败: {e}")
            # 如果发送失败，从连接列表中移除
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state.value <= 2:  # 连接仍然活跃
                    await connection.send_text(message)
                else:
                    disconnected.append(connection)
            except Exception as e:
                print(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 移除断开的连接
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()
network_monitor = NetworkMonitor()
system_monitor = SystemMonitor()

# Windows桌面截图生成器
class DesktopScreenshotGenerator:
    def __init__(self):
        self.counter = 0
        self.last_screenshot = None
        self.last_screenshot_time = None
        self.monitors = []
        self.update_monitor_info()
    
    def update_monitor_info(self):
        """更新显示器信息"""
        try:
            import win32api
            import win32con
            
            self.monitors = []
            
            # 获取虚拟桌面信息
            virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            
            # 获取主显示器信息
            primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # 获取显示器数量
            monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)
            
            print(f"检测到 {monitor_count} 个显示器")
            print(f"虚拟桌面: {virtual_width}x{virtual_height} 位置({virtual_left},{virtual_top})")
            print(f"主显示器: {primary_width}x{primary_height}")
            
            # 使用EnumDisplaySettings获取更准确的显示器信息
            try:
                # 获取所有显示器设备
                display_devices = []
                i = 0
                while True:
                    try:
                        device = win32api.EnumDisplayDevices(None, i)
                        if not device.DeviceName:
                            break
                        
                        print(f"设备 {i}: {device.DeviceName} - 状态: {device.StateFlags}")
                        
                        # 检查设备是否激活
                        if device.StateFlags & 0x1:  # DISPLAY_DEVICE_ACTIVE = 0x1
                            try:
                                settings = win32api.EnumDisplaySettings(device.DeviceName, win32con.ENUM_CURRENT_SETTINGS)
                                display_devices.append({
                                    'device_name': device.DeviceName,
                                    'device_string': device.DeviceString,
                                    'width': settings.PelsWidth,
                                    'height': settings.PelsHeight,
                                    'position_x': settings.Position_x,
                                    'position_y': settings.Position_y,
                                    'frequency': settings.DisplayFrequency,
                                    'bits_per_pel': settings.BitsPerPel
                                })
                                print(f"  激活显示器: {device.DeviceName} - {settings.PelsWidth}x{settings.PelsHeight} 位置({settings.Position_x},{settings.Position_y})")
                            except Exception as e:
                                print(f"  无法获取显示器 {device.DeviceName} 的设置: {e}")
                        else:
                            print(f"  未激活显示器: {device.DeviceName}")
                        
                        i += 1
                    except:
                        break
                
                # 如果没有找到激活的显示器，使用系统指标
                if not display_devices:
                    print("未找到激活的显示器设备，使用系统指标")
                    # 使用虚拟桌面信息
                    if virtual_width > 0 and virtual_height > 0:
                        self.monitors = [{
                            'index': 0,
                            'width': virtual_width,
                            'height': virtual_height,
                            'left': virtual_left,
                            'top': virtual_top,
                            'right': virtual_left + virtual_width,
                            'bottom': virtual_top + virtual_height,
                            'primary': True
                        }]
                    else:
                        # 使用主显示器信息
                        self.monitors = [{
                            'index': 0,
                            'width': primary_width,
                            'height': primary_height,
                            'left': 0,
                            'top': 0,
                            'right': primary_width,
                            'bottom': primary_height,
                            'primary': True
                        }]
                else:
                    # 根据位置信息排序显示器（先按Y坐标，再按X坐标）
                    display_devices.sort(key=lambda x: (x['position_y'], x['position_x']))
                    
                    # 转换为monitor格式
                    for i, device in enumerate(display_devices):
                        monitor_info = {
                            'index': i,
                            'width': device['width'],
                            'height': device['height'],
                            'left': device['position_x'],
                            'top': device['position_y'],
                            'right': device['position_x'] + device['width'],
                            'bottom': device['position_y'] + device['height'],
                            'primary': (device['position_x'] == 0 and device['position_y'] == 0),
                            'device_name': device['device_name'],
                            'frequency': device['frequency']
                        }
                        self.monitors.append(monitor_info)
                        
            except Exception as e:
                print(f"使用EnumDisplaySettings失败，使用备用方法: {e}")
                # 备用方法：基于虚拟桌面尺寸推断
                if virtual_width > 0 and virtual_height > 0:
                    self.monitors = [{
                        'index': 0,
                        'width': virtual_width,
                        'height': virtual_height,
                        'left': virtual_left,
                        'top': virtual_top,
                        'right': virtual_left + virtual_width,
                        'bottom': virtual_top + virtual_height,
                        'primary': True
                    }]
                else:
                    self.monitors = [{
                        'index': 0,
                        'width': primary_width,
                        'height': primary_height,
                        'left': 0,
                        'top': 0,
                        'right': primary_width,
                        'bottom': primary_height,
                        'primary': True
                    }]
            
            # 验证显示器信息
            print("\n=== 最终显示器配置 ===")
            for i, monitor in enumerate(self.monitors):
                print(f"显示器 {i + 1}: {monitor['width']}x{monitor['height']} 位置({monitor['left']},{monitor['top']}) 区域({monitor['left']},{monitor['top']},{monitor['right']},{monitor['bottom']}) {'(主显示器)' if monitor['primary'] else ''}")
                
        except Exception as e:
            print(f"获取显示器信息失败: {e}")
            # 默认单显示器
            self.monitors = [{'index': 0, 'width': 1920, 'height': 1080, 'left': 0, 'top': 0, 'right': 1920, 'bottom': 1080, 'primary': True}]
        
    def capture_single_monitor(self, monitor_index=0):
        """捕获单个显示器截图"""
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            
            # 获取显示器句柄
            hwin = win32gui.GetDesktopWindow()
            
            # 获取指定显示器的信息
            if monitor_index < len(self.monitors):
                monitor = self.monitors[monitor_index]
                width = monitor['width']
                height = monitor['height']
                left = monitor['left']
                top = monitor['top']
                right = monitor['right']
                bottom = monitor['bottom']
            else:
                # 默认使用主显示器
                width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                left = 0
                top = 0
                right = width
                bottom = height
            
            print(f"捕获显示器 {monitor_index + 1}: {width}x{height} 位置({left},{top}) 区域({left},{top},{right},{bottom})")
            
            # 验证截图区域是否合理
            if width <= 0 or height <= 0:
                print(f"错误: 显示器 {monitor_index + 1} 尺寸无效: {width}x{height}")
                return self._create_error_image(f"显示器 {monitor_index + 1} 尺寸无效")
            
            if left < 0 or top < 0:
                print(f"错误: 显示器 {monitor_index + 1} 位置无效: ({left},{top})")
                return self._create_error_image(f"显示器 {monitor_index + 1} 位置无效")
            
            # 创建设备上下文
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            
            # 创建位图
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)
            
            # 复制指定区域的屏幕内容到位图
            # 注意：BitBlt的源坐标是相对于虚拟桌面的，目标坐标是相对于位图的
            result = memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
            
            if result == 0:
                error_code = win32api.GetLastError()
                print(f"警告: BitBlt操作失败，错误代码: {error_code}")
                # 尝试使用备用方法
                print(f"尝试备用截图方法...")
                
                # 清理资源
                win32gui.DeleteObject(bmp.GetHandle())
                memdc.DeleteDC()
                srcdc.DeleteDC()
                win32gui.ReleaseDC(hwin, hwindc)
                
                # 使用PIL的ImageGrab作为备用方法
                return self._capture_monitor_fallback(monitor_index, left, top, width, height)
            
            # 获取位图信息
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)
            
            # 转换为PIL图像
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # 清理资源
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)
            
            print(f"成功捕获显示器 {monitor_index + 1} 截图: {img.width}x{img.height}")
            
            # 调整图像大小以适合显示（保持宽高比）
            max_width = 800
            max_height = 600
            
            # 计算缩放比例
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            # 使用LANCZOS重采样进行高质量缩放
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return img
            
        except Exception as e:
            print(f"捕获显示器 {monitor_index + 1} 截图失败: {e}")
            import traceback
            traceback.print_exc()
            return self._create_error_image(f"显示器 {monitor_index + 1} 截图失败: {str(e)}")
    
    def _capture_monitor_fallback(self, monitor_index, left, top, width, height):
        """备用截图方法，使用PIL的ImageGrab"""
        try:
            from PIL import ImageGrab
            
            print(f"使用备用方法捕获显示器 {monitor_index + 1}: 区域({left},{top},{left+width},{top+height})")
            
            # 使用ImageGrab捕获指定区域
            bbox = (left, top, left + width, top + height)
            img = ImageGrab.grab(bbox=bbox)
            
            print(f"备用方法成功捕获显示器 {monitor_index + 1} 截图: {img.width}x{img.height}")
            
            # 调整图像大小以适合显示（保持宽高比）
            max_width = 800
            max_height = 600
            
            # 计算缩放比例
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            # 使用LANCZOS重采样进行高质量缩放
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            return img
            
        except Exception as e:
            print(f"备用截图方法失败: {e}")
            return self._create_error_image(f"备用截图失败: {str(e)}")

    def capture_desktop_screenshot(self):
        """捕获Windows桌面截图"""
        try:
            import win32gui
            import win32ui
            import win32con
            import win32api
            from ctypes import windll
            
            # 获取主显示器的句柄
            hwin = win32gui.GetDesktopWindow()
            
            # 获取虚拟桌面的尺寸（支持多显示器）
            virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            
            # 如果虚拟桌面尺寸为0，则使用主显示器尺寸
            if virtual_width == 0 or virtual_height == 0:
                width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                left = 0
                top = 0
            else:
                width = virtual_width
                height = virtual_height
                left = virtual_left
                top = virtual_top
            
            # 创建设备上下文
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()
            
            # 创建位图
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)
            
            # 复制屏幕内容到位图（指定源区域）
            memdc.BitBlt((0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY)
            
            # 获取位图信息
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)
            
            # 转换为PIL图像
            img = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # 清理资源
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)
            
            # 调整图像大小以适合显示（保持宽高比）
            max_width = 1600
            max_height = 1000
            
            # 计算缩放比例
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            # 使用LANCZOS重采样进行高质量缩放
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.counter += 1
            self.last_screenshot = img
            self.last_screenshot_time = datetime.now()
            
            return img
            
        except ImportError:
            # 如果没有win32gui，使用备用方案
            return self._fallback_screenshot()
        except Exception as e:
            print(f"截图错误: {e}")
            return self._fallback_screenshot()
    
    def _fallback_screenshot(self):
        """备用截图方案"""
        try:
            # 使用PIL的ImageGrab（仅适用于Windows）
            from PIL import ImageGrab
            
            # 捕获整个屏幕（包括所有显示器）
            screenshot = ImageGrab.grab(bbox=None)  # bbox=None 表示捕获整个虚拟桌面
            
            # 调整大小（保持宽高比）
            max_width = 1600
            max_height = 1000
            
            # 计算缩放比例
            ratio = min(max_width / screenshot.width, max_height / screenshot.height)
            new_width = int(screenshot.width * ratio)
            new_height = int(screenshot.height * ratio)
            
            # 使用LANCZOS重采样进行高质量缩放
            screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            self.counter += 1
            self.last_screenshot = screenshot
            self.last_screenshot_time = datetime.now()
            
            return screenshot
            
        except Exception as e:
            print(f"备用截图错误: {e}")
            return self._create_error_image()
    
    def _create_error_image(self, error_message: str = "无法捕获桌面截图"):
        """创建错误提示图像"""
        img = Image.new('RGB', (800, 600), color='lightgray')
        draw = ImageDraw.Draw(img)
        
        # 添加错误信息
        draw.text((400, 250), error_message, fill='red', anchor='mm')
        
        # 添加时间戳
        timestamp = f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text((400, 300), timestamp, fill='black', anchor='mm')
        
        self.counter += 1
        return img

# 使用桌面截图生成器
ui_generator = DesktopScreenshotGenerator()

@app.get("/")
async def get_index():
    """返回主页HTML"""
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/screenshot")
async def get_screenshot():
    """获取当前桌面截图"""
    try:
        # 捕获桌面截图
        img = ui_generator.capture_desktop_screenshot()
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {"image": img_base64, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        return {"error": str(e)}

@app.get("/screenshot/monitor/{monitor_index}")
async def get_single_monitor_screenshot(monitor_index: int):
    """获取指定显示器的截图"""
    try:
        # 更新显示器信息
        ui_generator.update_monitor_info()
        
        # 检查显示器索引是否有效
        if monitor_index >= len(ui_generator.monitors):
            return {"error": f"显示器索引 {monitor_index} 超出范围，共有 {len(ui_generator.monitors)} 个显示器"}
        
        # 捕获指定显示器的截图
        img = ui_generator.capture_single_monitor(monitor_index)
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        monitor = ui_generator.monitors[monitor_index]
        
        return {
            "monitor_index": monitor_index,
            "width": monitor['width'],
            "height": monitor['height'],
            "primary": monitor['primary'],
            "image": img_base64,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/screenshots/all")
async def get_all_monitor_screenshots():
    """获取所有显示器的截图"""
    try:
        screenshots = []
        
        # 更新显示器信息
        ui_generator.update_monitor_info()
        
        # 为每个显示器捕获截图
        for i, monitor in enumerate(ui_generator.monitors):
            img = ui_generator.capture_single_monitor(i)
            
            # 转换为base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            
            screenshots.append({
                "monitor_index": i,
                "width": monitor['width'],
                "height": monitor['height'],
                "primary": monitor['primary'],
                "image": img_base64
            })
        
        return {
            "screenshots": screenshots,
            "monitor_count": len(screenshots),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接处理"""
    await manager.connect(websocket)
    try:
        while True:
            # 检查连接是否仍然活跃
            if websocket.client_state.value > 2:  # 连接已关闭
                break
                
            # 获取网络状态和系统资源信息
            network_info = network_monitor.get_network_info()
            system_info = system_monitor.get_system_info()
            
            # 发送实时数据
            data = {
                "type": "status",
                "counter": ui_generator.counter,
                "timestamp": datetime.now().isoformat(),
                "network": network_info,
                "memory_usage": system_info["memory_usage"],
                "cpu_usage": system_info["cpu_usage"],
                "disk_usage": system_info["disk_usage"]
            }
            
            try:
                await websocket.send_text(json.dumps(data))
            except Exception as e:
                # 如果发送失败，说明连接可能已断开
                print(f"WebSocket发送失败: {e}")
                break
                
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        print("WebSocket连接断开")
    except Exception as e:
        print(f"WebSocket异常: {e}")
    finally:
        manager.disconnect(websocket)

@app.get("/status")
async def get_status():
    """获取服务器状态"""
    network_info = network_monitor.get_network_info()
    system_info = system_monitor.get_system_info()
    return {
        "counter": ui_generator.counter,  # 保留用于内部逻辑
        "timestamp": datetime.now().isoformat(),
        "connections": len(manager.active_connections),
        "network": network_info,
        "memory_usage": system_info["memory_usage"],
        "cpu_usage": system_info["cpu_usage"],
        "disk_usage": system_info["disk_usage"]
    }

@app.get("/test-network")
async def test_network():
    """手动测试网络连接"""
    network_monitor.check_network_status()
    network_info = network_monitor.get_network_info()
    return {
        "message": "网络测试完成",
        "network": network_info,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/system-info")
async def get_system_info():
    """获取系统资源信息"""
    try:
        system_info = system_monitor.get_system_info()
        
        # 获取更详细的系统信息
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        disk = psutil.disk_usage('/')
        
        return {
            "memory": {
                "usage_percent": system_info["memory_usage"],
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2)
            },
            "cpu": {
                "usage_percent": system_info["cpu_usage"],
                "count": cpu_count,
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "usage_percent": round((disk.used / disk.total) * 100, 1)
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/monitors/config")
async def get_monitors_config():
    """获取显示器配置信息"""
    try:
        import win32api
        import win32con
        
        # 更新显示器信息
        ui_generator.update_monitor_info()
        
        # 获取系统信息
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        
        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)
        
        # 获取显示器详细信息
        monitors_info = []
        for monitor in ui_generator.monitors:
            monitors_info.append({
                "index": monitor['index'],
                "width": monitor['width'],
                "height": monitor['height'],
                "left": monitor['left'],
                "top": monitor['top'],
                "right": monitor['right'],
                "bottom": monitor['bottom'],
                "primary": monitor['primary'],
                "area": monitor['width'] * monitor['height']
            })
        
        return {
            "system_info": {
                "monitor_count": monitor_count,
                "virtual_screen": {
                    "width": virtual_width,
                    "height": virtual_height,
                    "left": virtual_left,
                    "top": virtual_top,
                    "area": virtual_width * virtual_height
                },
                "primary_screen": {
                    "width": primary_width,
                    "height": primary_height,
                    "area": primary_width * primary_height
                }
            },
            "monitors": monitors_info,
            "detection_method": "EnumDisplayMonitors" if len(monitors_info) > 1 else "Single Monitor",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/debug/monitor/{monitor_index}")
async def debug_monitor_screenshot(monitor_index: int):
    """调试单个显示器截图"""
    try:
        # 更新显示器信息
        ui_generator.update_monitor_info()
        
        # 检查显示器索引是否有效
        if monitor_index >= len(ui_generator.monitors):
            return {"error": f"显示器索引 {monitor_index} 超出范围，共有 {len(ui_generator.monitors)} 个显示器"}
        
        monitor = ui_generator.monitors[monitor_index]
        
        # 获取系统信息
        import win32api
        import win32con
        
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        
        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        # 捕获截图
        img = ui_generator.capture_single_monitor(monitor_index)
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {
            "monitor_index": monitor_index,
            "monitor_info": {
                "width": monitor['width'],
                "height": monitor['height'],
                "left": monitor['left'],
                "top": monitor['top'],
                "right": monitor['right'],
                "bottom": monitor['bottom'],
                "primary": monitor['primary']
            },
            "system_info": {
                "virtual_screen": f"{virtual_width}x{virtual_height} 位置({virtual_left},{virtual_top})",
                "primary_screen": f"{primary_width}x{primary_height}",
                "captured_image_size": f"{img.width}x{img.height}"
            },
            "image": img_base64,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/force-redetect")
async def force_redetect_monitors():
    """强制重新检测显示器配置"""
    try:
        # 强制重新检测显示器
        ui_generator.update_monitor_info()
        
        # 获取系统信息
        import win32api
        import win32con
        
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        
        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)
        
        # 获取显示器详细信息
        monitors_info = []
        for monitor in ui_generator.monitors:
            monitors_info.append({
                "index": monitor['index'],
                "width": monitor['width'],
                "height": monitor['height'],
                "left": monitor['left'],
                "top": monitor['top'],
                "right": monitor['right'],
                "bottom": monitor['bottom'],
                "primary": monitor['primary'],
                "area": monitor['width'] * monitor['height']
            })
        
        return {
            "message": "显示器重新检测完成",
            "system_info": {
                "monitor_count": monitor_count,
                "virtual_screen": {
                    "width": virtual_width,
                    "height": virtual_height,
                    "left": virtual_left,
                    "top": virtual_top,
                    "area": virtual_width * virtual_height
                },
                "primary_screen": {
                    "width": primary_width,
                    "height": primary_height,
                    "area": primary_width * primary_height
                }
            },
            "monitors": monitors_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/screenshot-info")
async def get_screenshot_info():
    """获取截图信息"""
    try:
        import win32api
        import win32con
        
        # 更新显示器信息
        ui_generator.update_monitor_info()
        
        # 获取屏幕信息
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        
        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
        
        # 获取当前截图信息
        if ui_generator.last_screenshot:
            current_width = ui_generator.last_screenshot.width
            current_height = ui_generator.last_screenshot.height
        else:
            current_width = 0
            current_height = 0
        
        # 获取显示器详细信息
        monitors_info = []
        for monitor in ui_generator.monitors:
            monitors_info.append({
                "index": monitor['index'],
                "width": monitor['width'],
                "height": monitor['height'],
                "left": monitor['left'],
                "top": monitor['top'],
                "primary": monitor['primary']
            })
        
        return {
            "virtual_screen": {
                "width": virtual_width,
                "height": virtual_height,
                "left": virtual_left,
                "top": virtual_top
            },
            "primary_screen": {
                "width": primary_width,
                "height": primary_height
            },
            "current_screenshot": {
                "width": current_width,
                "height": current_height
            },
            "monitors": monitors_info,
            "monitor_count": len(monitors_info),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    print("Starting Remote Viewer Server...")
    print("Access the application at: http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
