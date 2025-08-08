import os
import sys
import json
import signal
import socket
import threading
import time
import subprocess
import urllib.request
import urllib.error
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Tuple, List


# -----------------------------
# Configuration loading helpers
# -----------------------------

def get_app_dir() -> str:
    """Return the directory where the app is running from.
    Works for both normal run and PyInstaller-frozen executable.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # Running from PyInstaller bundle
        return os.path.dirname(sys.executable)
    # Running as a normal Python script
    return os.path.dirname(os.path.abspath(__file__))


def load_config() -> dict:
    """Load server configuration from server_config.json if present.
    Otherwise return sensible defaults.
    """
    app_dir = get_app_dir()
    config_path = os.path.join(app_dir, "server_config.json")
    default_config = {
        "command": "python server.py",     # Change to your server start command
        "working_directory": app_dir,       # Change to your project directory if needed
        "port": 8000,                       # If your server listens on a port
        "healthcheck_url": "",            # Optional: e.g., http://127.0.0.1:8000/health
        "pid_file": os.path.join(app_dir, "server.pid"),
        "log_file": os.path.join(app_dir, "server.log"),
        "graceful_stop_seconds": 8
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            default_config.update({k: v for k, v in file_config.items() if v is not None})
        except Exception as exc:
            print(f"Failed to load config: {exc}")
    return default_config


# -----------------------------
# Server controller
# -----------------------------

class ServerController:
    def __init__(self, config: dict, on_status_update):
        self.config = config
        self.on_status_update = on_status_update
        self.process: Optional[subprocess.Popen] = None
        self._stdout_thread: Optional[threading.Thread] = None
        self._stderr_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    # ---------- Utility ----------
    def _write_log(self, message: str) -> None:
        log_file = self.config.get("log_file")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass

    def _update_status(self, message: str) -> None:
        self._write_log(message)
        if callable(self.on_status_update):
            self.on_status_update(message)

    def _parse_command(self) -> List[str]:
        command_str = self.config.get("command", "")
        if not command_str:
            return []
        # Let shell split by default on Windows can be problematic; use list via shell=False
        # A simple split is acceptable for most commands; for complex quoting, consider JSON array in config
        return command_str.split()

    def _pid_file_path(self) -> str:
        return self.config.get("pid_file", os.path.join(get_app_dir(), "server.pid"))

    def _read_pid(self) -> Optional[int]:
        pid_path = self._pid_file_path()
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "r", encoding="utf-8") as f:
                    return int(f.read().strip())
            except Exception:
                return None
        return None

    def _write_pid(self, pid: int) -> None:
        try:
            with open(self._pid_file_path(), "w", encoding="utf-8") as f:
                f.write(str(pid))
        except Exception:
            pass

    def _remove_pid_file(self) -> None:
        try:
            os.remove(self._pid_file_path())
        except Exception:
            pass

    def _is_pid_running(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            # On POSIX, signal 0 checks existence; on Windows, this still works for Python processes
            os.kill(pid, 0)
            return True
        except OSError:
            return False

    def _is_port_in_use(self, port: int, host: str = "127.0.0.1") -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            result = sock.connect_ex((host, port))
            return result == 0

    def _healthcheck(self) -> Tuple[bool, str]:
        url = self.config.get("healthcheck_url")
        port = self.config.get("port")
        if url:
            try:
                with urllib.request.urlopen(url, timeout=2.5) as resp:
                    ok = 200 <= resp.status < 300
                    return ok, f"HTTP {resp.status} from {url}"
            except urllib.error.URLError as exc:
                return False, f"Healthcheck failed: {exc}"
        elif port:
            ok = self._is_port_in_use(int(port))
            return ok, f"Port {port} is {'open' if ok else 'closed'}"
        else:
            return False, "No healthcheck_url or port configured"

    def is_running(self) -> bool:
        # Prefer child process handle if available
        if self.process and self.process.poll() is None:
            return True
        # Else check PID file
        pid = self._read_pid()
        if pid and self._is_pid_running(pid):
            return True
        # Else heuristic: port check
        port = self.config.get("port")
        if port and self._is_port_in_use(int(port)):
            return True
        return False

    # ---------- Process IO threads ----------
    def _stream_to_log(self, stream, tag: str) -> None:
        try:
            for line in iter(stream.readline, b""):
                if not line:
                    break
                text = line.decode(errors="replace").rstrip()
                self._write_log(f"[{tag}] {text}")
        except Exception:
            pass
        finally:
            try:
                stream.close()
            except Exception:
                pass

    # ---------- Actions ----------
    def start_server(self) -> None:
        with self._lock:
            if self.is_running():
                self._update_status("Server is already running.")
                return

            command_list = self._parse_command()
            if not command_list:
                self._update_status("Invalid server start command. Please set 'command' in server_config.json.")
                return

            cwd = self.config.get("working_directory") or get_app_dir()
            if not os.path.isdir(cwd):
                self._update_status(f"Working directory does not exist: {cwd}")
                return

            self._stop_event.clear()
            creationflags = 0
            startupinfo = None
            preexec_fn = None

            # On Windows, detach new process group so it can receive CTRL_BREAK_EVENT if needed
            if os.name == "nt":
                creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            else:
                # On POSIX, start new session so we can signal the whole group
                try:
                    import signal as _signal  # noqa: F401
                    preexec_fn = os.setsid
                except Exception:
                    preexec_fn = None

            try:
                self.process = subprocess.Popen(
                    command_list,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL,
                    text=False,
                    shell=False,
                    creationflags=creationflags,
                    startupinfo=startupinfo,
                    preexec_fn=preexec_fn,
                )
                self._write_pid(self.process.pid)
                self._update_status(f"Started server (PID {self.process.pid}).")

                # Start background threads to pipe logs into file
                if self.process.stdout:
                    self._stdout_thread = threading.Thread(target=self._stream_to_log, args=(self.process.stdout, "stdout"), daemon=True)
                    self._stdout_thread.start()
                if self.process.stderr:
                    self._stderr_thread = threading.Thread(target=self._stream_to_log, args=(self.process.stderr, "stderr"), daemon=True)
                    self._stderr_thread.start()
            except FileNotFoundError:
                self._update_status("Failed to start server: command not found.")
            except Exception as exc:
                self._update_status(f"Failed to start server: {exc}")

    def stop_server(self) -> None:
        with self._lock:
            graceful_seconds = int(self.config.get("graceful_stop_seconds", 8))

            # Prefer child handle
            if self.process and self.process.poll() is None:
                pid = self.process.pid
                self._update_status(f"Stopping server (PID {pid})...")
                try:
                    if os.name == "nt":
                        # Try graceful CTRL_BREAK_EVENT to the process group
                        try:
                            self.process.send_signal(signal.CTRL_BREAK_EVENT)
                        except Exception:
                            self.process.terminate()
                    else:
                        try:
                            os.killpg(os.getpgid(pid), signal.SIGTERM)
                        except Exception:
                            self.process.terminate()

                    # Wait up to graceful_seconds
                    try:
                        self.process.wait(timeout=graceful_seconds)
                    except subprocess.TimeoutExpired:
                        self._update_status("Graceful stop timed out; killing server...")
                        if os.name == "nt":
                            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
                        else:
                            try:
                                os.killpg(os.getpgid(pid), signal.SIGKILL)
                            except Exception:
                                self.process.kill()
                finally:
                    self._cleanup_after_stop()
                return

            # Else stop by PID file if possible
            pid = self._read_pid()
            if pid and self._is_pid_running(pid):
                self._update_status(f"Stopping server by PID file (PID {pid})...")
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
                else:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:
                        pass
                    # Give a moment then SIGKILL if necessary
                    for _ in range(graceful_seconds):
                        if not self._is_pid_running(pid):
                            break
                        time.sleep(1)
                    if self._is_pid_running(pid):
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except Exception:
                            pass
                self._cleanup_after_stop()
                return

            self._update_status("Server is not running.")

    def _cleanup_after_stop(self) -> None:
        try:
            if self.process and self.process.stdout:
                try:
                    self.process.stdout.close()
                except Exception:
                    pass
            if self.process and self.process.stderr:
                try:
                    self.process.stderr.close()
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            self.process = None
            self._remove_pid_file()
            self._update_status("Server stopped.")

    def restart_server(self) -> None:
        self._update_status("Restarting server...")
        self.stop_server()
        # Short delay before restart
        time.sleep(1)
        self.start_server()

    def detect_server(self) -> None:
        running = self.is_running()
        ok, detail = self._healthcheck()
        status = "RUNNING" if running else "STOPPED"
        self._update_status(f"Detect: status={status}. {detail}")


# -----------------------------
# Tkinter GUI
# -----------------------------

class ServerGUI(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Server Controller")
        self.geometry("520x320")
        self.resizable(False, False)

        self.config_data = load_config()
        self.controller = ServerController(self.config_data, self.on_status_update)

        self._build_widgets()
        self._update_running_indicator()

        # Periodically update running indicator
        self.after(1500, self._periodic_update)

    def _build_widgets(self) -> None:
        padding = {"padx": 10, "pady": 10}

        # Command info
        frm_top = ttk.Frame(self)
        frm_top.pack(fill=tk.X, **padding)

        lbl_cmd = ttk.Label(frm_top, text=f"Command: {self.config_data.get('command')}")
        lbl_cmd.pack(anchor=tk.W)

        lbl_cwd = ttk.Label(frm_top, text=f"Working dir: {self.config_data.get('working_directory')}")
        lbl_cwd.pack(anchor=tk.W)

        # Buttons
        frm_btn = ttk.Frame(self)
        frm_btn.pack(fill=tk.X, **padding)

        self.btn_start = ttk.Button(frm_btn, text="启动 server", command=self._on_start)
        self.btn_start.pack(side=tk.LEFT, padx=5)

        self.btn_stop = ttk.Button(frm_btn, text="停止 server", command=self._on_stop)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_restart = ttk.Button(frm_btn, text="重启 server", command=self._on_restart)
        self.btn_restart.pack(side=tk.LEFT, padx=5)

        self.btn_detect = ttk.Button(frm_btn, text="检测 server", command=self._on_detect)
        self.btn_detect.pack(side=tk.LEFT, padx=5)

        self.btn_minimize = ttk.Button(frm_btn, text="最小化", command=self._on_minimize)
        self.btn_minimize.pack(side=tk.LEFT, padx=5)

        # Running indicator
        frm_status = ttk.Frame(self)
        frm_status.pack(fill=tk.X, **padding)

        self.var_running = tk.StringVar(value="未知")
        self.lbl_running = ttk.Label(frm_status, textvariable=self.var_running, foreground="blue")
        self.lbl_running.pack(anchor=tk.W)

        # Log box
        frm_log = ttk.Frame(self)
        frm_log.pack(fill=tk.BOTH, expand=True, **padding)

        self.txt_log = tk.Text(frm_log, height=10, wrap=tk.NONE)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.var_status = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self, textvariable=self.var_status, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ---------- UI helpers ----------
    def on_status_update(self, message: str) -> None:
        # Append to text box and status bar in UI thread
        def append():
            try:
                self.txt_log.insert(tk.END, message + "\n")
                self.txt_log.see(tk.END)
                self.var_status.set(message)
                self._update_running_indicator()
            except Exception:
                pass
        self.after(0, append)

    def _update_running_indicator(self) -> None:
        is_running = self.controller.is_running()
        ok, detail = self.controller._healthcheck()
        text = f"当前状态: {'运行中' if is_running else '未运行'} | {detail}"
        self.var_running.set(text)
        self.lbl_running.configure(foreground=("green" if is_running else "red"))

    def _periodic_update(self) -> None:
        self._update_running_indicator()
        self.after(1500, self._periodic_update)

    # ---------- Button handlers ----------
    def _run_in_thread(self, target):
        th = threading.Thread(target=target, daemon=True)
        th.start()

    def _on_start(self) -> None:
        self._run_in_thread(self.controller.start_server)

    def _on_stop(self) -> None:
        self._run_in_thread(self.controller.stop_server)

    def _on_restart(self) -> None:
        self._run_in_thread(self.controller.restart_server)

    def _on_detect(self) -> None:
        self._run_in_thread(self.controller.detect_server)

    def _on_minimize(self) -> None:
        self.iconify()

    # ---------- Lifecycle ----------
    def destroy(self) -> None:
        # Do not auto-stop server; keep it running unless user chose to stop
        return super().destroy()


def main():
    app = ServerGUI()
    app.mainloop()


if __name__ == "__main__":
    main()