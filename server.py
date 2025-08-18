import threading
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
from datetime import datetime, timezone
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
import win32api
import win32con
import win32gui
import win32ui

APP_VERSION = "1.0.0"
# GitHub Gist API URL to request
USE_GIST = ""
GIST_URL = None
GIST_HEADERS = None
# Check IP every 2 minutes, request interval in seconds (120 seconds = 2 minutes)
REQUEST_INTERVAL = 120
LOCAL_IP = None
LOCAL_COMPUTER_NAME = platform.node()

try:
    with open("gist_info.json", "r") as f:
        # Read JSON data
        data = json.load(f)
        USE_GIST = data.get("use_gist")
        if USE_GIST.lower() == "true":
            # Extract GIST_URL and token from JSON data
            GIST_URL = data.get("gist_url")
            auth_token = data.get("token")

            # Validate the content read
            if not GIST_URL:
                raise ValueError(
                    "No valid GIST URL (gist_url) found in gist_info.json")
            if not auth_token:
                raise ValueError(
                    "No valid Authorization information (token) found in gist_info.json")

            # Build request headers
            GIST_HEADERS = {
                "Authorization": auth_token,  # Use authentication info read from file
                "Content-Type": "application/json",
            }
except FileNotFoundError:
    print("Error: gist_info.json file not found.")
except json.JSONDecodeError:
    print("Error: Invalid gist_info.json file format.")
except Exception as e:
    print(f"An error occurred: {e}")


def fetch_gist_sync():
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Connect to a public DNS server (e.g. Google's 8.8.8.8)
        s.connect(("8.8.8.8", 80))
        # Get local IP address
        LOCAL_IP = s.getsockname()[0]
        print("Local IP address:", LOCAL_IP)
    finally:
        s.close()

    """Synchronously request GitHub Gist API (using requests)"""
    try:
        # Send GET request with 15 second timeout
        response = requests.get(GIST_URL, headers=GIST_HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"Failed to get Gist, status code: {response.status_code}")
            return
        # Parse JSON response (for demonstration, handle content as needed)
        content = response.json()
        print(
            f"Successfully got Gist content, status code: {response.status_code}")

        devices_content = content.get("files", {}).get(
            "devices.json", {}).get("content", "{}")
        json_content = json.loads(devices_content)

        # Update computer name, local IP address, timestamp to gist -> like heartbeat
        json_content[LOCAL_COMPUTER_NAME] = {
            "ip": LOCAL_IP,
            "timestamp": get_baidu_timestamp(),
        }
        payload = {
            "files": {
                "devices.json": {
                    "content": json.dumps(json_content)
                }
            }
        }
        print(f"Updating Gist content: {payload}")
        patch_response = requests.patch(
            url=GIST_URL, headers=GIST_HEADERS, json=payload
        )
        patch_response.raise_for_status()
        print(f"Successfully updated Gist content: {json_content}")
    except Exception as e:
        print(f"Request error occurred: {str(e)}")
        return False


async def periodic_fetch():
    """Asynchronous task for periodic synchronization request (using thread conversion to avoid blocking)"""
    while True:
        # Execute synchronous function in thread pool to avoid blocking event loop
        await asyncio.to_thread(fetch_gist_sync)
        # Wait for specified time interval
        await asyncio.sleep(REQUEST_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle manager for starting and stopping background tasks"""
    # Create and run background task on startup
    task = asyncio.create_task(periodic_fetch())
    yield
    # Cancel background task on shutdown
    task.cancel()
    await task


def get_baidu_timestamp():
    """Get network timestamp (seconds) from Baidu"""
    try:
        # Send HEAD request (get response headers only, no content download)
        response = requests.head("https://www.baidu.com", timeout=10)
        # Get GMT time string from response header
        gmt_time_str = response.headers.get("Date")
        if not gmt_time_str:
            return None

        # Parse GMT time to timestamp (convert to Unix timestamp, force UTC)
        gmt_time = datetime.strptime(gmt_time_str, "%a, %d %b %Y %H:%M:%S GMT")
        gmt_time = gmt_time.replace(tzinfo=timezone.utc)  # Key: specify as UTC
        return int(gmt_time.timestamp())
    except Exception as e:
        print(f"Failed to get timestamp: {e}")
        return -1


# Handle both cases: with and without GIST
if USE_GIST.lower() != "true":
    print("Configured to not use Gist, skipping sync task")
    app = FastAPI(title="Remote Viewer Server", version=APP_VERSION)
else:
    if GIST_URL is None or GIST_HEADERS is None:
        print("Gist URL or Authorization not configured, cannot start periodic task")
        app = FastAPI(title="Remote Viewer Server", version=APP_VERSION)
    else:
        print("Gist URL and Authorization configured, starting periodic task")
        app = FastAPI(lifespan=lifespan,
                      title="Remote Viewer Server", version=APP_VERSION)

# Configure static file service
app.mount("/static", StaticFiles(directory="static"), name="static")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global exception handler


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler, ensures all exceptions return JSON format"""
    import traceback

    # Log error details
    error_msg = f"Internal server error: {str(exc)}"
    print(f"Global exception handler caught error: {error_msg}")
    traceback.print_exc()

    # Return JSON error response
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
        """Check network connection status every 2 seconds"""
        try:
            # Test connect to Google DNS (8.8.8.8)
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
        """Get network status information"""
        # Check network status every 30 seconds
        if self.last_check_time is None or time.time() - self.last_check_time > 30:
            self.check_network_status()

        return {
            "status": self.network_status,
            "latency": self.ping_latency,
            "last_check": self.last_check_time,
        }


# Mouse and Keyboard Controller
class RemoteController:
    def __init__(self):
        # Disable pyautogui's fail-safe mechanism to allow remote control
        pyautogui.FAILSAFE = False
        pyautogui.PAUSE = 0.1  # Operation interval

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1):
        """Execute mouse click"""
        try:
            pyautogui.click(x, y, clicks=clicks, button=button)
            return {"success": True, "message": f"Click successful: ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"Click failed: {str(e)}"}

    def double_click(self, x: int, y: int, button: str = "left"):
        """Execute mouse double click"""
        try:
            pyautogui.doubleClick(x, y, button=button)
            return {"success": True, "message": f"Double click successful: ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"Double click failed: {str(e)}"}

    def right_click(self, x: int, y: int):
        """Execute mouse right click"""
        try:
            pyautogui.rightClick(x, y)
            return {"success": True, "message": f"Right click successful: ({x}, {y})"}
        except Exception as e:
            return {"success": False, "message": f"Right click failed: {str(e)}"}

    def drag(
        self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5
    ):
        """Execute mouse drag"""
        try:
            # Move to start position and press mouse button
            pyautogui.moveTo(start_x, start_y)
            pyautogui.mouseDown(button="left")
            # Drag to end position
            pyautogui.moveTo(end_x, end_y, duration=duration)
            pyautogui.mouseUp(button="left")
            return {
                "success": True,
                "message": f"Drag successful: ({start_x}, {start_y}) -> ({end_x}, {end_y})",
            }
        except Exception as e:
            return {"success": False, "message": f"Drag failed: {str(e)}"}

    def type_text(self, text: str):
        """Input text"""
        try:
            pyautogui.typewrite(text)
            return {"success": True, "message": f"Text input successful: {text}"}
        except Exception as e:
            return {"success": False, "message": f"Text input failed: {str(e)}"}

    def press_key(self, key: str):
        """Press single key"""
        try:
            pyautogui.press(key)
            return {"success": True, "message": f"Key press successful: {key}"}
        except Exception as e:
            return {"success": False, "message": f"Key press failed: {str(e)}"}

    def hotkey(self, *keys):
        """Execute key combination"""
        try:
            pyautogui.hotkey(*keys)
            return {"success": True, "message": f"Hotkey successful: {'+'.join(keys)}"}
        except Exception as e:
            return {"success": False, "message": f"Hotkey failed: {str(e)}"}

    def scroll(self, x: int, y: int, clicks: int):
        """Execute mouse scroll"""
        try:
            pyautogui.scroll(clicks, x=x, y=y)
            return {"success": True, "message": f"Scroll successful: ({x}, {y}) scroll {clicks}"}
        except Exception as e:
            return {"success": False, "message": f"Scroll failed: {str(e)}"}

    def get_mouse_position(self):
        """Get current mouse position"""
        try:
            x, y = pyautogui.position()
            return {"success": True, "x": x, "y": y}
        except Exception as e:
            return {"success": False, "message": f"Failed to get mouse position: {str(e)}"}


# System Resource Monitor
class SystemMonitor:
    def __init__(self):
        self.last_check_time = None
        self.memory_usage = 0
        self.cpu_usage = 0
        self.disk_usage = 0

    def check_system_resources(self):
        """Check system resource usage"""
        try:
            # Get memory usage percentage
            memory = psutil.virtual_memory()
            self.memory_usage = round(memory.percent, 1)

            # Get CPU usage percentage
            self.cpu_usage = round(psutil.cpu_percent(interval=1), 1)

            # Get disk usage percentage
            disk = psutil.disk_usage("/")
            self.disk_usage = round((disk.used / disk.total) * 100, 1)

            self.last_check_time = time.time()

        except Exception as e:
            print(f"Failed to get system resource info: {e}")
            self.memory_usage = 0
            self.cpu_usage = 0
            self.disk_usage = 0
            self.last_check_time = time.time()

    def get_system_info(self):
        """Get system resource information"""
        # Check system resources every 5 seconds
        if self.last_check_time is None or time.time() - self.last_check_time > 5:
            self.check_system_resources()

        return {
            "memory_usage": self.memory_usage,
            "cpu_usage": self.cpu_usage,
            "disk_usage": self.disk_usage,
            "last_check": self.last_check_time,
        }


# WebSocket Connection Manager
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
            if websocket.client_state.value <= 2:  # Connection still active
                await websocket.send_text(message)
        except Exception as e:
            print(f"Failed to send personal message: {e}")
            # Remove from connection list if sending fails
            self.disconnect(websocket)

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                if connection.client_state.value <= 2:  # Connection still active
                    await connection.send_text(message)
                else:
                    disconnected.append(connection)
            except Exception as e:
                print(f"Failed to broadcast message: {e}")
                disconnected.append(connection)

        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()
network_monitor = NetworkMonitor()
system_monitor = SystemMonitor()
remote_controller = RemoteController()


# Windows Desktop Screenshot Generator
class DesktopScreenshotGenerator:
    def __init__(self):
        self.counter = 0
        self.last_screenshot = None
        self.last_screenshot_time = None
        self.monitors = []
        # Screenshot quality settings - optimized configuration
        self.quality_settings = {
            # Reduced default size
            "single_monitor": {"max_width": 1200, "max_height": 900},
            # Reduced default size
            "desktop": {"max_width": 1600, "max_height": 1000},
            "png_quality": 60,  # Reduced PNG quality to decrease file size
            "jpeg_quality": 60,  # Added JPEG quality setting
            "optimize": True,  # Enable PNG optimization
            # Whether to use JPEG format (smaller but slightly lower quality)
            "use_jpeg": True,
            # PNG compression level (0-9, 9 is highest)
            "compression_level": 6,
        }
        # Memory cache
        self.image_cache = {}
        self.cache_max_size = 3  # Maximum cache size
        self.cache_ttl = 1.5  # Cache time to live (seconds)
        self.update_monitor_info()

    def _should_resize_image(self, img, max_width, max_height):
        """Check if image needs to be resized"""
        return img.width > max_width or img.height > max_height

    def _resize_image_high_quality(self, img, max_width, max_height):
        """High quality image resizing"""
        # Don't resize if image is already smaller than target size
        if not self._should_resize_image(img, max_width, max_height):
            return img

        # Calculate scaling ratio
        ratio = min(max_width / img.width, max_height / img.height)
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)

        # Use LANCZOS resampling for high quality scaling
        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _get_cache_key(self, monitor_index, quality_settings):
        """Generate cache key"""
        return f"monitor_{monitor_index}_{hash(str(quality_settings))}"

    def _clean_cache(self):
        """Clean expired cache entries"""
        current_time = time.time()
        expired_keys = []

        for key, (image_data, timestamp) in self.image_cache.items():
            if current_time - timestamp > self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.image_cache[key]

    def _add_to_cache(self, key, image_data):
        """Add to cache"""
        # Clean expired cache
        self._clean_cache()

        # Remove oldest entry if cache is full
        if len(self.image_cache) >= self.cache_max_size:
            oldest_key = min(
                self.image_cache.keys(), key=lambda k: self.image_cache[k][1]
            )
            del self.image_cache[oldest_key]

        # Add new entry
        self.image_cache[key] = (image_data, time.time())

    def _get_from_cache(self, key):
        """Get data from cache"""
        if key in self.image_cache:
            image_data, timestamp = self.image_cache[key]
            if time.time() - timestamp <= self.cache_ttl:
                return image_data
            else:
                # Delete expired cache
                del self.image_cache[key]
        return None

    def _optimize_image_for_transmission(self, img, monitor_index):
        """Optimize image to reduce transmission size"""
        # Generate cache key
        cache_key = self._get_cache_key(monitor_index, self.quality_settings)

        # Check cache
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data

        # Get quality settings
        max_width = self.quality_settings["single_monitor"]["max_width"]
        max_height = self.quality_settings["single_monitor"]["max_height"]

        # Resize image
        img = self._resize_image_high_quality(img, max_width, max_height)

        # Convert to base64
        buffer = io.BytesIO()

        if self.quality_settings["use_jpeg"]:
            # Use JPEG format (smaller)
            img.save(
                buffer,
                format="JPEG",
                quality=self.quality_settings["jpeg_quality"],
                optimize=True,
            )
        else:
            # Use PNG format
            img.save(
                buffer,
                format="PNG",
                optimize=self.quality_settings["optimize"],
                quality=self.quality_settings["png_quality"],
                compress_level=self.quality_settings["compression_level"],
            )

        img_base64 = base64.b64encode(buffer.getvalue()).decode()

        # Add to cache
        self._add_to_cache(cache_key, img_base64)

        return img_base64

    def update_monitor_info(self):
        try:
            self.monitors = []

            # 获取虚拟桌面信息
            virtual_width = win32api.GetSystemMetrics(
                win32con.SM_CXVIRTUALSCREEN)
            virtual_height = win32api.GetSystemMetrics(
                win32con.SM_CYVIRTUALSCREEN)
            virtual_left = win32api.GetSystemMetrics(
                win32con.SM_XVIRTUALSCREEN)
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
                        #     f"Device {i}: {device.DeviceName} - Status: {device.StateFlags}"
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
                    print("No active display device found, using system metrics.")
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
                print(
                    f"Fail to use EnumDisplaySettings, use back up way instead: {e}")
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
            #         f"Monitor {i + 1}: {monitor['width']}x{monitor['height']} position({monitor['left']},{monitor['top']}) locate({monitor['left']},{monitor['top']},{monitor['right']},{monitor['bottom']}) {'(main monitor)' if monitor['primary'] else ''}"
            #     )

        except Exception as e:
            print(f"Fail to get monitor info: {e}")
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
                # default to primary monitor if index out of range
                width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
                height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
                left = 0
                top = 0
                right = width
                bottom = height

            # print(
            #     f"捕获显示器 {monitor_index + 1}: {width}x{height} 位置({left},{top}) 区域({left},{top},{right},{bottom})"
            # )

            # validate monitor dimensions and position
            if width <= 0 or height <= 0:
                print(
                    f"Error: Monitor {monitor_index + 1} has invalid dimensions: {width}x{height}")
                return self._create_error_image(f"Monitor {monitor_index + 1} has invalid dimensions")

            if left < 0 or top < 0:
                print(
                    f"Error: Monitor {monitor_index + 1} has invalid position: ({left},{top})")
                return self._create_error_image(f"Monitor {monitor_index + 1} has invalid position")

            # create device context
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()

            # create bitmap
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)

            # copy screen content to bitmap
            # Heads up: BitBlt source coordinates are relative to the virtual desktop, while target coordinates are relative to the bitmap
            result = memdc.BitBlt(
                (0, 0), (width, height), srcdc, (left, top), win32con.SRCCOPY
            )

            if result == 0:
                error_code = win32api.GetLastError()
                print(
                    f"warning: BitBlt operation failed, error code: {error_code}")
                print(f"try to use fallback screenshot method...")

                # Clear sources before fallback
                win32gui.DeleteObject(bmp.GetHandle())
                memdc.DeleteDC()
                srcdc.DeleteDC()
                win32gui.ReleaseDC(hwin, hwindc)

                # use PIL's ImageGrab as fallback method
                return self._capture_monitor_fallback(
                    monitor_index, left, top, width, height
                )

            # get bitmap info
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)

            # convert bitmap to PIL image
            img = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )

            # clear sources
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)

            # print(f"成功捕获显示器 {monitor_index + 1} 截图: {img.width}x{img.height}")

            return img

        except Exception as e:
            print(
                f"Fail to capture monitor {monitor_index + 1} screenshot: {e}")
            import traceback

            traceback.print_exc()
            return self._create_error_image(
                f"Fail to capture monitor {monitor_index + 1}: {str(e)}"
            )

    def _capture_monitor_fallback(self, monitor_index, left, top, width, height):
        """Backup screenshot method using PIL's ImageGrab"""
        try:
            from PIL import ImageGrab

            # print(
            #     f"使用备用方法捕获显示器 {monitor_index + 1}: 区域({left},{top},{left+width},{top+height})"
            # )

            # Use ImageGrab to capture the specified area
            bbox = (left, top, left + width, top + height)
            img = ImageGrab.grab(bbox=bbox)

            # print(
            #     f"备用方法成功捕获显示器 {monitor_index + 1} 截图: {img.width}x{img.height}"
            # )

            return img

        except Exception as e:
            print(f"Fallback screenshot method failed: {e}")
            return self._create_error_image(f"Fallback screenshot failed: {str(e)}")

    def capture_desktop_screenshot(self):
        try:
            # Get the handle of the desktop window
            hwin = win32gui.GetDesktopWindow()

            # Get the virtual desktop size (supports multiple monitors)
            virtual_width = win32api.GetSystemMetrics(
                win32con.SM_CXVIRTUALSCREEN)
            virtual_height = win32api.GetSystemMetrics(
                win32con.SM_CYVIRTUALSCREEN)
            virtual_left = win32api.GetSystemMetrics(
                win32con.SM_XVIRTUALSCREEN)
            virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

            # If virtual desktop size is 0, use primary monitor size
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

            # Create device context
            hwindc = win32gui.GetWindowDC(hwin)
            srcdc = win32ui.CreateDCFromHandle(hwindc)
            memdc = srcdc.CreateCompatibleDC()

            # Create a bitmap compatible with the source device context
            bmp = win32ui.CreateBitmap()
            bmp.CreateCompatibleBitmap(srcdc, width, height)
            memdc.SelectObject(bmp)

            # Copy screen content to bitmap (source coordinates are relative to the virtual desktop)
            memdc.BitBlt((0, 0), (width, height), srcdc,
                         (left, top), win32con.SRCCOPY)

            # Get bitmap info
            bmpinfo = bmp.GetInfo()
            bmpstr = bmp.GetBitmapBits(True)

            # Convert bitmap to PIL image
            img = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )

            # Clear the device context and bitmap
            win32gui.DeleteObject(bmp.GetHandle())
            memdc.DeleteDC()
            srcdc.DeleteDC()
            win32gui.ReleaseDC(hwin, hwindc)

            # Adjust image size to fit desktop resolution
            max_width = self.quality_settings["desktop"]["max_width"]
            max_height = self.quality_settings["desktop"]["max_height"]
            img = self._resize_image_high_quality(img, max_width, max_height)

            self.counter += 1
            self.last_screenshot = img
            self.last_screenshot_time = datetime.now()

            return img

        except ImportError:
            # If win32gui is not available, use fallback method
            return self._fallback_screenshot()
        except Exception as e:
            print(f"screenshot error: {e}")
            return self._fallback_screenshot()

    def _fallback_screenshot(self):
        """Backup screenshot method"""
        try:
            # Use PIL's ImageGrab (only available on Windows)
            from PIL import ImageGrab

            # Capture the entire virtual desktop
            # bbox=None means capture the entire virtual desktop
            screenshot = ImageGrab.grab(bbox=None)

            # Adjust image size to fit desktop resolution
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
            print(f"Backup screenshot error: {e}")
            return self._create_error_image()

    def _create_error_image(self, error_message: str = "Cannot capture screenshot"):
        """Create a blank image with error message"""
        img = Image.new("RGB", (800, 600), color="lightgray")
        draw = ImageDraw.Draw(img)

        # Add error message
        draw.text((400, 250), error_message, fill="red", anchor="mm")

        # Add timestamp
        timestamp = f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        draw.text((400, 300), timestamp, fill="black", anchor="mm")

        self.counter += 1
        return img


# Use the DesktopScreenshotGenerator
ui_generator = DesktopScreenshotGenerator()

# Initialize monitor information at startup
try:
    print("Initializing monitor information...")
    ui_generator.update_monitor_info()
    print(
        f"Monitor information initialized, detected {len(ui_generator.monitors)} monitors")
    for i, monitor in enumerate(ui_generator.monitors):
        print(
            f"Monitor {i}: {monitor['width']}x{monitor['height']} position({monitor['left']},{monitor['top']})")
except Exception as e:
    print(f"Failed to initialize monitor information: {e}")
    import traceback

    traceback.print_exc()

# Following monitors that have been collapsed (backend state)
collapsed_monitors = set()


@app.get("/ping")
async def ping():
    """ping"""
    return "success"


@app.get("/")
async def get_index():
    # Get back to index.html
    with open("index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/screenshot")
async def get_screenshot():
    """Get current desktop screenshot"""
    try:
        # get the latest screenshot
        img = ui_generator.capture_desktop_screenshot()

        # convert to base64 using high quality PNG
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
    """Get the screenshot of a specific monitor"""
    try:
        # Update monitor info
        ui_generator.update_monitor_info()

        # Validate monitor index
        if monitor_index >= len(ui_generator.monitors):
            return {
                "error": f"Monitor index {monitor_index} is out of scope, total monitor quantity: {len(ui_generator.monitors)}"
            }

        # Validate against collapsed monitors
        if monitor_index in collapsed_monitors:
            return {
                "error": f"Monitor {monitor_index} was collapsed, can't get screenshot for you",
                "monitor_index": monitor_index,
                "collapsed": True,
                "timestamp": datetime.now().isoformat(),
            }

        # Get screenshot of the specified monitor
        img = ui_generator.capture_single_monitor(monitor_index)

        # Use optimized image transmission function
        img_base64 = ui_generator._optimize_image_for_transmission(
            img, monitor_index)

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
    # Get screenshots of all monitors that are not collapsed
    try:
        screenshots = []

        # Update monitor info
        ui_generator.update_monitor_info()

        # Get total monitor count from system metrics
        total_monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)

        # Only process monitors that are not collapsed
        for i, monitor in enumerate(ui_generator.monitors):
            # Skip collapsed monitors
            if i in collapsed_monitors:
                continue

            # Only process active monitors: capture screenshot
            img = ui_generator.capture_single_monitor(i)

            # Use optimized image transmission function
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
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Validate if connection is still active
            if websocket.client_state.value > 2:  # Connection is closed
                break

            # Get real-time info
            network_info = network_monitor.get_network_info()
            system_info = system_monitor.get_system_info()

            # Send real-time data
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
                # If sending fails, the connection might be broken
                print(f"Failed to send WebSocket: {e}")
                break

            # 0.8 second interval, consistent with frontend
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        print("WebSocket connection is closed")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


@app.get("/status")
async def get_status():
    network_info = network_monitor.get_network_info()
    system_info = system_monitor.get_system_info()
    return {
        "counter": ui_generator.counter,
        "timestamp": datetime.now().isoformat(),
        "connections": len(manager.active_connections),
        "network": network_info,
        "memory_usage": system_info["memory_usage"],
        "cpu_usage": system_info["cpu_usage"],
        "disk_usage": system_info["disk_usage"],
    }


@app.get("/test-network")
async def test_network():
    network_monitor.check_network_status()
    network_info = network_monitor.get_network_info()
    return {
        "message": "Success to test network status",
        "network": network_info,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/system-info")
async def get_system_info():
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
    """Get detailed monitor configuration"""
    try:
        ui_generator.update_monitor_info()

        # Get system metrics
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)

        # Get detailed monitor info
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
                "EnumDisplayMonitors" if len(
                    monitors_info) > 1 else "Single Monitor"
            ),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/debug/monitor/{monitor_index}")
async def debug_monitor_screenshot(monitor_index: int):
    """Debug single monitor screenshot with detailed info"""
    try:
        ui_generator.update_monitor_info()

        # Validate monitor index
        if monitor_index >= len(ui_generator.monitors):
            return {
                "error": f"Monitor index {monitor_index} is out of scope, total monitor quantity {len(ui_generator.monitors)}"
            }

        monitor = ui_generator.monitors[monitor_index]

        # Get system metrics
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        img = ui_generator.capture_single_monitor(monitor_index)

        # Convert to base64
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
    """Update quality settings"""
    try:
        if "single_monitor" in settings:
            ui_generator.quality_settings["single_monitor"].update(
                settings["single_monitor"]
            )
        if "desktop" in settings:
            ui_generator.quality_settings["desktop"].update(
                settings["desktop"])
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

        # Clear cache to apply new settings
        ui_generator.image_cache.clear()

        return {
            "message": "Success to update image quality",
            "current_settings": ui_generator.quality_settings,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/quality-settings")
async def get_quality_settings():
    """Get current quality settings"""
    return {
        "settings": ui_generator.quality_settings,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/cache-stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        cache_size = len(ui_generator.image_cache)
        cache_keys = list(ui_generator.image_cache.keys())

        # Calculate cache hit rate (simplified)
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
    try:
        cache_size = len(ui_generator.image_cache)
        ui_generator.image_cache.clear()

        return {
            "message": f"Cache is cleared, {cache_size} cache items were removed",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.post("/collapsed-monitors")
async def update_collapsed_monitors(collapsed_data: dict):
    # Update the set of collapsed monitors based on provided indices
    global collapsed_monitors
    try:
        collapsed_indices = collapsed_data.get("collapsed_monitors", [])
        collapsed_monitors = set(collapsed_indices)

        return {
            "message": "Successfully updated collapsed monitors state",
            "collapsed_monitors": list(collapsed_monitors),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/collapsed-monitors")
async def get_collapsed_monitors():
    """Get the current set of collapsed monitors"""
    return {
        "collapsed_monitors": list(collapsed_monitors),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/force-redetect")
async def force_redetect_monitors():
    """Force re-detect monitor configuration"""
    try:
        # Force re-detect monitors
        ui_generator.update_monitor_info()

        # Get system metrics
        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        monitor_count = win32api.GetSystemMetrics(win32con.SM_CMONITORS)

        # Get detailed monitor info
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
            "message": "Successfully re-detected monitors",
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
    try:
        ui_generator.update_monitor_info()

        virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)

        primary_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
        primary_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

        # Get current screenshot info
        if ui_generator.last_screenshot:
            current_width = ui_generator.last_screenshot.width
            current_height = ui_generator.last_screenshot.height
        else:
            current_width = 0
            current_height = 0

        # Get detailed monitor info
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


# File upload related features
# Use the system Downloads folder as the default upload directory
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
UPLOAD_FILE_SIZE_LIMIT = 200

# Ensure the default Downloads directory exists (usually already exists)
if not os.path.exists(DEFAULT_UPLOAD_DIR):
    os.makedirs(DEFAULT_UPLOAD_DIR, exist_ok=True)


def get_upload_dir(folder_path=None):
    if folder_path:
        # Validate if it's an absolute path
        if (
            os.path.isabs(folder_path)
            or folder_path.startswith("/")
            or ":" in folder_path
        ):
            upload_dir = folder_path
        else:
            # Downloads subdirectory, create subfolder under Downloads
            upload_dir = os.path.join(DEFAULT_UPLOAD_DIR, folder_path)

        # Ensure the directory exists
        os.makedirs(upload_dir, exist_ok=True)
        # Return absolute path to ensure consistent path separators
        abs_upload_dir = os.path.abspath(upload_dir)
        return abs_upload_dir
    else:
        return DEFAULT_UPLOAD_DIR


def is_allowed_file(filename: str) -> bool:
    # Validate file extension
    if not filename:
        return False
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in ALLOWED_EXTENSIONS


@app.post("/upload")
async def upload_file(file: UploadFile = File(...), folder_path: str = Form(None)):
    # Upload a single file
    try:
        # Validate file size (limit to UPLOAD_FILE_SIZE_LIMIT MB)
        if file.size and file.size > UPLOAD_FILE_SIZE_LIMIT * 1024 * 1024:
            raise HTTPException(
                status_code=400, detail=f"The file size is over {UPLOAD_FILE_SIZE_LIMIT}MB limit"
            )

        upload_dir = get_upload_dir(folder_path)

        # Generate a safe filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = os.path.join(upload_dir, safe_filename)

        # Save file
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Get file size in MB
        file_size = len(content)
        file_size_mb = round(file_size / (1024 * 1024), 2)
        response_data = {
            "message": "The file is saved successfully",
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
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.post("/upload/multiple")
async def upload_multiple_files(
    files: List[UploadFile] = File(...), folder_path: str = Form(None)
):
    try:
        if not files:
            raise HTTPException(status_code=400, detail="There is no file selected")

        if len(files) > 10:
            raise HTTPException(status_code=400, detail="It's limited to upload up to 10 files at a time")

        upload_dir = get_upload_dir(folder_path)

        uploaded_files = []
        total_size = 0
        for file in files:
            if file.size and file.size > UPLOAD_FILE_SIZE_LIMIT * 1024 * 1024:
                continue

            # Create a safe filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{file.filename}"
            file_path = os.path.join(upload_dir, safe_filename)

            # Save file
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
            "message": f"Success to upload {len(uploaded_files)} files",
            "files": uploaded_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "upload_time": datetime.now().isoformat(),
            "upload_dir": upload_dir,
        }
        return JSONResponse(response_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")


@app.get("/files")
async def list_uploaded_files(folder: str = None):
    """获取已上传文件列表"""
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
                    ]
                    for forbidden in forbidden_paths:
                        if full_path.startswith(forbidden):
                            raise HTTPException(
                                status_code=403, detail="Cannot create folders in system directories"
                            )
            else:
                # Downloads路径
                full_path = os.path.join(
                    DEFAULT_UPLOAD_DIR, parent_path, folder_name)
                # 确保路径在Downloads目录内
                if not os.path.abspath(full_path).startswith(
                    os.path.abspath(DEFAULT_UPLOAD_DIR)
                ):
                    raise HTTPException(
                        status_code=403, detail="Access denied")
        else:
            # Create in the root of Downloads
            full_path = os.path.join(DEFAULT_UPLOAD_DIR, folder_name)

        # Check if the folder already exists
        if os.path.exists(full_path):
            raise HTTPException(
                status_code=409, detail="Folder already exists")

        # Create the folder
        try:
            os.makedirs(full_path, exist_ok=False)
        except PermissionError:
            raise HTTPException(
                status_code=403, detail="No permission to create folder")
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to create folder: {str(e)}")

        return JSONResponse(
            {
                "success": True,
                "message": f"Folder '{folder_name}' created successfully",
                "folder_path": full_path,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create folder: {str(e)}")


@app.get("/directories")
async def list_available_directories(path: str = ""):
    """Get the list of directories under the specified path"""
    start_time = time.time()
    timeout_seconds = 10

    try:
        # URL decode path parameter
        import urllib.parse

        if path:
            path = urllib.parse.unquote(path)

        # Build full path
        if path:
            full_path = os.path.join(DEFAULT_UPLOAD_DIR, path)
            # Ensure the path is within the Downloads directory
            if not os.path.abspath(full_path).startswith(
                os.path.abspath(DEFAULT_UPLOAD_DIR)
            ):
                raise HTTPException(status_code=403, detail="Access denied")
        else:
            full_path = DEFAULT_UPLOAD_DIR

        # Ensure the path exists
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="Path does not exist")

        if not os.path.isdir(full_path):
            raise HTTPException(
                status_code=400, detail="Specified path is not a directory")

        # Get relative path and parent path
        relative_path = path
        parent_path = os.path.dirname(relative_path) if relative_path else ""

        # Get directory list
        try:
            items = []
            timeout_occurred = False

            for item in os.listdir(full_path):
                item_path = os.path.join(full_path, item)

                # Check for timeout
                if time.time() - start_time > timeout_seconds:
                    raise HTTPException(
                        status_code=408, detail="Request timeout")

                if os.path.isdir(item_path):
                    # Count folders, with timeout handling
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
                        # If an error occurs while counting folders (timeout or other), return special value
                        folder_count = -1  # Use -1 to indicate timeout or error

                    # Build relative path
                    if relative_path:
                        item_relative_path = os.path.join(relative_path, item)
                    else:
                        item_relative_path = item

                    # Ensure path uses forward slashes (as expected by frontend)
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
            raise HTTPException(
                status_code=403, detail="No permission to access this directory")

        # Sort by name
        items.sort(key=lambda x: x["name"].lower())

        response_data = {
            "items": items,
            "current_path": relative_path,
            "parent_path": parent_path,
            "base_path": DEFAULT_UPLOAD_DIR,
            "total_count": len(items),
            "can_go_up": relative_path != "",
        }

        # If timeout occurred, add timeout info
        if timeout_occurred:
            response_data["partial_results"] = True
            response_data["timeout_message"] = (
                "Some directories could not be loaded due to timeout, only accessible directories are shown"
            )

        return JSONResponse(response_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get directory list: {str(e)}")


@app.get("/system-directories")
async def list_system_directories(path: str = ""):
    """浏览系统根目录下的文件系统"""
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
            result = remote_controller.click(
                actual_x, actual_y, button, clicks)
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
            screenshot_height = monitor.get(
                "screenshot_height", monitor_height)

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
    # for local use
    uvicorn.run(app, host="0.0.0.0", port=8000)

    # # for https use
    # uvicorn.run(
    #     app,
    #     host="0.0.0.0",
    #     port=8443,
    #     ssl_keyfile="cert/key.pem",
    #     ssl_certfile="cert/cert.pem",
    # )
