import sys
import os
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as font
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import threading
import subprocess
import time
import atexit
import signal
from typing import Optional, Callable, Any, Dict, Tuple
import socket


# 确保打包后能正确找到路径
def get_resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径，兼容开发环境和打包后环境"""
    try:
        base_path = sys._MEIPASS  # PyInstaller临时路径
    except Exception:
        base_path = os.path.abspath(".")  # 开发环境路径
    return os.path.join(base_path, relative_path)


class SecondSightManager(tk.Tk):
    """千里眼远程桌面服务管理器主类"""
    # 配置常量
    WINDOW_WIDTH: int = 400
    WINDOW_HEIGHT: int = 560
    SERVER_PORT: int = 8000  # 服务器默认端口
    START_DELAY: int = 3000  # 服务器启动检查延迟(ms)
    STOP_DELAY: int = 1500  # 服务器停止后重启延迟(ms)
    CHECK_TIMEOUT: int = 5  # 服务器状态检查超时(s)
    
    # 前端文件路径配置
    STATIC_FOLDER: str = "static"  # 静态文件根目录
    JS_FOLDER: str = os.path.join("static", "js")  # JS文件目录
    CSS_FOLDER: str = os.path.join("static", "styles.css")  # CSS文件路径
    INDEX_HTML: str = "index.html"  # 主页HTML文件
    
    # 样式配置
    FONT_CONFIG: Dict[str, Dict[str, Any]] = {
        "default": {"family": "微软雅黑", "size": 10},
        "title": {"family": "微软雅黑", "size": 16, "weight": "bold"},
        "status": {"family": "微软雅黑", "size": 11},
        "version": {"family": "微软雅黑", "size": 9}
    }
    
    BUTTON_STYLES: Dict[str, Dict[str, Any]] = {
        "Start": {"bg": "#4CAF50", "active_bg": "#45a049", "pressed_bg": "#3d8b40", "text": "启动服务器"},
        "Stop": {"bg": "#f44336", "active_bg": "#d32f2f", "pressed_bg": "#b71c1c", "text": "停止服务器"},
        "Restart": {"bg": "#2196F3", "active_bg": "#0b7dda", "pressed_bg": "#0d47a1", "text": "重启服务器"},
        "Check": {"bg": "#FFC107", "active_bg": "#ffb300", "pressed_bg": "#ff8f00", "text": "检测状态"},
        "OpenWeb": {"bg": "#009688", "active_bg": "#00897B", "pressed_bg": "#00796B", "text": "打开网页"},
        "Tray": {"bg": "#9C27B0", "active_bg": "#7b1fa2", "pressed_bg": "#4a148c", "text": "最小化到托盘"},
        "Exit": {"bg": "#607D8B", "active_bg": "#546E7A", "pressed_bg": "#37474F", "text": "退出程序"}
    }

    def __init__(self):
        super().__init__()
        self.tray_icon: Optional[Icon] = None  # 托盘图标实例
        self.server_process: Optional[subprocess.Popen] = None  # 服务器进程
        self.server_thread: Optional[threading.Thread] = None  # 服务器线程
        self.is_server_running: bool = False  # 服务器运行状态
        self._lock: threading.Lock = threading.Lock()  # 线程安全锁
        self._output_threads = []  # 存储输出处理线程，用于停止时清理
        
        # 先隐藏窗口，避免居中过程可见
        self.withdraw()
        # 计算居中位置并设置
        self.calculate_center_position()
        # 初始化UI
        self.init_ui()
        # 显示窗口
        self.deiconify()
        # 创建托盘图标
        self.create_tray_icon()
        
        # 注册程序退出时的清理函数
        atexit.register(self.cleanup)
        
    def calculate_center_position(self) -> None:
        """计算并设置窗口居中位置"""
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - self.WINDOW_WIDTH) // 2
        y = (screen_height - self.WINDOW_HEIGHT) // 2
        self.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")
        self.resizable(False, False)
        
    def init_ui(self) -> None:
        """初始化UI界面"""
        self.title("千里眼-远程桌面 服务管理器")
        self._init_fonts()
        self._configure_styles()
        
        main_frame = ttk.Frame(self, padding="20 20 20 20", relief="solid", borderwidth=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self._create_title_area(main_frame)
        self._create_status_area(main_frame)
        self._create_button_area(main_frame)
        self._create_version_area(main_frame)
        self._update_button_states()
    
    def _init_fonts(self) -> None:
        """初始化字体对象"""
        self.default_font = font.Font(** self.FONT_CONFIG["default"])
        self.title_font = font.Font(**self.FONT_CONFIG["title"])
        self.status_font = font.Font(** self.FONT_CONFIG["status"])
        self.version_font = font.Font(**self.FONT_CONFIG["version"])
    
    def _configure_styles(self) -> None:
        """配置ttk样式"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("Status.TFrame", background="#f0f0f0")
        
        for style_name, config in self.BUTTON_STYLES.items():
            self.style.configure(
                f"{style_name}.TButton",
                font=self.default_font,
                padding=10,
                background=config["bg"],
                foreground="black"
            )
            self.style.map(
                f"{style_name}.TButton",
                background=[("active", config["active_bg"]), ("pressed", config["pressed_bg"])]
            )
    
    def _create_title_area(self, parent: ttk.Frame) -> None:
        """创建标题区域"""
        title_label = ttk.Label(parent, text="服务管理器", font=self.title_font)
        title_label.pack(pady=(0, 25))
    
    def _create_status_area(self, parent: ttk.Frame) -> None:
        """创建状态显示区域"""
        status_frame = ttk.Frame(parent, padding=10, relief="flat", borderwidth=1)
        status_frame.pack(fill=tk.X, pady=(0, 25))
        status_frame.configure(style="Status.TFrame")
        
        self.status_var = tk.StringVar(value="状态: 未运行")
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var, 
            font=self.status_font, 
            foreground="#2E7D32"
        )
        status_label.pack()
        
        self.server_url_var = tk.StringVar(value=f"服务器地址: http://localhost:{self.SERVER_PORT}")
        url_label = ttk.Label(
            status_frame, 
            textvariable=self.server_url_var, 
            font=self.default_font, 
            foreground="#607D8B"
        )
        url_label.pack(pady=(5, 0))
    
    def _create_button_area(self, parent: ttk.Frame) -> None:
        """创建按钮区域"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, expand=False)
        
        button_commands = {
            "Start": self.start_server,
            "Stop": self.stop_server,
            "Restart": self.restart_server,
            "Check": self.check_status,
            "OpenWeb": self.open_web_page,
            "Tray": self.min_to_tray,
            "Exit": self.exit_program
        }
        
        for style_name, config in self.BUTTON_STYLES.items():
            ttk.Button(
                button_frame, 
                text=config["text"], 
                command=button_commands[style_name],
                style=f"{style_name}.TButton"
            ).pack(fill=tk.X, pady=5)
    
    def _create_version_area(self, parent: ttk.Frame) -> None:
        """创建版本信息区域"""
        version_label = ttk.Label(parent, text="v1.0.0", font=self.version_font)
        version_label.pack(side=tk.BOTTOM, pady=10)
    
    def _update_button_states(self) -> None:
        """根据服务器状态更新按钮可用状态"""
        for child in self.winfo_children():
            if isinstance(child, ttk.Frame):
                for btn in child.winfo_children():
                    if isinstance(btn, ttk.Frame):
                        for b in btn.winfo_children():
                            if isinstance(b, ttk.Button):
                                self._update_single_button(b)
    
    def _update_single_button(self, button: ttk.Button) -> None:
        """更新单个按钮的状态"""
        style = button.cget("style")
        if "Start.TButton" in style:
            button.config(state=tk.DISABLED if self.is_server_running else tk.NORMAL)
        elif "Stop.TButton" in style or "Restart.TButton" in style or "OpenWeb.TButton" in style:
            button.config(state=tk.NORMAL if self.is_server_running else tk.DISABLED)

    # 启动FastAPI服务器
    def start_server(self) -> None:
        """启动服务器进程（线程安全）"""
        with self._lock:
            if self.is_server_running:
                messagebox.showinfo("提示", "服务器已在运行中")
                return
                
        self.status_var.set("状态: 启动中...")
        self.update_idletasks()
        
        if not self._check_frontend_files():
            return
        
        self._output_threads = []  # 清空之前的输出线程
        self.server_thread = threading.Thread(target=self._run_server, daemon=True)
        self.server_thread.start()
        self.after(self.START_DELAY, self._check_server_started)
    
    def _check_frontend_files(self) -> bool:
        """检查前端文件是否存在"""
        index_path = get_resource_path(self.INDEX_HTML)
        if not os.path.exists(index_path):
            messagebox.showerror("错误", f"未找到主页文件: {index_path}")
            return False
            
        static_path = get_resource_path(self.STATIC_FOLDER)
        if not os.path.exists(static_path):
            messagebox.showerror("错误", f"未找到静态文件目录: {static_path}")
            return False
            
        js_path = get_resource_path(self.JS_FOLDER)
        if not os.path.exists(js_path):
            messagebox.showerror("错误", f"未找到JS文件目录: {js_path}")
            return False
            
        css_path = get_resource_path(self.CSS_FOLDER)
        if not os.path.exists(css_path):
            messagebox.showerror("错误", f"未找到CSS文件: {css_path}")
            return False
            
        return True
    
    def _run_server(self) -> None:
        """实际运行服务器的函数（在子线程中执行）"""
        try:
            server_path = get_resource_path("server.py")
            if not os.path.exists(server_path):
                self.status_var.set("状态: 启动失败")
                messagebox.showerror("错误", f"未找到server.py文件，路径: {server_path}")
                with self._lock:
                    self.is_server_running = False
                return
            
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            static_abs_path = get_resource_path(self.STATIC_FOLDER)
            env["STATIC_DIR"] = static_abs_path
            env["INDEX_HTML_PATH"] = get_resource_path(self.INDEX_HTML)
            
            self.server_process = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "server:app", 
                 "--host", "0.0.0.0", f"--port", f"{self.SERVER_PORT}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(server_path),
                env=env
            )
            
            # 存储输出线程以便后续清理
            stdout_thread = threading.Thread(
                target=self._read_server_output,
                args=(self.server_process.stdout,),
                daemon=True
            )
            stderr_thread = threading.Thread(
                target=self._read_server_output,
                args=(self.server_process.stderr,),
                daemon=True
            )
            self._output_threads = [stdout_thread, stderr_thread]
            stdout_thread.start()
            stderr_thread.start()
            
            with self._lock:
                self.is_server_running = True
            print(f"服务器已启动，PID: {self.server_process.pid}")
            self.status_var.set("状态: 运行中")
            self._update_button_states()
                
        except Exception as e:
            with self._lock:
                self.is_server_running = False
            self.status_var.set("状态: 启动失败")
            messagebox.showerror("错误", f"启动服务器时发生错误: {str(e)}")
            print(f"服务器启动错误: {str(e)}")
    
    def _read_server_output(self, stream: Any) -> None:
        """读取服务器输出（非阻塞方式）"""
        try:
            while True:
                if stream.closed:
                    break
                line = stream.readline()
                if not line:
                    break
                print(f"服务器输出: {line.strip()}")
        except Exception as e:
            # 忽略流关闭导致的错误
            if "I/O operation on closed file" not in str(e):
                print(f"读取服务器输出错误: {str(e)}")
    
    def _check_server_started(self) -> None:
        """检查服务器是否成功启动"""
        with self._lock:
            running = self.is_server_running
        
        if not running:
            return
            
        success = self._test_server_connection()
        if success:
            self.status_var.set("状态: 运行中")
            print("服务器启动成功并可访问")
        else:
            with self._lock:
                self.is_server_running = False
            self.status_var.set("状态: 启动失败（服务不可访问）")
            messagebox.showerror("启动失败", "服务器进程已启动，但无法访问服务端口")
    
    def _test_server_connection(self) -> bool:
        """测试服务器端口是否可连接"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(2)
                result = s.connect_ex(("localhost", self.SERVER_PORT))
                return result == 0
        except Exception as e:
            print(f"测试服务器连接失败: {str(e)}")
            return False
    
    # 停止服务器（核心修复部分）
    def stop_server(self) -> None:
        """停止服务器进程（线程安全，修复资源释放问题）"""
        with self._lock:
            if not self.is_server_running:
                messagebox.showinfo("提示", "服务器未在运行")
                return
                
        self.status_var.set("状态: 停止中...")
        self.update_idletasks()
        
        if self.server_process:
            try:
                # 关键修复1：先关闭输出流，避免日志写入错误
                if self.server_process.stdout:
                    self.server_process.stdout.close()
                if self.server_process.stderr:
                    self.server_process.stderr.close()
                
                # 关键修复2：Windows使用terminate()替代CTRL_C_EVENT，避免影响主程序
                if os.name == "nt":
                    self.server_process.terminate()  # 强制终止，更安全
                else:
                    self.server_process.send_signal(signal.SIGINT)
                
                # 等待进程结束
                self._wait_for_server_stop()
                
            except Exception as e:
                messagebox.showerror("错误", f"停止服务器时发生错误: {str(e)}")
                print(f"停止服务器错误: {str(e)}")
        
        # 清理线程和状态
        self._cleanup_server_resources()
    
    def _wait_for_server_stop(self) -> None:
        """等待服务器停止（非阻塞方式）"""
        if not self.server_process:
            return
            
        if self.server_process.poll() is not None:
            return  # 进程已停止
            
        # 继续等待，100ms后再次检查
        self.after(100, self._wait_for_server_stop)
    
    def _cleanup_server_resources(self) -> None:
        """清理服务器相关资源（输出线程、进程对象）"""
        # 标记状态为停止
        with self._lock:
            self.is_server_running = False
        
        # 等待输出线程结束
        for thread in self._output_threads:
            if thread.is_alive():
                thread.join(timeout=0.5)
        
        # 释放进程对象
        self.server_process = None
        self._output_threads = []
        self.status_var.set("状态: 已停止")
        self._update_button_states()
    
    # 重启服务器
    def restart_server(self) -> None:
        """重启服务器"""
        self.stop_server()
        self.after(self.STOP_DELAY, self.start_server)
    
    # 检测服务器状态
    def check_status(self) -> None:
        """检查并更新服务器状态"""
        with self._lock:
            running = self.is_server_running
            process = self.server_process
        
        if running and process and process.poll() is None and self._test_server_connection():
            status = "运行中"
        else:
            status = "已停止"
            with self._lock:
                self.is_server_running = False
                
        self.status_var.set(f"状态: {status}")
        messagebox.showinfo("状态检测", f"当前服务器状态: {status}")
        self._update_button_states()
    
    # 打开网页
    def open_web_page(self) -> None:
        """在默认浏览器中打开网页"""
        if not self.is_server_running:
            messagebox.showinfo("提示", "请先启动服务器")
            return
            
        import webbrowser
        url = f"http://localhost:{self.SERVER_PORT}"
        try:
            webbrowser.open(url)
            print(f"已在浏览器中打开: {url}")
        except Exception as e:
            messagebox.showerror("错误", f"无法打开浏览器: {str(e)}")
    
    # 显示窗口
    def show_window(self) -> None:
        """从托盘恢复窗口显示"""
        self.deiconify()
        self.lift()
        self.calculate_center_position()
    
    # 最小化到托盘
    def min_to_tray(self) -> None:
        """最小化窗口到系统托盘"""
        self.withdraw()
        messagebox.showinfo("提示", "程序已最小化到系统托盘")
    
    # 创建托盘图标
    def create_tray_icon(self) -> None:
        """创建系统托盘图标"""
        try:
            icon_path = get_resource_path("icon.png")
            if os.path.exists(icon_path):
                image = Image.open(icon_path)
            else:
                image = self._create_default_tray_icon()
        except Exception:
            image = self._create_default_tray_icon()
        
        menu = Menu(
            MenuItem("显示窗口", self.show_window),
            MenuItem("打开网页", self.open_web_page),
            MenuItem("退出", self.exit_program)
        )
        
        self.tray_icon = Icon("千里眼服务", image, "千里眼-远程桌面服务", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def _create_default_tray_icon(self) -> Image.Image:
        """创建默认的托盘图标"""
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        draw.text((10, 20), "千里眼", fill=(255, 255, 255))
        return image
    
    # 退出程序
    def exit_program(self) -> None:
        """退出整个程序"""
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            self.cleanup()
            self.destroy()
            sys.exit(0)
    
    # 程序清理函数
    def cleanup(self) -> None:
        """程序退出时的清理工作"""
        self._cleanup_server_resources()  # 统一清理资源
        if self.tray_icon:
            self.tray_icon.stop()
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(timeout=1.0)


if __name__ == "__main__":
    os.environ["PYTHONUTF8"] = "1"
    os.environ["PYTHONIOENCODING"] = "utf-8"
    app = SecondSightManager()
    try:
        # 关键修复3：捕获KeyboardInterrupt，避免程序意外退出
        app.mainloop()
    except KeyboardInterrupt:
        app.cleanup()
        sys.exit(0)