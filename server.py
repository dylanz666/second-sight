from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    Form,
    HTTPException,
)
import pyautogui
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
import psutil
from pathlib import Path
import asyncio
import json
import requests
from contextlib import asynccontextmanager
import platform
import socket

# 要请求的 GitHub Gist 接口地址
GIST_URL = None
GIST_HEADERS = None
try:
    with open("gist_info.txt", "r") as f:
        # 读取第一行为GIST_URL（去除首尾空白字符）
        GIST_URL = f.readline().strip()
        # 读取第二行为Authorization（去除首尾空白字符）
        auth_token = f.readline().strip()
        
        # 验证读取内容是否有效
        if not GIST_URL:
            raise ValueError("gist_info.txt中未找到有效的GIST URL（第一行）")
        if not auth_token:
            raise ValueError("gist_info.txt中未找到有效的Authorization信息（第二行）")
        
        # 构建请求头
        GIST_HEADERS = {
            "Authorization": auth_token,  # 使用文件中读取的认证信息
            "Content-Type": "application/json"
        }

except FileNotFoundError:
    raise FileNotFoundError("未找到gist_info.txt文件，请检查文件是否存在")
except Exception as e:
    raise Exception(f"读取文件时发生错误：{str(e)}")
# 每5分钟检查一次 ip，请求的间隔时间（秒），5分钟 = 300秒
REQUEST_INTERVAL = 300
LOCAL_IP = None
LOCAL_COMPUTER_NAME = platform.node()


def fetch_gist_sync():
    try:
        # 创建一个 socket 对象
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 连接到一个公共 DNS 服务器（例如 Google 的 8.8.8.8）
        s.connect(("8.8.8.8", 80))
        # 获取本地 IP 地址
        LOCAL_IP = s.getsockname()[0]
    finally:
        s.close()
    
    """同步请求 GitHub Gist 接口（使用 requests）"""
    try:
        # 发送GET请求，设置15秒超时
        response = requests.get(GIST_URL, timeout=15)
        if response.status_code != 200:
            print(f"获取 Gist 失败，状态码：{response.status_code}")
            return
         # 解析JSON响应（仅做演示，可根据需要处理内容）
        content = response.json()
        print(f"成功获取 Gist 内容，状态码：{response.status_code}")

        json_content = json.loads(content.get('files', {}).get('devices.json', {}).get('content', '{}'))            
        # 更新本地 IP 地址和电脑名到 gist 上
        if LOCAL_COMPUTER_NAME not in json_content or json_content.get(LOCAL_COMPUTER_NAME) != LOCAL_IP:
            json_content[LOCAL_COMPUTER_NAME] = LOCAL_IP
            payload = {
                "files": {
                    "devices.json": {
                        "content": json.dumps(json_content, indent=2)
                    }
                }
            }
            patch_response = requests.patch(
                url=GIST_URL,
                headers=GIST_HEADERS,
                data=json.dumps(payload)
            )
            if patch_response.status_code != 200:
                print(f"更新 Gist 失败，状态码：{response.status_code}")
                return
            print(f"成功更新 Gist 内容：{json_content}")
            return
        print("无需更新 Gist 内容")
    except Exception as e:
        print(f"请求发生错误：{str(e)}")
        return False

async def periodic_fetch():
    """周期性执行同步请求的异步任务（通过线程转换避免阻塞）"""
    while True:
        # 将同步函数放入线程池执行，避免阻塞事件循环
        await asyncio.to_thread(fetch_gist_sync)
        # 等待指定的时间间隔
        await asyncio.sleep(REQUEST_INTERVAL)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI的生命周期管理器，用于启动和停止后台任务"""
    # 启动时创建并运行后台任务
    task = asyncio.create_task(periodic_fetch())
    yield
    # 关闭时取消后台任务
    task.cancel()
    await task
    
app = FastAPI(lifespan=lifespan, title="Remote Viewer Server", version="1.0.0")

# 配置静态文件服务
app.mount("/static", StaticFiles(directory="static"), name="static")

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理器，确保所有异常都返回JSON格式"""
    import traceback

    # 记录错误详情
    error_msg = f"服务器内部错误: {str(exc)}"
    print(f"全局异常处理器捕获到错误: {error_msg}")
    traceback.print_exc()

    # 返回JSON格式的错误响应
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": error_msg,
            "error_type": type(exc).__name__,
            "timestamp": datetime.now().isoformat(),
        },
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


# 键鼠控制器
class RemoteController:
    def __init__(self):
        # 禁用pyautogui的安全机制，允许远程控制
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.1  # 操作间隔

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        """执行鼠标点击"""
        try:
            pyautogui.click(x, y, clicks=clicks, button=button)
            return {"success": True, "message": f"点击成功: ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"点击失败: {str(e)}"}

    def double_click(self, x: int, y: int, button: str = "left"):
        """执行鼠标双击"""
        try:
            pyautogui.doubleClick(x, y, button=button)
            return {"success": True, "message": f"双击成功: ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"双击失败: {str(e)}"}

    def right_click(self, x: int, y: int):
        """执行鼠标右键点击"""
        try:
            pyautogui.rightClick(x, y)
            return {"success": True, "message": f"右键点击成功: ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"右键点击失败: {str(e)}"}

    def drag(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5
    ):
        """执行鼠标拖拽"""
        try:
            # 移动到起始位置并按下鼠标
            pyautogui.moveTo(start_x, start_y)
            pyautogui.mouseDown(button="left")
            # 拖拽到结束位置
            pyautogui.moveTo(end_x, end_y, duration=duration)
            pyautogui.mouseUp(button="left")
            return {
                "success": True,
                "message": f"拖拽成功: ({start_x}, {start_y}) -> ({end_x}, {end_y})",
            }
        except Exception as e:
            return {"success": False, "message": f"拖拽失败: {str(e)}"}

    def type_text(self, text: str):
        """输入文本"""
        try:
            pyautogui.typewrite(text)
            return {"success": True, "message": f"文本输入成功: {text}"}
        except Exception as e:
            return {"success": False, "message": f"文本输入失败: {str(e)}"}

    def press_key(self, key: str):
        """按下单个按键"""
        try:
            pyautogui.press(key)
            return {"success": True, "message": f"按键成功: {key}"}
        except Exception as e:
            return {"success": False, "message": f"按键失败: {str(e)}"}

    def hotkey(self, *keys):
        """执行组合键"""
        try:
            pyautogui.hotkey(*keys)
            return {"success": True, "message": f"组合键成功: {'+'.join(keys)}"}
        except Exception as e:
            return {"success": False, "message": f"组合键失败: {str(e)}"}

    def scroll(self, x: int, y: int, clicks: int):
        """执行鼠标滚轮"""
        try:
            pyautogui.scroll(clicks, x=x, y=y)
            return {"success": True, "message": f"滚轮成功: ({x}, {y}) 滚动 {clicks}"}
        except Exception as e:
            return {"success": False, "message": f"滚轮失败: {str(e)}"}

    def get_mouse_position(self):
        """获取当前鼠标位置"""
        try:
            x, y = pyautogui.position()
            return {"success": True, "x": x, "y": y}
        except Exception as e:
            return {"success": False, "message": f"获取鼠标位置失败: {str(e)}"}


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
remote_controller = RemoteController()


# Windows桌面截图生成器
class DesktopScreenshotGenerator:
    def __init__(self):
        self.counter = 0
        self.last_screenshot = None
        self.last_screenshot_time = None
        self.monitors = []
        # 截图质量配置 - 优化后的设置
        self.quality_settings = {
            "single_monitor": {"max_width": 1200, "max_height": 900},  # 降低默认尺寸
            "desktop": {"max_width": 1600, "max_height": 1000},  # 降低默认尺寸
            "png_quality": 60,  # 降低PNG质量以减小文件大小
            "jpeg_quality": 60,  # 新增JPEG质量设置
            "optimize": True,  # 启用PNG优化
            "use_jpeg": True,  # 是否使用JPEG格式（更小但质量稍低）
            "compression_level": 6,  # PNG压缩级别 (0-9, 9为最高压缩)
        }
        # 内存缓存
        self.image_cache = {}
        self.cache_max_size = 3  # 最大缓存数量
        self.cache_ttl = 1.5  # 缓存生存时间（秒）
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

    def _get_cache_key(self, monitor_index, quality_settings):
        """生成缓存键"""
        return f"monitor_{monitor_index}_{hash(str(quality_settings))}"

    def _clean_cache(self):
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = []

        for key, (image_data, timestamp) in self.image_cache.items():
            if current_time - timestamp > self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.image_cache[key]

    def _add_to_cache(self, key, image_data):
        """添加到缓存"""
        # 清理过期缓存
        self._clean_cache()

        # 如果缓存已满，删除最旧的条目
        if len(self.image_cache) >= self.cache_max_size:
            oldest_key = min(
                self.image_cache.keys(), key=lambda k: self.image_cache[k][1]
            )
            del self.image_cache[oldest_key]

        # 添加新条目
        self.image_cache[key] = (image_data, time.time())

    def _get_from_cache(self, key):
        """从缓存获取数据"""
        if key in self.image_cache:
            image_data, timestamp = self.image_cache[key]
            if time.time() - timestamp <= self.cache_ttl:
                return image_data
            else:
                # 删除过期缓存
                del self.image_cache[key]
        return None

    def _optimize_image_for_transmission(self, img, monitor_index):
        """优化图像以减小传输大小"""
        # 生成缓存键
        cache_key = self._get_cache_key(monitor_index, self.quality_settings)

        # 检查缓存
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # 获取质量设置
        max_width = self.quality_settings["single_monitor"]["max_width"]
        max_height = self.quality_settings["single_monitor"]["max_height"]

        # 调整图像大小
        img = self._resize_image_high_quality(img, max_width, max_height)

        # 转换为base64
        buffer = io.BytesIO()

        if self.quality_settings["use_jpeg"]:
            # 使用JPEG格式（更小）
            img.save(
                buffer,
                format="JPEG",
                quality=self.quality_settings["jpeg_quality"],
                optimize=True,
            )
        else:
            # 使用PNG格式
            img.save(
                buffer,
                format="PNG",
                optimize=self.quality_settings["optimize"],
                quality=self.quality_settings["png_quality"],
                compress_level=self.quality_settings["compression_level"],
            )

        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        # 添加到缓存
        self._add_to_cache(cache_key, img_base64)

        return img_base64

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

# 启动时初始化显示器信息
try:
    print("正在初始化显示器信息...")
    ui_generator.update_monitor_info()
    print(f"显示器信息初始化完成，检测到 {len(ui_generator.monitors)} 个显示器")
    for i, monitor in enumerate(ui_generator.monitors):
        print(
            f"  显示器 {i}: {monitor['width']}x{monitor['height']} 位置({monitor['left']},{monitor['top']})"
        )
except Exception as e:
    print(f"显示器信息初始化失败: {e}")
    import traceback

    traceback.print_exc()

# 跟踪被收起的显示器（后端状态）
collapsed_monitors = set()


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

        # 检查显示器是否被收起
        if monitor_index in collapsed_monitors:
            return {
                "error": f"显示器 {monitor_index} 已被收起，无法获取截图",
                "monitor_index": monitor_index,
                "collapsed": True,
                "timestamp": datetime.now().isoformat(),
            }

        # 捕获指定显示器的截图
        img = ui_generator.capture_single_monitor(monitor_index)

        # 使用优化的图像传输函数
        img_base64 = ui_generator._optimize_image_for_transmission(img, monitor_index)

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
    """获取所有未收起显示器的截图"""
    try:
        screenshots = []

        # 更新显示器信息
        ui_generator.update_monitor_info()

        # 获取总显示器数量
        import win32api
        import win32con

        total_monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)

        # 只处理未收起的显示器
        for i, monitor in enumerate(ui_generator.monitors):
            # 跳过被收起的显示器
            if i in collapsed_monitors:
                continue

            # 只处理活跃的显示器：捕获截图
            img = ui_generator.capture_single_monitor(i)

            # 使用优化的图像传输函数
            img_base64 = ui_generator._optimize_image_for_transmission(img, i)

            screenshots.append(
                {
                    "monitor_index": i,
                    "width": monitor["width"],
                    "height": monitor["height"],
                    "primary": monitor["primary"],
                    "image": img_base64,
                    "collapsed": False,
                }
            )

        return {
            "screenshots": screenshots,
            "monitor_count": len(screenshots),
            "total_monitor_count": total_monitor_count,
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
        if "jpeg_quality" in settings:
            ui_generator.quality_settings["jpeg_quality"] = settings["jpeg_quality"]
        if "optimize" in settings:
            ui_generator.quality_settings["optimize"] = settings["optimize"]
        if "use_jpeg" in settings:
            ui_generator.quality_settings["use_jpeg"] = settings["use_jpeg"]
        if "compression_level" in settings:
            ui_generator.quality_settings["compression_level"] = settings[
                "compression_level"
            ]

        # 清除缓存以应用新设置
        ui_generator.image_cache.clear()

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


@app.get("/cache-stats")
async def get_cache_stats():
    """获取缓存统计信息"""
    try:
        cache_size = len(ui_generator.image_cache)
        cache_keys = list(ui_generator.image_cache.keys())

        # 计算缓存命中率（这里简化处理，实际需要更复杂的统计）
        total_requests = ui_generator.counter
        cache_hits = sum(
            1 for key in cache_keys if ui_generator._get_from_cache(key) is not None
        )

        return {
            "cache_size": cache_size,
            "max_cache_size": ui_generator.cache_max_size,
            "cache_ttl_seconds": ui_generator.cache_ttl,
            "cache_keys": cache_keys,
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "cache_hit_rate": round((cache_hits / max(total_requests, 1)) * 100, 2),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/clear-cache")
async def clear_cache():
    """清除图像缓存"""
    try:
        cache_size = len(ui_generator.image_cache)
        ui_generator.image_cache.clear()

        return {
            "message": f"缓存已清除，共清除 {cache_size} 个缓存项",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/collapsed-monitors")
async def update_collapsed_monitors(collapsed_data: dict):
    """更新被收起的显示器状态"""
    global collapsed_monitors
    try:
        collapsed_indices = collapsed_data.get("collapsed_monitors", [])
        collapsed_monitors = set(collapsed_indices)

        return {
            "message": "被收起的显示器状态更新成功",
            "collapsed_monitors": list(collapsed_monitors),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/collapsed-monitors")
async def get_collapsed_monitors():
    """获取当前被收起的显示器状态"""
    return {
        "collapsed_monitors": list(collapsed_monitors),
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


@app.delete("/delete_folder")
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
            response_data["timeout_message"] = (
                "部分目录因超时未能加载，已显示可访问的目录"
            )

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
                        response_data["timeout_message"] = (
                            "部分盘符因超时未能加载，已显示可访问的盘符"
                        )

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
            raise HTTPException(status_code=403, detail="没有权限访问此目录")

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
            response_data["timeout_message"] = (
                "部分目录因超时未能加载，已显示可访问的目录"
            )

        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统目录列表失败: {str(e)}")


# ==================== 远程键鼠控制API ====================


@app.post("/remote/click")
async def remote_click(data: dict):
    """远程鼠标点击"""
    try:
        # 验证输入数据
        if not isinstance(data, dict):
            return JSONResponse({"success": False, "message": "无效的请求数据格式"})

        x = data.get("x")
        y = data.get("y")
        button = data.get("button", "left")
        clicks = data.get("clicks", 1)
        monitor_index = data.get("monitor_index", 0)
        use_percentage = data.get("use_percentage", False)

        coord_type = "百分比" if use_percentage else "像素"
        print(
            f"收到远程点击请求: {coord_type} x={x}, y={y}, monitor_index={monitor_index}"
        )

        if x is None or y is None:
            return JSONResponse({"success": False, "message": "缺少坐标参数"})

        # 验证坐标类型
        try:
            x = float(x)
            y = float(y)
        except (ValueError, TypeError):
            return JSONResponse({"success": False, "message": "坐标参数必须是数字"})

        # 验证显示器索引
        if not hasattr(ui_generator, "monitors") or not ui_generator.monitors:
            print("警告: 显示器信息未初始化，尝试更新...")
            try:
                ui_generator.update_monitor_info()
            except Exception as e:
                print(f"更新显示器信息失败: {e}")
                return JSONResponse(
                    {"success": False, "message": "显示器信息初始化失败"}
                )

        # 坐标转换：从截图坐标转换为实际屏幕坐标
        try:
            actual_x, actual_y = convert_screenshot_coords_to_screen(
                x, y, monitor_index, use_percentage
            )
            print(f"坐标转换: ({x}, {y}) -> ({actual_x}, {actual_y})")
        except Exception as e:
            print(f"坐标转换失败: {e}")
            return JSONResponse(
                {"success": False, "message": f"坐标转换失败: {str(e)}"}
            )

        # 执行点击操作
        try:
            result = remote_controller.click(actual_x, actual_y, button, clicks)
            print(f"点击操作结果: {result}")
            return JSONResponse(result)
        except Exception as e:
            print(f"pyautogui点击操作失败: {e}")
            return JSONResponse(
                {"success": False, "message": f"点击操作执行失败: {str(e)}"}
            )

    except Exception as e:
        error_msg = f"点击操作失败: {str(e)}"
        print(f"远程点击异常: {error_msg}")
        import traceback

        traceback.print_exc()
        return JSONResponse({"success": False, "message": error_msg})


@app.post("/remote/double-click")
async def remote_double_click(data: dict):
    """远程鼠标双击"""
    try:
        x = data.get("x")
        y = data.get("y")
        button = data.get("button", "left")
        monitor_index = data.get("monitor_index", 0)
        use_percentage = data.get("use_percentage", False)

        if x is None or y is None:
            return JSONResponse({"success": False, "message": "缺少坐标参数"})

        # 验证坐标类型
        try:
            x = float(x)
            y = float(y)
        except (ValueError, TypeError):
            return JSONResponse({"success": False, "message": "坐标参数必须是数字"})

        # 坐标转换
        try:
            actual_x, actual_y = convert_screenshot_coords_to_screen(
                x, y, monitor_index, use_percentage
            )
        except Exception as e:
            return JSONResponse(
                {"success": False, "message": f"坐标转换失败: {str(e)}"}
            )

        result = remote_controller.double_click(actual_x, actual_y, button)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"success": False, "message": f"双击操作失败: {str(e)}"})


@app.post("/remote/right-click")
async def remote_right_click(data: dict):
    """远程鼠标右键点击"""
    try:
        # 验证输入数据
        if not isinstance(data, dict):
            return JSONResponse({"success": False, "message": "无效的请求数据格式"})

        x = data.get("x")
        y = data.get("y")
        monitor_index = data.get("monitor_index", 0)
        use_percentage = data.get("use_percentage", False)

        if x is None or y is None:
            return JSONResponse({"success": False, "message": "缺少坐标参数"})

        # 验证坐标类型
        try:
            x = float(x)
            y = float(y)
        except (ValueError, TypeError):
            return JSONResponse({"success": False, "message": "坐标参数必须是数字"})

        # 坐标转换
        try:
            actual_x, actual_y = convert_screenshot_coords_to_screen(
                x, y, monitor_index, use_percentage
            )
        except Exception as e:
            return JSONResponse(
                {"success": False, "message": f"坐标转换失败: {str(e)}"}
            )

        result = remote_controller.right_click(actual_x, actual_y)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"右键点击操作失败: {str(e)}"}
        )


@app.post("/remote/drag")
async def remote_drag(data: dict):
    """远程鼠标拖拽"""
    try:
        start_x = data.get("start_x")
        start_y = data.get("start_y")
        end_x = data.get("end_x")
        end_y = data.get("end_y")
        duration = data.get("duration", 0.5)
        monitor_index = data.get("monitor_index", 0)
        use_percentage = data.get("use_percentage", False)

        if start_x is None or start_y is None or end_x is None or end_y is None:
            raise HTTPException(status_code=400, detail="缺少坐标参数")

        # 坐标转换
        actual_start_x, actual_start_y = convert_screenshot_coords_to_screen(
            start_x, start_y, monitor_index, use_percentage
        )
        actual_end_x, actual_end_y = convert_screenshot_coords_to_screen(
            end_x, end_y, monitor_index, use_percentage
        )

        result = remote_controller.drag(
            actual_start_x, actual_start_y, actual_end_x, actual_end_y, duration
        )
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"success": False, "message": f"拖拽操作失败: {str(e)}"})


@app.post("/remote/type")
async def remote_type(data: dict):
    """远程文本输入"""
    try:
        text = data.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="缺少文本参数")

        result = remote_controller.type_text(text)
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"success": False, "message": f"文本输入失败: {str(e)}"})


@app.post("/remote/press-key")
async def remote_press_key(data: dict):
    """远程按键"""
    try:
        key = data.get("key")
        if not key:
            raise HTTPException(status_code=400, detail="缺少按键参数")

        # 支持方向键的别名
        key_aliases = {
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "arrowup": "up",
            "arrowdown": "down",
            "arrowleft": "left",
            "arrowright": "right",
        }
        key_lower = key.lower()
        if key_lower in key_aliases:
            key = key_aliases[key_lower]
        result = remote_controller.press_key(key)
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"success": False, "message": f"按键操作失败: {str(e)}"})


@app.post("/remote/hotkey")
async def remote_hotkey(data: dict):
    """远程组合键"""
    try:
        keys = data.get("keys", [])
        if not keys:
            raise HTTPException(status_code=400, detail="缺少组合键参数")

        result = remote_controller.hotkey(*keys)
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"success": False, "message": f"组合键操作失败: {str(e)}"})


@app.post("/remote/scroll")
async def remote_scroll(data: dict):
    """远程鼠标滚轮"""
    try:
        x = data.get("x")
        y = data.get("y")
        clicks = data.get("clicks", 3)
        monitor_index = data.get("monitor_index", 0)
        use_percentage = data.get("use_percentage", False)

        if x is None or y is None:
            raise HTTPException(status_code=400, detail="缺少坐标参数")

        # 坐标转换
        actual_x, actual_y = convert_screenshot_coords_to_screen(
            x, y, monitor_index, use_percentage
        )

        # 放大滚动幅度（如每次滚动乘以10，可根据实际需要调整倍数）
        amplified_clicks = int(clicks) * 10

        # 先移动鼠标到指定位置，再滚动
        try:
            pyautogui.moveTo(actual_x, actual_y)
            pyautogui.scroll(amplified_clicks)
            result = {
                "success": True,
                "message": f"滚轮成功: ({actual_x}, {actual_y}) 滚动 {amplified_clicks}",
            }
        except Exception as e:
            result = {"success": False, "message": f"滚轮失败: {str(e)}"}
        return JSONResponse(result)
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"success": False, "message": f"滚轮操作失败: {str(e)}"})


@app.get("/remote/mouse-position")
async def get_mouse_position():
    """获取当前鼠标位置"""
    try:
        result = remote_controller.get_mouse_position()
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"获取鼠标位置失败: {str(e)}"}
        )


def convert_screenshot_coords_to_screen(
    x: float, y: float, monitor_index: int = 0, use_percentage: bool = False
):
    """将截图坐标转换为实际屏幕坐标"""
    try:
        # 验证输入参数
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(
                f"坐标参数必须是数字，收到: x={type(x)}({x}), y={type(y)}({y})"
            )

        if not isinstance(monitor_index, int) or monitor_index < 0:
            raise ValueError(f"显示器索引必须是正整数，收到: {monitor_index}")

        # 获取显示器信息
        if not hasattr(ui_generator, "monitors"):
            raise RuntimeError("ui_generator.monitors 属性不存在")

        monitors = ui_generator.monitors
        if not monitors:
            print("警告: 显示器列表为空，尝试更新显示器信息...")
            try:
                ui_generator.update_monitor_info()
                monitors = ui_generator.monitors
                if not monitors:
                    raise RuntimeError("无法获取显示器信息")
            except Exception as e:
                raise RuntimeError(f"更新显示器信息失败: {e}")

        if monitor_index >= len(monitors):
            raise ValueError(f"显示器索引超出范围: {monitor_index} >= {len(monitors)}")

        monitor = monitors[monitor_index]
        if not isinstance(monitor, dict):
            raise ValueError(f"显示器信息格式错误: {type(monitor)}")

        # 验证显示器信息完整性
        required_keys = ["left", "top", "width", "height"]
        for key in required_keys:
            if key not in monitor or not isinstance(monitor[key], (int, float)):
                raise ValueError(f"显示器信息缺少或无效的 {key}: {monitor.get(key)}")

        monitor_left = int(monitor["left"])
        monitor_top = int(monitor["top"])
        monitor_width = int(monitor["width"])
        monitor_height = int(monitor["height"])

        # 验证显示器尺寸
        if monitor_width <= 0 or monitor_height <= 0:
            raise ValueError(f"显示器尺寸无效: {monitor_width}x{monitor_height}")

        if use_percentage:
            # 百分比坐标转换：直接使用百分比计算实际屏幕位置
            if not (0 <= x <= 100 and 0 <= y <= 100):
                raise ValueError(f"百分比坐标超出范围: x={x}%, y={y}%")

            actual_x = int(monitor_left + (x / 100.0) * monitor_width)
            actual_y = int(monitor_top + (y / 100.0) * monitor_height)
            print(
                f"百分比坐标转换: 显示器{monitor_index} ({monitor_left},{monitor_top}) {monitor_width}x{monitor_height}, 百分比({x:.2f}%, {y:.2f}%) -> 实际({actual_x}, {actual_y})"
            )
        else:
            # 像素坐标转换：考虑截图缩放
            screenshot_width = monitor.get("screenshot_width", monitor_width)
            screenshot_height = monitor.get("screenshot_height", monitor_height)

            # 验证截图尺寸
            if screenshot_width <= 0 or screenshot_height <= 0:
                screenshot_width = monitor_width
                screenshot_height = monitor_height

            # 计算缩放比例
            scale_x = monitor_width / screenshot_width if screenshot_width > 0 else 1
            scale_y = monitor_height / screenshot_height if screenshot_height > 0 else 1

            # 转换坐标
            actual_x = int(monitor_left + x * scale_x)
            actual_y = int(monitor_top + y * scale_y)
            print(
                f"像素坐标转换: 显示器{monitor_index} ({monitor_left},{monitor_top}) {monitor_width}x{monitor_height}, 截图尺寸 {screenshot_width}x{screenshot_height}, 缩放比例 {scale_x:.2f}x{scale_y:.2f}, 像素({x}, {y}) -> 实际({actual_x}, {actual_y})"
            )

        # 验证转换后的坐标是否在合理范围内
        if actual_x < 0 or actual_y < 0:
            print(f"警告: 转换后的坐标为负值: ({actual_x}, {actual_y})")

        return actual_x, actual_y

    except Exception as e:
        print(f"坐标转换失败: {e}")
        import traceback

        traceback.print_exc()
        # 转换失败时抛出异常，让调用者处理
        raise RuntimeError(f"坐标转换失败: {str(e)}")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
