from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
    HTTPException,
)
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import base64
import io
import time
import os
from datetime import datetime
import uvicorn
from typing import List
from PIL import Image, ImageDraw
import psutil  # 添加psutil用于系统监控
from pathlib import Path

app = FastAPI(title="Remote Viewer Server", version="1.0.0")

# 添加静态文件服务
app.mount("/static", StaticFiles(directory="."), name="static")

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
        if self.last_check_time is None or time.time() - self.last_check_time > 30:
            self.check_network_status()

        return {
            "status": self.network_status,
            "latency": self.ping_latency,
            "last_check": self.last_check_time,
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
            disk = psutil.disk_usage("/")
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
        if self.last_check_time is None or time.time() - self.last_check_time > 5:
            self.check_system_resources()

        return {
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "disk_usage": self.disk_usage,
            "last_check": self.last_check_time,
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
        # 截图质量配置
        self.quality_settings = {
            "single_monitor": {"max_width": 1400, "max_height": 1050},
            "desktop": {"max_width": 1920, "max_height": 1200},
            "png_quality": 95,
            "optimize": False,
        }
        self.update_monitor_info()

    def _should_resize_image(self, img, max_width, max_height):
        """检查是否需要调整图像大小"""
        return img.width > max_width or img.height > max_height

    def _resize_image_high_quality(self, img, max_width, max_height):
        """高质量调整图像大小"""
        # 如果图像已经小于等于目标尺寸，不进行缩放
        if not self._should_resize_image(img, max_width, max_height):
            return img

        # 计算缩放比例
        ratio = min(max_width / img.width, max_height / img.height)
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)

        # 使用LANCZOS重采样进行高质量缩放
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

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

            # print(f"检测到 {monitor_count} 个显示器")
            # print(
            #     f"虚拟桌面: {virtual_width}x{virtual_height} 位置({virtual_left},{virtual_top})"
            # )
            # print(f"主显示器: {primary_width}x{primary_height}")

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

                        # print(
                        #     f"设备 {i}: {device.DeviceName} - 状态: {device.StateFlags}"
                        # )

                        # 检查设备是否激活
                        if device.StateFlags & 0x1:  # DISPLAY_DEVICE_ACTIVE = 0x1
                            try:
                                settings = win32api.EnumDisplaySettings(
                                    device.DeviceName, win32con.ENUM_CURRENT_SETTINGS
                                )
                                display_devices.append(
                                    {
                                        "device_name": device.DeviceName,
                                        "device_string": device.DeviceString,
                                        "width": settings.PelsWidth,
                                        "height": settings.PelsHeight,
                                        "position_x": settings.Position_x,
                                        "position_y": settings.Position_y,
                                        "frequency": settings.DisplayFrequency,
                                        "bits_per_pel": settings.BitsPerPel,
                                    }
                                )
                                # print(
                                #     f"  激活显示器: {device.DeviceName} - {settings.PelsWidth}x{settings.PelsHeight} 位置({settings.Position_x},{settings.Position_y})"
                                # )
                            except Exception as e:
                                pass
                                # print(
                                    # f"  无法获取显示器 {device.DeviceName} 的设置: {e}"
                                # )
                        else:
                            pass
                            # print(f"  未激活显示器: {device.DeviceName}")

                        i += 1
                    except:
                        break

                # 如果没有找到激活的显示器，使用系统指标
                if not display_devices:
                    print("未找到激活的显示器设备，使用系统指标")
                    # 使用虚拟桌面信息
                    if virtual_width > 0 and virtual_height > 0:
                        self.monitors = [
                            {
                                "index": 0,
                                "width": virtual_width,
                                "height": virtual_height,
                                "left": virtual_left,
                                "top": virtual_top,
                                "right": virtual_left + virtual_width,
                                "bottom": virtual_top + virtual_height,
                                "primary": True,
                            }
                        ]
                    else:
                        # 使用主显示器信息
                        self.monitors = [
                            {
                                "index": 0,
                                "width": primary_width,
                                "height": primary_height,
                                "left": 0,
                                "top": 0,
                                "right": primary_width,
                                "bottom": primary_height,
                                "primary": True,
                            }
                        ]
                else:
                    # 根据位置信息排序显示器（先按Y坐标，再按X坐标）
                    display_devices.sort(
                        key=lambda x: (x["position_y"], x["position_x"])
                    )

                    # 转换为monitor格式
                    for i, device in enumerate(display_devices):
                        monitor_info = {
                            "index": i,
                            "width": device["width"],
                            "height": device["height"],
                            "left": device["position_x"],
                            "top": device["position_y"],
                            "right": device["position_x"] + device["width"],
                            "bottom": device["position_y"] + device["height"],
                            "primary": (
                                device["position_x"] == 0 and device["position_y"] == 0
                            ),
                            "device_name": device["device_name"],
                            "frequency": device["frequency"],
                        }
                        self.monitors.append(monitor_info)

            except Exception as e:
                print(f"使用EnumDisplaySettings失败，使用备用方法: {e}")
                # 备用方法：基于虚拟桌面尺寸推断
                if virtual_width > 0 and virtual_height > 0:
                    self.monitors = [
                        {
                            "index": 0,
                            "width": virtual_width,
                            "height": virtual_height,
                            "left": virtual_left,
                            "top": virtual_top,
                            "right": virtual_left + virtual_width,
                            "bottom": virtual_top + virtual_height,
                            "primary": True,
                        }
                    ]
                else:
                    self.monitors = [
                        {
                            "index": 0,
                            "width": primary_width,
                            "height": primary_height,
                            "left": 0,
                            "top": 0,
                            "right": primary_width,
                            "bottom": primary_height,
                            "primary": True,
                        }
                    ]

            # 验证显示器信息
            # print("\n=== 最终显示器配置 ===")
            # for i, monitor in enumerate(self.monitors):
            #     print(
            #         f"显示器 {i + 1}: {monitor['width']}x{monitor['height']} 位置({monitor['left']},{monitor['top']}) 区域({monitor['left']},{monitor['top']},{monitor['right']},{monitor['bottom']}) {'(主显示器)' if monitor['primary'] else ''}"
            #     )

        except Exception as e:
            print(f"获取显示器信息失败: {e}")
            # 默认单显示器
            self.monitors = [
                {
                    "index": 0,
                    "width": 1920,
                    "height": 1080,
                    "left": 0,
                    "top": 0,
                    "right": 1920,
                    "bottom": 1080,
                    "primary": True,
                }
            ]

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
                width = monitor["width"]
                height = monitor["height"]
                left = monitor["left"]
                top = monitor["top"]
                right = monitor["right"]
                bottom = monitor["bottom"]
            else:
                # 默认使用主显示器
                width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                left = 0
                top = 0
                right = width
                bottom = height

            # print(
            #     f"捕获显示器 {monitor_index + 1}: {width}x{height} 位置({left},{top}) 区域({left},{top},{right},{bottom})"
            # )

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
            result = memdc.BitBlt(
                (0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY
            )

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
                return self._capture_monitor_fallback(
                    monitor_index, left, top, width, height
                )

            # 获取位图信息
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)

            # 转换为PIL图像
            img = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )

            # 清理资源
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)

            # print(f"成功捕获显示器 {monitor_index + 1} 截图: {img.width}x{img.height}")

            # 高质量调整图像大小
            max_width = self.quality_settings["single_monitor"]["max_width"]
            max_height = self.quality_settings["single_monitor"]["max_height"]
            img = self._resize_image_high_quality(img, max_width, max_height)

            return img

        except Exception as e:
            print(f"捕获显示器 {monitor_index + 1} 截图失败: {e}")
            import traceback

            traceback.print_exc()
            return self._create_error_image(
                f"显示器 {monitor_index + 1} 截图失败: {str(e)}"
            )

    def _capture_monitor_fallback(self, monitor_index, left, top, width, height):
        """备用截图方法，使用PIL的ImageGrab"""
        try:
            from PIL import ImageGrab

            # print(
            #     f"使用备用方法捕获显示器 {monitor_index + 1}: 区域({left},{top},{left+width},{top+height})"
            # )

            # 使用ImageGrab捕获指定区域
            bbox = (left, top, left + width, top + height)
            img = ImageGrab.grab(bbox=bbox)

            # print(
            #     f"备用方法成功捕获显示器 {monitor_index + 1} 截图: {img.width}x{img.height}"
            # )

            # 高质量调整图像大小
            max_width = self.quality_settings["single_monitor"]["max_width"]
            max_height = self.quality_settings["single_monitor"]["max_height"]
            img = self._resize_image_high_quality(img, max_width, max_height)

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
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )

            # 清理资源
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)

            # 高质量调整图像大小
            max_width = self.quality_settings["desktop"]["max_width"]
            max_height = self.quality_settings["desktop"]["max_height"]
            img = self._resize_image_high_quality(img, max_width, max_height)

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

            # 高质量调整图像大小
            max_width = self.quality_settings["desktop"]["max_width"]
            max_height = self.quality_settings["desktop"]["max_height"]
            screenshot = self._resize_image_high_quality(
                screenshot, max_width, max_height
            )

            self.counter += 1
            self.last_screenshot = screenshot
            self.last_screenshot_time = datetime.now()

            return screenshot

        except Exception as e:
            print(f"备用截图错误: {e}")
            return self._create_error_image()

    def _create_error_image(self, error_message: str = "无法捕获桌面截图"):
        """创建错误提示图像"""
        img = Image.new("RGB", (800, 600), color="lightgray")
        draw = ImageDraw.Draw(img)

        # 添加错误信息
        draw.text((400, 250), error_message, fill="red", anchor="mm")

        # 添加时间戳
        timestamp = f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text((400, 300), timestamp, fill="black", anchor="mm")

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

        # 转换为base64，使用高质量PNG
        buffer = io.BytesIO()
        img.save(
            buffer,
            format="PNG",
            optimize=ui_generator.quality_settings["optimize"],
            quality=ui_generator.quality_settings["png_quality"],
        )
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
            return {
                "error": f"显示器索引 {monitor_index} 超出范围，共有 {len(ui_generator.monitors)} 个显示器"
            }

        # 捕获指定显示器的截图
        img = ui_generator.capture_single_monitor(monitor_index)

        # 转换为base64，使用高质量PNG
        buffer = io.BytesIO()
        img.save(
            buffer,
            format="PNG",
            optimize=ui_generator.quality_settings["optimize"],
            quality=ui_generator.quality_settings["png_quality"],
        )
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        monitor = ui_generator.monitors[monitor_index]

        return {
            "monitor_index": monitor_index,
            "width": monitor["width"],
            "height": monitor["height"],
            "primary": monitor["primary"],
            "image": img_base64,
            "timestamp": datetime.now().isoformat(),
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

            # 转换为base64，使用高质量PNG
            buffer = io.BytesIO()
            img.save(
                buffer,
                format="PNG",
                optimize=ui_generator.quality_settings["optimize"],
                quality=ui_generator.quality_settings["png_quality"],
            )
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            screenshots.append(
                {
                    "monitor_index": i,
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "primary": monitor["primary"],
                    "image": img_base64,
                }
            )

        return {
            "screenshots": screenshots,
            "monitor_count": len(screenshots),
            "timestamp": datetime.now().isoformat(),
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
                "disk_usage": system_info["disk_usage"],
            }

            try:
                await websocket.send_text(json.dumps(data))
            except Exception as e:
                # 如果发送失败，说明连接可能已断开
                print(f"WebSocket发送失败: {e}")
                break

            # 0.8秒间隔，与前端一致
            await asyncio.sleep(0.8)
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
        "disk_usage": system_info["disk_usage"],
    }


@app.get("/test-network")
async def test_network():
    """手动测试网络连接"""
    network_monitor.check_network_status()
    network_info = network_monitor.get_network_info()
    return {
        "message": "网络测试完成",
        "network": network_info,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/system-info")
async def get_system_info():
    """获取系统资源信息"""
    try:
        system_info = system_monitor.get_system_info()

        # 获取更详细的系统信息
        memory = psutil.virtual_memory()
        cpu_count = psutil.cpu_count()
        disk = psutil.disk_usage("/")

        return {
            "memory": {
                "usage_percent": system_info["memory_usage"],
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
            },
            "cpu": {
                "usage_percent": system_info["cpu_usage"],
                "count": cpu_count,
                "frequency_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "usage_percent": round((disk.used / disk.total) * 100, 1),
            },
            "timestamp": datetime.now().isoformat(),
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
            monitors_info.append(
                {
                    "index": monitor["index"],
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "left": monitor["left"],
                    "top": monitor["top"],
                    "right": monitor["right"],
                    "bottom": monitor["bottom"],
                    "primary": monitor["primary"],
                    "area": monitor["width"] * monitor["height"],
                }
            )

        return {
            "system_info": {
                "monitor_count": monitor_count,
                "virtual_screen": {
                    "width": virtual_width,
                    "height": virtual_height,
                    "left": virtual_left,
                    "top": virtual_top,
                    "area": virtual_width * virtual_height,
                },
                "primary_screen": {
                    "width": primary_width,
                    "height": primary_height,
                    "area": primary_width * primary_height,
                },
            },
            "monitors": monitors_info,
            "detection_method": (
                "EnumDisplayMonitors" if len(monitors_info) > 1 else "Single Monitor"
            ),
            "timestamp": datetime.now().isoformat(),
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
            return {
                "error": f"显示器索引 {monitor_index} 超出范围，共有 {len(ui_generator.monitors)} 个显示器"
            }

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
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        return {
            "monitor_index": monitor_index,
            "monitor_info": {
                "width": monitor["width"],
                "height": monitor["height"],
                "left": monitor["left"],
                "top": monitor["top"],
                "right": monitor["right"],
                "bottom": monitor["bottom"],
                "primary": monitor["primary"],
            },
            "system_info": {
                "virtual_screen": f"{virtual_width}x{virtual_height} 位置({virtual_left},{virtual_top})",
                "primary_screen": f"{primary_width}x{primary_height}",
                "captured_image_size": f"{img.width}x{img.height}",
            },
            "image": img_base64,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/quality-settings")
async def update_quality_settings(settings: dict):
    """更新截图质量设置"""
    try:
        if "single_monitor" in settings:
            ui_generator.quality_settings["single_monitor"].update(
                settings["single_monitor"]
            )
        if "desktop" in settings:
            ui_generator.quality_settings["desktop"].update(settings["desktop"])
        if "png_quality" in settings:
            ui_generator.quality_settings["png_quality"] = settings["png_quality"]
        if "optimize" in settings:
            ui_generator.quality_settings["optimize"] = settings["optimize"]

        return {
            "message": "质量设置更新成功",
            "current_settings": ui_generator.quality_settings,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/quality-settings")
async def get_quality_settings():
    """获取当前截图质量设置"""
    return {
        "settings": ui_generator.quality_settings,
        "timestamp": datetime.now().isoformat(),
    }


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
            monitors_info.append(
                {
                    "index": monitor["index"],
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "left": monitor["left"],
                    "top": monitor["top"],
                    "right": monitor["right"],
                    "bottom": monitor["bottom"],
                    "primary": monitor["primary"],
                    "area": monitor["width"] * monitor["height"],
                }
            )

        return {
            "message": "显示器重新检测完成",
            "system_info": {
                "monitor_count": monitor_count,
                "virtual_screen": {
                    "width": virtual_width,
                    "height": virtual_height,
                    "left": virtual_left,
                    "top": virtual_top,
                    "area": virtual_width * virtual_height,
                },
                "primary_screen": {
                    "width": primary_width,
                    "height": primary_height,
                    "area": primary_width * primary_height,
                },
            },
            "monitors": monitors_info,
            "timestamp": datetime.now().isoformat(),
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
            monitors_info.append(
                {
                    "index": monitor["index"],
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "left": monitor["left"],
                    "top": monitor["top"],
                    "primary": monitor["primary"],
                }
            )

        return {
            "virtual_screen": {
                "width": virtual_width,
                "height": virtual_height,
                "left": virtual_left,
                "top": virtual_top,
            },
            "primary_screen": {"width": primary_width, "height": primary_height},
            "current_screenshot": {"width": current_width, "height": current_height},
            "monitors": monitors_info,
            "monitor_count": len(monitors_info),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


# 文件上传相关功能
# 使用系统Downloads文件夹作为默认上传目录
DEFAULT_UPLOAD_DIR = str(Path.home() / "Downloads")
ALLOWED_EXTENSIONS = {
    ".txt",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".zip",
    ".rar",
    ".7z",
}
UPLOAD_FILE_SIZE_LIMIT = 100

# 确保默认Downloads目录存在（通常已经存在）
if not os.path.exists(DEFAULT_UPLOAD_DIR):
    os.makedirs(DEFAULT_UPLOAD_DIR, exist_ok=True)


def get_upload_dir(folder_path=None):
    """获取上传目录路径"""
    if folder_path:
        # 检查是否是系统路径（绝对路径）
        if (
            os.path.isabs(folder_path)
            or folder_path.startswith("/")
            or ":" in folder_path
        ):
            # 系统路径，直接使用
            upload_dir = folder_path
        else:
            # Downloads子目录，在Downloads目录下创建子文件夹
            upload_dir = os.path.join(DEFAULT_UPLOAD_DIR, folder_path)

        # 确保目录存在
        os.makedirs(upload_dir, exist_ok=True)
        # 返回绝对路径，确保路径分隔符一致
        abs_upload_dir = os.path.abspath(upload_dir)
        return abs_upload_dir
    else:
        return DEFAULT_UPLOAD_DIR


def is_allowed_file(filename: str) -> bool:
    """检查文件扩展名是否允许"""
    if not filename:
        return False
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in ALLOWED_EXTENSIONS


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), folder_path: str = Form(None)):
    """上传单个文件"""
    try:
        # 检查文件大小 (限制为 UPLOAD_FILE_SIZE_LIMIT MB)
        if file.size and file.size > UPLOAD_FILE_SIZE_LIMIT * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail=f"文件大小超过{UPLOAD_FILE_SIZE_LIMIT}MB限制"
            )

        # 获取上传目录
        upload_dir = get_upload_dir(folder_path)

        # 生成安全的文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_ext = os.path.splitext(file.filename)[1].lower()
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)

        # 保存文件
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # 获取文件信息
        file_size = len(content)
        file_size_mb = round(file_size / (1024 * 1024), 2)

        response_data = {
            "message": "文件上传成功",
            "filename": safe_filename,
            "original_name": file.filename,
            "size_mb": file_size_mb,
            "upload_time": datetime.now().isoformat(),
            "file_path": file_path,
            "upload_dir": upload_dir,
        }
        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.post("/upload/multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...), folder_path: str = Form(None)
):
    """上传多个文件"""
    try:
        if not files:
            raise HTTPException(status_code=400, detail="没有选择文件")

        if len(files) > 10:
            raise HTTPException(status_code=400, detail="一次最多只能上传10个文件")

        # 获取上传目录
        upload_dir = get_upload_dir(folder_path)

        uploaded_files = []
        total_size = 0

        for file in files:
            # 检查文件大小
            if file.size and file.size > UPLOAD_FILE_SIZE_LIMIT * 1024 * 1024:
                continue  # 跳过过大的文件

            # 生成安全的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_ext = os.path.splitext(file.filename)[1].lower()
            safe_filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(upload_dir, safe_filename)

            # 保存文件
            content = await file.read()
            with open(file_path, "wb") as buffer:
                buffer.write(content)

            file_size = len(content)
            total_size += file_size

            uploaded_files.append(
                {
                    "filename": safe_filename,
                    "original_name": file.filename,
                    "size_mb": round(file_size / (1024 * 1024), 2),
                }
            )

        response_data = {
            "message": f"成功上传 {len(uploaded_files)} 个文件",
            "files": uploaded_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "upload_time": datetime.now().isoformat(),
            "upload_dir": upload_dir,
        }
        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@app.get("/files")
async def list_uploaded_files(folder: str = None):
    """获取已上传文件列表"""
    import time

    start_time = time.time()
    timeout_seconds = 15

    try:
        # 使用统一的路径处理逻辑
        list_dir = get_upload_dir(folder)
        if not os.path.exists(list_dir):
            return JSONResponse(
                {
                    "files": [],
                    "total_count": 0,
                    "total_size_mb": 0,
                    "current_folder": folder or "Downloads",
                }
            )

        files = []
        if os.path.exists(list_dir):
            for filename in os.listdir(list_dir):
                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    raise HTTPException(status_code=408, detail="请求超时")

                file_path = os.path.join(list_dir, filename)
                if os.path.isfile(file_path):
                    file_stat = os.stat(file_path)
                    files.append(
                        {
                            "filename": filename,
                            "size_mb": round(file_stat.st_size / (1024 * 1024), 2),
                            "upload_time": datetime.fromtimestamp(
                                file_stat.st_mtime
                            ).isoformat(),
                            "file_path": file_path,
                        }
                    )

        # 按上传时间倒序排列
        files.sort(key=lambda x: x["upload_time"], reverse=True)

        return JSONResponse(
            {
                "files": files,
                "total_count": len(files),
                "total_size_mb": round(sum(f["size_mb"] for f in files), 2),
                "current_folder": folder or "Downloads",
            }
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.get("/files/{filename}")
async def download_uploaded_file(filename: str, folder: str = None):
    """下载上传的文件"""
    try:
        # 使用统一的路径处理逻辑
        file_dir = get_upload_dir(folder)

        file_path = os.path.join(file_dir, filename)

        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 安全检查：确保文件路径是有效的
        try:
            # 验证路径是否在允许的范围内
            abs_file_path = os.path.abspath(file_path)
            abs_dir_path = os.path.abspath(file_dir)

            # 确保文件路径在目录路径内（防止路径遍历攻击）
            if not abs_file_path.startswith(abs_dir_path):
                raise HTTPException(status_code=400, detail="无效的文件路径")
        except Exception:
            raise HTTPException(status_code=400, detail="无效的文件路径")

        # 返回文件流
        return StreamingResponse(
            open(file_path, "rb"),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")


@app.delete("/files/{filename}")
async def delete_uploaded_file(filename: str, folder: str = None):
    """删除上传的文件"""
    try:
        # 使用统一的路径处理逻辑
        file_dir = get_upload_dir(folder)

        file_path = os.path.join(file_dir, filename)

        # 检查文件是否存在
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="文件不存在")

        # 安全检查：确保文件路径是有效的
        try:
            # 验证路径是否在允许的范围内
            abs_file_path = os.path.abspath(file_path)
            abs_dir_path = os.path.abspath(file_dir)

            # 确保文件路径在目录路径内（防止路径遍历攻击）
            if not abs_file_path.startswith(abs_dir_path):
                raise HTTPException(status_code=400, detail="无效的文件路径")
        except Exception:
            raise HTTPException(status_code=400, detail="无效的文件路径")

        # 删除文件
        os.remove(file_path)

        return JSONResponse({"message": "文件删除成功", "filename": filename})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件删除失败: {str(e)}")


@app.post("/delete_folder")
async def delete_folder(folder_data: dict):
    """删除文件夹"""
    try:
        import shutil

        folder_path = folder_data.get("folder_path")
        if not folder_path:
            raise HTTPException(status_code=400, detail="缺少文件夹路径参数")

        # 使用统一的路径处理逻辑
        target_dir = get_upload_dir(folder_path)

        # 检查文件夹是否存在
        if not os.path.exists(target_dir):
            raise HTTPException(status_code=404, detail="文件夹不存在")

        if not os.path.isdir(target_dir):
            raise HTTPException(status_code=400, detail="指定路径不是文件夹")

        # 安全检查：确保文件夹路径是有效的
        try:
            # 验证路径是否在允许的范围内
            abs_target_dir = os.path.abspath(target_dir)

            # 对于Downloads子目录，确保在Downloads目录内
            if not folder_path.startswith("/") and ":" not in folder_path:
                # Downloads子目录
                abs_downloads_dir = os.path.abspath(DEFAULT_UPLOAD_DIR)
                if not abs_target_dir.startswith(abs_downloads_dir):
                    raise HTTPException(
                        status_code=403, detail="不能删除Downloads目录外的文件夹"
                    )
            else:
                # 系统路径，进行额外的安全检查
                critical_paths = [
                    "C:\\",
                    "D:\\",
                    "E:\\",
                    "F:\\",
                    "/",
                    "/home",
                    "/root",
                    "/etc",
                    "/usr",
                    "/var",
                ]
                for critical in critical_paths:
                    if abs_target_dir == critical or abs_target_dir.startswith(
                        critical + os.sep
                    ):
                        raise HTTPException(
                            status_code=403, detail="不能删除系统关键目录"
                        )
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="无效的文件夹路径")

        # 删除文件夹及其所有内容
        shutil.rmtree(target_dir)

        return JSONResponse({"message": "文件夹删除成功", "folder_path": folder_path})

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件夹删除失败: {str(e)}")


@app.post("/create_folder")
async def create_folder(folder_data: dict):
    """创建新文件夹"""
    try:
        folder_name = folder_data.get("folder_name", "").strip()
        parent_path = folder_data.get("parent_path", "")
        if not folder_name:
            raise HTTPException(status_code=400, detail="文件夹名称不能为空")

        # 检查文件夹名称是否包含非法字符
        import re

        invalid_chars = r'[<>:"/\\|?*]'
        if re.search(invalid_chars, folder_name):
            raise HTTPException(status_code=400, detail="文件夹名称包含非法字符")

        # 构建完整路径
        if parent_path:
            # 检查是否是系统路径
            if parent_path.startswith("/") or re.match(r"^[A-Za-z]:\\", parent_path):
                # 系统路径
                full_path = os.path.join(parent_path, folder_name)
                # 安全检查：确保路径在允许的范围内
                if os.name == "nt":  # Windows
                    # 检查是否在系统关键目录之外
                    system_dirs = [
                        "C:\\Windows",
                        "C:\\System32",
                        "C:\\Program Files",
                        "C:\\Program Files (x86)",
                    ]
                    for sys_dir in system_dirs:
                        if full_path.startswith(sys_dir):
                            raise HTTPException(
                                status_code=403, detail="不能在系统目录中创建文件夹"
                            )
                else:  # Linux/Mac
                    forbidden_paths = [
                        "/etc",
                        "/var",
                        "/usr",
                        "/bin",
                        "/sbin",
                        "/boot",
                        "/dev",
                        "/proc",
                        "/sys",
                    ]
                    for forbidden in forbidden_paths:
                        if full_path.startswith(forbidden):
                            raise HTTPException(
                                status_code=403, detail="不能在系统目录中创建文件夹"
                            )
            else:
                # Downloads路径
                full_path = os.path.join(DEFAULT_UPLOAD_DIR, parent_path, folder_name)
                # 确保路径在Downloads目录内
                if not os.path.abspath(full_path).startswith(
                    os.path.abspath(DEFAULT_UPLOAD_DIR)
                ):
                    raise HTTPException(status_code=403, detail="访问被拒绝")
        else:
            # 在Downloads根目录创建
            full_path = os.path.join(DEFAULT_UPLOAD_DIR, folder_name)

        # 检查文件夹是否已存在
        if os.path.exists(full_path):
            raise HTTPException(status_code=409, detail="文件夹已存在")

        # 创建文件夹
        try:
            os.makedirs(full_path, exist_ok=False)
        except PermissionError:
            raise HTTPException(status_code=403, detail="没有权限创建文件夹")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"创建文件夹失败: {str(e)}")

        return JSONResponse(
            {
                "success": True,
                "message": f"文件夹 '{folder_name}' 创建成功",
                "folder_path": full_path,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建文件夹失败: {str(e)}")


@app.get("/directories")
async def list_available_directories(path: str = ""):
    """获取指定路径下的目录列表"""
    import time

    start_time = time.time()
    timeout_seconds = 10

    try:
        # URL解码路径参数
        import urllib.parse

        if path:
            path = urllib.parse.unquote(path)

        # 构建完整路径
        if path:
            full_path = os.path.join(DEFAULT_UPLOAD_DIR, path)
            # 确保路径在Downloads目录内
            if not os.path.abspath(full_path).startswith(
                os.path.abspath(DEFAULT_UPLOAD_DIR)
            ):
                raise HTTPException(status_code=403, detail="访问被拒绝")
        else:
            full_path = DEFAULT_UPLOAD_DIR

        # 确保路径存在
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="路径不存在")

        if not os.path.isdir(full_path):
            raise HTTPException(status_code=400, detail="指定路径不是目录")

        # 获取相对路径和父路径
        relative_path = path
        parent_path = os.path.dirname(relative_path) if relative_path else ""

        # 获取目录列表
        try:
            items = []
            timeout_occurred = False
            
            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)

                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    timeout_occurred = True
                    break

                if os.path.isdir(item_path):
                    # 计算文件夹数量，带超时处理
                    try:
                        folder_count = len(
                            [
                                f
                                for f in os.listdir(item_path)
                                if os.path.isdir(os.path.join(item_path, f))
                            ]
                        )
                    except PermissionError:
                        folder_count = 0
                    except Exception as e:
                        # 如果计算文件夹数量时出错（可能是超时或其他问题），返回特殊值
                        folder_count = -1  # 使用-1表示超时或错误

                    # 构建相对路径
                    if relative_path:
                        item_relative_path = os.path.join(relative_path, item)
                    else:
                        item_relative_path = item

                    # 确保路径使用正斜杠（前端期望的格式）
                    item_relative_path = item_relative_path.replace("\\", "/")

                    items.append(
                        {
                            "name": item,
                            "path": item_relative_path,
                            "file_count": folder_count,
                            "full_path": item_path,
                            "type": "directory",
                        }
                    )
        except PermissionError:
            raise HTTPException(status_code=403, detail="没有权限访问此目录")

        # 按名称排序
        items.sort(key=lambda x: x["name"].lower())

        response_data = {
            "items": items,
            "current_path": relative_path,
            "parent_path": parent_path,
            "base_path": DEFAULT_UPLOAD_DIR,
            "total_count": len(items),
            "can_go_up": relative_path != "",
        }
        
        # 如果发生了超时，添加超时信息
        if timeout_occurred:
            response_data["partial_results"] = True
            response_data["timeout_message"] = "部分目录因超时未能加载，已显示可访问的目录"
        
        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取目录列表失败: {str(e)}")


@app.get("/system-directories")
async def list_system_directories(path: str = ""):
    """浏览系统根目录下的文件系统"""
    import time

    start_time = time.time()
    timeout_seconds = 10

    try:
        # 构建目标路径
        if path:
            # 处理Windows路径的特殊情况
            if os.name == "nt":
                # 首先进行URL解码
                import urllib.parse

                try:
                    decoded_path = urllib.parse.unquote(path)
                    path = decoded_path
                except Exception as e:
                    pass

                # 处理Windows路径格式问题 - 支持所有盘符
                import re

                # 匹配盘符模式：如 "C:", "D:", "E:" 等
                drive_pattern = re.match(r"^([A-Za-z]:)(.+)$", path)
                if drive_pattern:
                    drive_letter = drive_pattern.group(1)
                    remaining_path = drive_pattern.group(2)
                    # 如果盘符后没有反斜杠，添加反斜杠
                    if not remaining_path.startswith("\\"):
                        path = drive_letter + "\\" + remaining_path

                # 确保路径中的反斜杠是正确的 - 支持所有盘符
                if re.match(r"^[A-Za-z]:\\", path):
                    # 替换所有正斜杠为反斜杠（如果存在）
                    path = path.replace("/", "\\")

            # 确保路径是绝对路径且安全
            if os.path.isabs(path):
                target_path = path
            else:
                target_path = os.path.abspath(path)
        else:
            # 根目录 - 在Windows上列出所有可用盘符
            if os.name == "nt":
                # 获取所有可用盘符
                import string

                available_drives = []
                for drive_letter in string.ascii_uppercase:
                    drive_path = f"{drive_letter}:\\"
                    if os.path.exists(drive_path):
                        available_drives.append(drive_path)

                if available_drives:
                    # 如果有可用盘符，返回盘符列表
                    items = []
                    timeout_occurred = False
                    
                    for drive in available_drives:
                        # 检查超时
                        if time.time() - start_time > timeout_seconds:
                            timeout_occurred = True
                            break

                        try:
                            # 获取盘符的卷标（如果可用）
                            import subprocess

                            try:
                                result = subprocess.run(
                                    ["vol", drive],
                                    capture_output=True,
                                    text=True,
                                    shell=True,
                                )
                                volume_label = (
                                    result.stdout.strip().split("\n")[-1]
                                    if result.stdout
                                    else ""
                                )
                            except:
                                volume_label = ""

                            # 计算该盘符下的文件夹数量，带超时处理
                            try:
                                folder_count = len(
                                    [
                                        f
                                        for f in os.listdir(drive)
                                        if os.path.isdir(os.path.join(drive, f))
                                    ]
                                )
                            except PermissionError:
                                folder_count = 0
                            except Exception as e:
                                # 如果计算文件夹数量时出错（可能是超时或其他问题），返回特殊值
                                folder_count = -1  # 使用-1表示超时或错误

                            items.append(
                                {
                                    "name": f"{drive} {volume_label}".strip(),
                                    "path": drive,
                                    "file_count": folder_count,
                                    "full_path": drive,
                                    "type": "drive",
                                }
                            )
                        except Exception as e:
                            # 如果处理某个盘符时出错，跳过该盘符，继续处理其他盘符
                            print(f"处理盘符 {drive} 时出错: {e}")
                            continue

                    response_data = {
                        "items": items,
                        "current_path": "",
                        "parent_path": "",
                        "base_path": "",
                        "total_count": len(items),
                        "can_go_up": False,
                    }
                    
                    # 如果发生了超时，添加超时信息
                    if timeout_occurred:
                        response_data["partial_results"] = True
                        response_data["timeout_message"] = "部分盘符因超时未能加载，已显示可访问的盘符"
                    
                    return JSONResponse(response_data)
                else:
                    # 如果没有可用盘符，使用C盘作为默认
                    target_path = "C:\\"
            else:
                target_path = "/"

        # 安全检查：防止访问系统关键目录（仅在非Windows系统上）
        if os.name != "nt":  # 非Windows系统
            forbidden_paths = [
                os.path.expanduser("~/.ssh"),
                "/etc/passwd",
                "/etc/shadow",
                "/proc",
                "/sys",
                "/dev",
            ]

            for forbidden in forbidden_paths:
                if target_path.startswith(forbidden):
                    raise HTTPException(status_code=403, detail="访问被拒绝")

        if not os.path.exists(target_path):
            raise HTTPException(status_code=404, detail="路径不存在")

        if not os.path.isdir(target_path):
            raise HTTPException(status_code=400, detail="指定路径不是目录")

        # 获取当前路径
        current_path = target_path

        # 获取父目录路径
        parent_path = ""
        if current_path != "/" and not (
            os.name == "nt" and re.match(r"^[A-Za-z]:\\$", current_path)
        ):
            parent_dir = os.path.dirname(current_path)
            if parent_dir == current_path:  # 已经是根目录
                parent_path = ""
            else:
                parent_path = parent_dir
                # 修复Windows路径问题：确保盘符后有反斜杠
                if os.name == "nt" and re.match(r"^[A-Za-z]:$", parent_path):
                    parent_path += "\\"

        # 获取目录列表
        try:
            items = []
            timeout_occurred = False
            
            for item in os.listdir(current_path):
                item_path = os.path.join(current_path, item)

                # 检查超时
                if time.time() - start_time > timeout_seconds:
                    timeout_occurred = True
                    break

                if os.path.isdir(item_path):
                    # 计算文件夹数量，带超时处理
                    try:
                        folder_count = len(
                            [
                                f
                                for f in os.listdir(item_path)
                                if os.path.isdir(os.path.join(item_path, f))
                            ]
                        )
                    except PermissionError:
                        folder_count = 0
                    except Exception as e:
                        # 如果计算文件夹数量时出错（可能是超时或其他问题），返回特殊值
                        folder_count = -1  # 使用-1表示超时或错误

                    items.append(
                        {
                            "name": item,
                            "path": item_path,
                            "file_count": folder_count,
                            "full_path": item_path,
                            "type": "directory",
                        }
                    )
        except PermissionError:
            raise HTTPException(
                status_code=403,
                detail = "没有权限访问此目录"
            )

        # 按名称排序
        items.sort(key=lambda x: x["name"].lower())

        response_data = {
            "items": items,
            "current_path": current_path,
            "parent_path": parent_path,
            "base_path": "",
            "total_count": len(items),
            "can_go_up": parent_path != "",
        }
        
        # 如果发生了超时，添加超时信息
        if timeout_occurred:
            response_data["partial_results"] = True
            response_data["timeout_message"] = "部分目录因超时未能加载，已显示可访问的目录"
        
        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统目录列表失败: {str(e)}")


if __name__ == "__main__":
    print("Starting Remote Viewer Server...")
    print("Access the application at: http://localhost:8000")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
