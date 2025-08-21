import pythoncom
import win32com.client
import win32gui
import os
import urllib.parse
import ctypes
from ctypes import wintypes


class ForegroundPathDetector:
    """检测前台文件资源管理器路径或桌面路径的类"""

    def __init__(self):
        """初始化检测器"""
        # 桌面窗口类名
        self.DESKTOP_CLASSES = ["Progman", "WorkerW"]
        # 初始化COM组件
        self._initialize_com()

    def _initialize_com(self):
        """初始化COM组件"""
        try:
            pythoncom.CoInitialize()
        except Exception as e:
            print(f"COM组件初始化失败: {str(e)}")

    def get_desktop_path(self):
        """获取当前用户的桌面路径"""
        CSIDL_DESKTOP = 0x0000
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(
            None, CSIDL_DESKTOP, None, SHGFP_TYPE_CURRENT, buf)
        return buf.value

    def is_desktop_foreground(self):
        """判断当前前台窗口是否为桌面"""
        foreground_hwnd = win32gui.GetForegroundWindow()
        if not foreground_hwnd:
            return False

        class_name = win32gui.GetClassName(foreground_hwnd)
        return class_name in self.DESKTOP_CLASSES

    def _parse_explorer_path(self, location_url):
        """解析资源管理器的URL为本地路径"""
        if location_url.startswith("file:///"):
            path = location_url[8:].replace("/", "\\")
            path = urllib.parse.unquote(path)

            # 处理编码问题
            try:
                path = path.encode('latin-1').decode('gbk')
            except:
                try:
                    path = path.encode('latin-1').decode('utf-8')
                except:
                    pass

            if os.path.exists(path):
                return path
        return None

    def get_foreground_path(self):
        """
        获取前台路径

        返回值:
            tuple: (类型, 路径)
                  类型包括: "explorer" (资源管理器), "desktop" (桌面), "none" (无匹配), "error" (错误)
        """
        try:
            # 获取前台窗口句柄
            foreground_hwnd = win32gui.GetForegroundWindow()

            # 检查文件资源管理器窗口
            shell = win32com.client.Dispatch("Shell.Application")
            shell_windows = shell.Windows()

            for window in shell_windows:
                if "explorer.exe" in window.FullName.lower():
                    path = self._parse_explorer_path(window.LocationURL)
                    if path and window.HWND == foreground_hwnd:
                        return ("explorer", path)

            # 检查是否在桌面
            if self.is_desktop_foreground():
                return ("desktop", self.get_desktop_path())

            # 无匹配情况
            return ("none", None)

        except Exception as e:
            print(f"获取路径时出错: {str(e)}")
            return ("error", None)

    def __del__(self):
        """析构函数，释放COM资源"""
        try:
            pythoncom.CoUninitialize()
        except:
            pass


if __name__ == "__main__":
    import time
    time.sleep(5)  # 本地调试用
    # 使用示例
    detector = ForegroundPathDetector()
    result_type, path = detector.get_foreground_path()

    if result_type == "explorer":
        print(f"当前前台文件资源管理器路径: {path}")
    elif result_type == "desktop":
        print(f"当前在桌面，桌面路径: {path}")
    elif result_type == "none":
        print("没有打开的文件资源管理器窗口，且当前不在桌面")
    else:
        print("获取路径时发生错误")
