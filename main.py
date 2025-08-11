import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import time
import psutil
import os
import sys
import webbrowser
from pathlib import Path
import pystray
from PIL import Image, ImageTk
import requests
import socket
import traceback

class ServiceManager:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("千里眼-远程桌面")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        
        # 设置窗口图标
        try:
            if os.path.exists("icon.ico"):
                self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # 服务状态
        self.server_process = None
        self.server_running = False
        self.server_port = 8000
        
        # 创建托盘图标
        self.setup_tray()
        
        # 创建界面
        self.create_widgets()
        
        # 启动状态检测线程
        self.status_thread = threading.Thread(target=self.status_monitor, daemon=True)
        self.status_thread.start()
        
        # 绑定窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.exit_program)
        
    def create_widgets(self):
        """创建界面组件"""
        # 主标题
        title_label = tk.Label(
            self.root, 
            text="服务管理器", 
            font=("Microsoft YaHei", 20, "bold"),
            fg="#333333"
        )
        title_label.pack(pady=20)
        
        # 状态显示区域
        status_frame = tk.Frame(self.root)
        status_frame.pack(pady=10, padx=20, fill="x")
        
        # 状态指示器
        self.status_indicator = tk.Label(
            status_frame,
            text="●",
            font=("Arial", 16),
            fg="#ff4444"  # 红色表示未运行
        )
        self.status_indicator.pack(side="left", padx=(0, 10))
        
        # 状态文本
        self.status_label = tk.Label(
            status_frame,
            text="状态: 未运行",
            font=("Microsoft YaHei", 12),
            fg="#666666"
        )
        self.status_label.pack(side="left")
        
        # 按钮区域
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=20, padx=40, fill="x")
        
        # 启动服务器按钮
        self.start_btn = tk.Button(
            button_frame,
            text="启动服务器",
            command=self.start_server,
            font=("Microsoft YaHei", 11),
            bg="#4CAF50",
            fg="white",
            relief="flat",
            height=2,
            cursor="hand2"
        )
        self.start_btn.pack(fill="x", pady=5)
        
        # 停止服务器按钮
        self.stop_btn = tk.Button(
            button_frame,
            text="停止服务器",
            command=self.stop_server,
            font=("Microsoft YaHei", 11),
            bg="#f44336",
            fg="white",
            relief="flat",
            height=2,
            cursor="hand2",
            state="disabled"
        )
        self.stop_btn.pack(fill="x", pady=5)
        
        # 重启服务器按钮
        self.restart_btn = tk.Button(
            button_frame,
            text="重启服务器",
            command=self.restart_server,
            font=("Microsoft YaHei", 11),
            bg="#2196F3",
            fg="white",
            relief="flat",
            height=2,
            cursor="hand2",
            state="disabled"
        )
        self.restart_btn.pack(fill="x", pady=5)
        
        # 检测状态按钮
        self.check_btn = tk.Button(
            button_frame,
            text="检测状态",
            command=self.check_status,
            font=("Microsoft YaHei", 11),
            bg="#FF9800",
            fg="white",
            relief="flat",
            height=2,
            cursor="hand2"
        )
        self.check_btn.pack(fill="x", pady=5)
        
        # 最小化到托盘按钮
        self.tray_btn = tk.Button(
            button_frame,
            text="最小化到托盘",
            command=self.minimize_to_tray,
            font=("Microsoft YaHei", 11),
            bg="#9C27B0",
            fg="white",
            relief="flat",
            height=2,
            cursor="hand2"
        )
        self.tray_btn.pack(fill="x", pady=5)
        
        # 退出程序按钮
        self.exit_btn = tk.Button(
            button_frame,
            text="退出程序",
            command=self.exit_program,
            font=("Microsoft YaHei", 11),
            bg="#607D8B",
            fg="white",
            relief="flat",
            height=2,
            cursor="hand2"
        )
        self.exit_btn.pack(fill="x", pady=5)
        
        # 版本信息
        version_label = tk.Label(
            self.root,
            text="v1.0.0",
            font=("Microsoft YaHei", 10),
            fg="#999999"
        )
        version_label.pack(side="bottom", pady=10)
        
        # 绑定按钮悬停效果
        self.bind_button_hover_effects()
        
    def bind_button_hover_effects(self):
        """绑定按钮悬停效果"""
        buttons = [self.start_btn, self.stop_btn, self.restart_btn, 
                  self.check_btn, self.tray_btn, self.exit_btn]
        
        for btn in buttons:
            btn.bind("<Enter>", lambda e, b=btn: self.on_button_hover(b, True))
            btn.bind("<Leave>", lambda e, b=btn: self.on_button_hover(b, False))
    
    def on_button_hover(self, button, entering):
        """按钮悬停效果"""
        if entering:
            button.config(relief="raised")
        else:
            button.config(relief="flat")
    
    def is_port_in_use(self, port):
        """检测端口是否被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0

    def kill_process_on_port(self, port):
        """杀死占用指定端口的进程"""
        for proc in psutil.process_iter(['pid', 'name', 'connections']):
            try:
                for conn in proc.info.get('connections', []):
                    if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                        proc.kill()
                        return True
            except Exception:
                continue
        return False

    def start_server(self):
        """启动服务器"""
        try:
            if self.server_process and self.server_process.poll() is None:
                messagebox.showinfo("提示", "服务器已在运行中")
                return
            # 检查server.py是否存在（仅源码模式下）
            if not getattr(sys, 'frozen', False) and not os.path.exists("server.py"):
                messagebox.showerror("错误", "找不到server.py文件")
                return
            # 启动前先调用 stop_server.py，彻底释放端口
            if os.path.exists("stop_server.py"):
                try:
                    subprocess.run([sys.executable, "stop_server.py"],
                                   capture_output=True,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                except Exception as e:
                    print(f"调用 stop_server.py 失败: {e}")
            # 多次检测端口是否被释放
            max_wait = 5
            for i in range(max_wait):
                if not self.is_port_in_use(self.server_port):
                    break
                time.sleep(1)
            else:
                # 端口仍被占用，列出占用进程
                msg = f"端口{self.server_port}仍被占用。"
                try:
                    procs = []
                    for proc in psutil.process_iter(['pid', 'name', 'connections']):
                        for conn in proc.info.get('connections', []):
                            if conn.status == psutil.CONN_LISTEN and conn.laddr.port == self.server_port:
                                procs.append(f"PID: {proc.info['pid']} 名称: {proc.info['name']}")
                    if procs:
                        msg += "\n占用进程:\n" + "\n".join(procs)
                    else:
                        msg += "\n未能检测到具体占用进程，可能需要以管理员身份运行。"
                except Exception as e:
                    msg += f"\n检测进程信息失败: {e}"
                messagebox.showerror("错误", msg)
                return
            # 启动服务器（区分源码/打包模式）
            if getattr(sys, 'frozen', False):
                # 打包模式，直接import server并用线程启动，异常写入日志
                def run_server_with_log():
                    try:
                        import server
                        server.run_server()
                    except Exception as e:
                        with open("server_error.log", "a", encoding="utf-8") as f:
                            f.write(traceback.format_exc())
                        print("服务启动异常，详情见 server_error.log")
                self.server_thread = threading.Thread(target=run_server_with_log, daemon=True)
                self.server_thread.start()
                time.sleep(2)
                if self.check_server_status():
                    self.server_running = True
                    self.update_status_display()
                    self.update_button_states()
                    messagebox.showinfo("成功", "服务器启动成功！\n访问地址: http://localhost:8000")
                    threading.Thread(target=self.open_browser, daemon=True).start()
                else:
                    self.server_running = False
                    print(f"222服务器启动失败，请检查端口是否被占用")
                    messagebox.showerror("错误", "服务器启动失败，请检查端口是否被占用")
                return
            # 源码模式，仍用subprocess.Popen
            self.server_process = subprocess.Popen(
                [sys.executable, "server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            print([sys.executable, "server.py"], self.server_process.pid)
            # 等待服务器启动
            time.sleep(10)
            # 检查服务器是否成功启动
            if self.check_server_status():
                self.server_running = True
                self.update_status_display()
                self.update_button_states()
                messagebox.showinfo("成功", "服务器启动成功！\n访问地址: http://localhost:8000")
                threading.Thread(target=self.open_browser, daemon=True).start()
            else:
                self.server_running = False
                print(f"111服务器启动失败，请检查端口是否被占用")
                messagebox.showerror("错误", "服务器启动失败，请检查端口是否被占用")
            return
        except Exception as e:
            messagebox.showerror("错误", f"启动服务器时发生错误:\n{str(e)}")
    
    def stop_server(self):
        """停止服务器"""
        try:
            if self.server_process:
                # 终止服务器进程
                self.server_process.terminate()
                
                # 等待进程结束
                try:
                    self.server_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # 强制终止
                    self.server_process.kill()
                
                self.server_process = None
            
            # 使用stop_server.py确保进程被终止
            if os.path.exists("stop_server.py"):
                try:
                    subprocess.run([sys.executable, "stop_server.py"], 
                                 capture_output=True, 
                                 creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                except:
                    pass
            
            self.server_running = False
            self.update_status_display()
            self.update_button_states()
            messagebox.showinfo("成功", "服务器已停止")
            
        except Exception as e:
            messagebox.showerror("错误", f"停止服务器时发生错误:\n{str(e)}")
    
    def restart_server(self):
        """重启服务器"""
        self.stop_server()
        time.sleep(1)
        self.start_server()
    
    def check_status(self):
        """检测服务器状态"""
        if self.check_server_status():
            self.server_running = True
            messagebox.showinfo("状态检测", "服务器运行正常！\n访问地址: http://localhost:8000")
        else:
            self.server_running = False
            messagebox.showinfo("状态检测", "服务器未运行")
        
        self.update_status_display()
        self.update_button_states()
    
    def check_server_status(self):
        """检查服务器状态"""
        try:
            response = requests.get(f"http://localhost:{self.server_port}/status", timeout=3)
            return response.status_code == 200
        except:
            return False
    
    def open_browser(self):
        """打开浏览器"""
        try:
            webbrowser.open(f"http://localhost:{self.server_port}")
        except:
            pass
    
    def update_status_display(self):
        """更新状态显示"""
        if self.server_running:
            self.status_indicator.config(fg="#4CAF50")  # 绿色
            self.status_label.config(text="状态: 运行中")
        else:
            self.status_indicator.config(fg="#ff4444")  # 红色
            self.status_label.config(text="状态: 未运行")
    
    def update_button_states(self):
        """更新按钮状态"""
        if self.server_running:
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.restart_btn.config(state="normal")
        else:
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.restart_btn.config(state="disabled")
    
    def status_monitor(self):
        """状态监控线程"""
        while True:
            try:
                # 检查服务器进程状态
                if self.server_process and self.server_process.poll() is not None:
                    # 进程已结束
                    self.server_running = False
                    self.server_process = None
                    self.root.after(0, self.update_status_display)
                    self.root.after(0, self.update_button_states)
                
                # 检查服务器响应状态
                if self.server_running and not self.check_server_status():
                    self.server_running = False
                    self.root.after(0, self.update_status_display)
                    self.root.after(0, self.update_button_states)
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception:
                time.sleep(5)
    
    def setup_tray(self):
        """设置系统托盘"""
        try:
            # 创建托盘图标
            if os.path.exists("icon.ico"):
                icon_image = Image.open("icon.ico")
            else:
                # 创建一个简单的图标
                icon_image = Image.new('RGB', (64, 64), color='blue')
            
            # 托盘菜单
            menu = pystray.Menu(
                pystray.MenuItem("显示主窗口", self.show_main_window),
                pystray.MenuItem("启动服务器", self.start_server),
                pystray.MenuItem("停止服务器", self.stop_server),
                pystray.MenuItem("打开网页", self.open_browser),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self.exit_program)
            )
            
            self.tray_icon = pystray.Icon("second_sight", icon_image, "千里眼-远程桌面", menu)
            
        except Exception as e:
            print(f"设置托盘失败: {e}")
            self.tray_icon = None
    
    def show_main_window(self):
        """显示主窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def minimize_to_tray(self):
        """最小化到托盘"""
        if self.tray_icon:
            self.root.withdraw()
            if not self.tray_icon.visible:
                self.tray_icon.run()
        else:
            self.root.iconify()
    
    def exit_program(self):
        """退出程序"""
        try:
            # 停止服务器
            if self.server_running:
                self.stop_server()
            
            # 停止托盘图标
            if self.tray_icon and self.tray_icon.visible:
                self.tray_icon.stop()
            
            # 退出程序
            self.root.quit()
            sys.exit(0)
            
        except Exception as e:
            print(f"退出程序时发生错误: {e}")
            sys.exit(1)
    
    def run(self):
        """运行程序"""
        try:
            # 检查是否已有实例运行
            if self.check_server_status():
                self.server_running = True
                self.update_status_display()
                self.update_button_states()
            
            self.root.mainloop()
            
        except KeyboardInterrupt:
            self.exit_program()

def main():
    """主函数"""
    try:
        app = ServiceManager()
        app.run()
    except Exception as e:
        messagebox.showerror("错误", f"程序启动失败:\n{str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
