import sys
import tkinter as tk
from tkinter import messagebox, ttk
import tkinter.font as font
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw
import threading

class SecondSightManager(tk.Tk):
    def __init__(self):
        super().__init__()
        self.tray_icon = None  # 托盘图标实例
        # 先隐藏窗口，避免居中过程可见
        self.withdraw()
        # 计算居中位置并设置
        self.calculate_center_position()
        # 初始化UI
        self.init_ui()
        # 显示窗口
        self.deiconify()
        self.create_tray_icon()
        
    def calculate_center_position(self):
        # 获取屏幕宽度和高度
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # 窗口尺寸
        window_width = 400
        window_height = 560
        
        # 计算居中位置
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        # 设置窗口大小和位置（一次性完成）
        self.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.resizable(False, False)  # 禁止窗口大小调整
        
    def init_ui(self):
        # 设置窗口标题
        self.title("千里眼-远程桌面 服务管理器")
        
        # 设置中文字体支持
        self.default_font = font.Font(family="微软雅黑", size=10)
        self.title_font = font.Font(family="微软雅黑", size=16, weight="bold")
        self.status_font = font.Font(family="微软雅黑", size=11)
        self.version_font = font.Font(family="微软雅黑", size=9)
        
        # 配置样式
        self.style = ttk.Style()
        self.style.theme_use('clam')  # 使用clam主题获得更好的跨平台一致性
        
        # 定义按钮样式
        self.style.configure("Start.TButton", 
                           font=self.default_font,
                           padding=10,
                           background="#4CAF50",  # 绿色
                           foreground="white")
        self.style.map("Start.TButton",
                      background=[("active", "#45a049"), ("pressed", "#3d8b40")])
        
        self.style.configure("Stop.TButton", 
                           font=self.default_font,
                           padding=10,
                           background="#f44336",  # 红色
                           foreground="white")
        self.style.map("Stop.TButton",
                      background=[("active", "#d32f2f"), ("pressed", "#b71c1c")])
        
        self.style.configure("Restart.TButton", 
                           font=self.default_font,
                           padding=10,
                           background="#2196F3",  # 蓝色
                           foreground="white")
        self.style.map("Restart.TButton",
                      background=[("active", "#0b7dda"), ("pressed", "#0d47a1")])
        
        self.style.configure("Check.TButton", 
                           font=self.default_font,
                           padding=10,
                           background="#FFC107",  # 黄色
                           foreground="black")
        self.style.map("Check.TButton",
                      background=[("active", "#ffb300"), ("pressed", "#ff8f00")])
        
        self.style.configure("Tray.TButton", 
                           font=self.default_font,
                           padding=10,
                           background="#9C27B0",  # 紫色
                           foreground="white")
        self.style.map("Tray.TButton",
                      background=[("active", "#7b1fa2"), ("pressed", "#4a148c")])
        
        self.style.configure("Exit.TButton", 
                           font=self.default_font,
                           padding=10,
                           background="#607D8B",  # 灰色
                           foreground="white")
        self.style.map("Exit.TButton",
                      background=[("active", "#546E7A"), ("pressed", "#37474F")])
        
        # 创建主框架
        main_frame = ttk.Frame(self, padding="20 20 20 20", relief="solid", borderwidth=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 标题
        title_label = ttk.Label(main_frame, text="服务管理器", font=self.title_font)
        title_label.pack(pady=(0, 25))
        
        # 状态显示区域
        status_frame = ttk.Frame(main_frame, padding=10, relief="flat", borderwidth=1)
        status_frame.pack(fill=tk.X, pady=(0, 25))
        status_frame.configure(style="Status.TFrame")
        self.style.configure("Status.TFrame", background="#f0f0f0")
        
        self.status_var = tk.StringVar(value="状态: 运行中")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                font=self.status_font, foreground="#2E7D32")
        status_label.pack()
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=False)
        
        # 创建按钮
        ttk.Button(button_frame, text="启动服务器", command=self.start_server, 
                  style="Start.TButton").pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="停止服务器", command=self.stop_server, 
                  style="Stop.TButton").pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="重启服务器", command=self.restart_server, 
                  style="Restart.TButton").pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="检测状态", command=self.check_status, 
                  style="Check.TButton").pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="最小化到托盘", command=self.min_to_tray, 
                  style="Tray.TButton").pack(fill=tk.X, pady=5)
        ttk.Button(button_frame, text="退出程序", command=self.exit_program, 
                  style="Exit.TButton").pack(fill=tk.X, pady=5)
        
        # 版本信息
        version_label = ttk.Label(main_frame, text="v1.0.0", font=self.version_font)
        version_label.pack(side=tk.BOTTOM, pady=10)
    
    # 显示窗口（从托盘恢复时）
    def show_window(self):
        self.deiconify()  # 从最小化状态恢复
        self.lift()  # 窗口置顶
        # 重新计算居中位置（应对可能的屏幕分辨率变化）
        self.calculate_center_position()
    
    # 最小化到托盘
    def min_to_tray(self):
        self.withdraw()  # 隐藏窗口
        messagebox.showinfo("提示", "程序已最小化到系统托盘")
    
    # 创建托盘图标
    def create_tray_icon(self):
        # 创建一个简单的图标（实际应用中可替换为自己的图标）
        image = Image.new('RGB', (64, 64), color=(73, 109, 137))
        draw = ImageDraw.Draw(image)
        draw.text((10, 20), "千里眼", fill=(255, 255, 255))
        
        # 创建托盘菜单
        menu = Menu(
            MenuItem("显示窗口", self.show_window),
            MenuItem("退出", self.exit_program)
        )
        
        # 创建托盘图标
        self.tray_icon = Icon("千里眼服务", image, "千里眼-远程桌面服务", menu)
        
        # 在后台线程中运行托盘图标
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    # 按钮功能实现
    def start_server(self):
        self.status_var.set("状态: 启动中...")
        # 实际应用中添加启动服务器的代码
        self.after(1000, lambda: self.status_var.set("状态: 运行中"))  # 模拟启动过程
    
    def stop_server(self):
        self.status_var.set("状态: 停止中...")
        # 实际应用中添加停止服务器的代码
        self.after(1000, lambda: self.status_var.set("状态: 已停止"))  # 模拟停止过程
    
    def restart_server(self):
        self.status_var.set("状态: 重启中...")
        # 实际应用中添加重启服务器的代码
        self.after(1500, lambda: self.status_var.set("状态: 运行中"))  # 模拟重启过程
    
    def check_status(self):
        # 实际应用中添加检测服务器状态的代码
        current_status = self.status_var.get()
        messagebox.showinfo("状态检测", f"当前服务器状态: {current_status.split(': ')[1]}")
    
    def exit_program(self):
        if messagebox.askyesno("确认", "确定要退出程序吗？"):
            if self.tray_icon:
                self.tray_icon.stop()  # 停止托盘图标
            self.destroy()  # 关闭窗口
            sys.exit(0)  # 退出程序

if __name__ == "__main__":
    app = SecondSightManager()
    app.mainloop()
