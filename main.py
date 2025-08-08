import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
import threading
from PIL import Image
import pystray
import requests
import psutil

class SecondSightManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("千里眼")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # 计算居中位置
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 400
        window_height = 500
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口位置
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # 获取程序运行路径
        self.base_path = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        self.server_process = None
        self.is_running = False
        
        self.setup_ui()
        self.setup_tray()
        self.check_server_status()

    def setup_ui(self):
        # 标题
        title_label = ttk.Label(self.root, text="服务管理器", font=("Arial", 16, "bold"))
        title_label.pack(pady=10)
        
        # 状态面板（使用 Frame 包装）
        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=10, padx=20, fill=tk.X)
        
        # 状态指示器（圆点）
        self.status_indicator = ttk.Label(
            status_frame, 
            text="●", 
            font=("Arial", 16),
            foreground="gray"
        )
        self.status_indicator.pack(side=tk.LEFT, padx=(0,10))
        
        # 状态文本
        self.status_label = ttk.Label(
            status_frame, 
            text="状态: 检测中...",
            font=("Arial", 12)
        )
        self.status_label.pack(side=tk.LEFT)
        
        # 自动刷新状态的定时器
        self.root.after(5000, self.auto_check_status)
        
        # 按钮样式
        style = ttk.Style()
        style.configure("Action.TButton", padding=10)
        
        # 控制按钮
        buttons = [
            ("启动服务器", self.start_server),
            ("停止服务器", self.stop_server),
            ("重启服务器", self.restart_server),
            ("检测状态", self.check_server_status),
            ("最小化到托盘", self.minimize_to_tray),
            ("退出程序", self.confirm_quit)
        ]
        
        for text, command in buttons:
            btn = ttk.Button(
                self.root,
                text=text,
                command=command,
                style="Action.TButton"
            )
            btn.pack(pady=8, padx=20, fill=tk.X)
        
        # 版本信息
        version_label = ttk.Label(self.root, text="v1.0.0", font=("Arial", 8))
        version_label.pack(side=tk.BOTTOM, pady=5)

    def setup_tray(self):
        # 创建托盘图标
        icon_path = os.path.join(self.base_path, "assets", "icon.ico")
        if os.path.exists(icon_path):
            icon_image = Image.open(icon_path)
        else:
            icon_image = Image.new('RGB', (64, 64), 'black')
            
        self.icon = pystray.Icon(
            "Second Sight",
            icon_image,
            "Second Sight",
            menu=pystray.Menu(
                pystray.MenuItem("显示", self.show_window),
                pystray.MenuItem("退出", self.quit_app)
            )
        )
        threading.Thread(target=self.icon.run, daemon=True).start()

    def start_server(self):
        if not self.is_running:
            try:
                server_path = os.path.join(self.base_path, "server.py")
                python_exe = os.path.join(self.base_path, "python", "python.exe")
                
                if not os.path.exists(python_exe):
                    python_exe = sys.executable
                    
                self.server_process = subprocess.Popen(
                    [python_exe, server_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    cwd=self.base_path
                )
                self.is_running = True
                # 更新状态显示
                self.update_status_display(True)
                messagebox.showinfo("成功", "服务器已启动")
            except Exception as e:
                # 更新状态显示为错误状态
                self.is_running = False
                self.update_status_display(False)
                messagebox.showerror("错误", f"启动失败: {str(e)}")

    def kill_server_by_port(self, port=8000):
        """通过端口号找到并终止进程"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    connections = proc.connections()
                    for conn in connections:
                        if conn.laddr.port == port:
                            # 找到目标进程
                            parent = psutil.Process(proc.pid)
                            # 终止所有子进程
                            for child in parent.children(recursive=True):
                                try:
                                    child.kill()  # 使用 kill 而不是 terminate
                                except:
                                    pass
                            # 强制终止主进程
                            parent.kill()
                            return True
                except:
                    continue
        except:
            pass
        return False

    def stop_server(self):
        """增强的停止服务器功能"""
        try:
            stopped = False
            # 1. 尝试通过 self.server_process 停止
            if self.server_process and self.is_running:
                try:
                    parent = psutil.Process(self.server_process.pid)
                    for child in parent.children(recursive=True):
                        try:
                            child.kill()
                        except:
                            pass
                    parent.kill()
                    stopped = True
                except:
                    pass

            # 2. 如果上述方法失败，通过端口号查找并终止进程
            if not stopped:
                self.kill_server_by_port(8000)

            # 3. 重置状态
            self.server_process = None
            self.is_running = False
            # 更新状态显示
            self.update_status_display(False)
            messagebox.showinfo("成功", "服务器已停止")
        except Exception as e:
            self.is_running = False
            self.server_process = None
            # 更新状态显示为错误状态
            self.update_status_display(False)
            messagebox.showerror("警告", f"停止服务器时出现问题: {str(e)}")

    def restart_server(self):
        self.stop_server()
        self.start_server()

    def update_status_display(self, is_running):
        """更新状态显示"""
        if is_running:
            self.status_indicator.config(foreground="green")
            self.status_label.config(text="状态: 运行中")
        else:
            self.status_indicator.config(foreground="red")
            self.status_label.config(text="状态: 已停止")

    def check_server_status(self):
        """检查服务器状态"""
        try:
            response = requests.get("http://localhost:8000/status", timeout=2)
            is_running = response.status_code == 200
            # 显示状态检测结果
            if is_running:
                messagebox.showinfo("状态检测", "服务器正在运行")
            else:
                messagebox.showwarning("状态检测", "服务器未运行")
        except:
            is_running = False
            messagebox.showwarning("状态检测", "服务器未运行")
    
        self.is_running = is_running
        self.update_status_display(is_running)
        return is_running

    def auto_check_status(self):
        """自动定期检查状态 - 不弹窗"""
        try:
            response = requests.get("http://localhost:8000/status", timeout=2)
            is_running = response.status_code == 200
        except:
            is_running = False
    
        self.is_running = is_running
        self.update_status_display(is_running)
        # 每5秒检查一次
        self.root.after(5000, self.auto_check_status)

    def minimize_to_tray(self):
        self.root.withdraw()

    def show_window(self):
        self.root.deiconify()

    def confirm_quit(self):
        """确认退出程序"""
        if messagebox.askokcancel("确认", "确定要退出程序吗？"):
            self.quit_app()

    def quit_app(self):
        """改进的退出功能"""
        try:
            # 1. 先尝试正常停止服务器
            if self.is_running:
                self.stop_server()
            
            # 2. 强制清理端口占用
            self.kill_server_by_port(8000)
            
            # 3. 停止托盘图标
            try:
                self.icon.stop()
            except:
                pass
            
            # 4. 退出程序
            self.root.quit()
        except Exception as e:
            # 确保程序能退出
            try:
                self.root.destroy()
            except:
                pass
            sys.exit(0)

    def run(self):
        # 修改窗口关闭按钮的行为，从最小化改为确认退出
        self.root.protocol("WM_DELETE_WINDOW", self.confirm_quit)
        self.root.mainloop()

if __name__ == "__main__":
    app = SecondSightManager()
    app.run()