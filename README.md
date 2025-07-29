# Second Sight - 远程桌面系统

一个基于FastAPI和WebSocket的实时Windows桌面截图和监控工具，支持多显示器独立显示。

## 功能特性

### 🖥️ 多显示器支持
- **自动检测**：自动识别系统中的所有显示器
- **独立显示**：每个显示器独立显示，不拼接
- **主显示器标识**：绿色边框标识主显示器
- **独立刷新**：每个显示器可单独刷新
- **全屏查看**：点击图片或全屏按钮查看

### 📊 实时监控
- **系统资源监控**：实时显示内存、CPU使用率
- **网络状态监控**：检测网络连接质量和延迟
- **WebSocket实时通信**：实时更新状态信息
- **自动刷新**：可设置自动刷新间隔

### 🔧 调试功能
- **显示器配置查看**：显示详细的显示器配置信息
- **强制重新检测**：强制重新检测显示器配置
- **单个显示器调试**：单独测试每个显示器的截图功能
- **系统信息查看**：查看详细的系统资源使用情况

## 安装依赖

```bash
pip install -r requirements.txt
```

### 依赖包说明
- `fastapi`: Web框架
- `uvicorn`: ASGI服务器
- `pillow`: 图像处理
- `pywin32`: Windows API接口
- `psutil`: 系统资源监控

## 运行方式

### 方式1：直接打开HTML文件
1. 启动服务器：
   ```bash
   python server.py
   ```
2. 双击打开 `index.html`
3. 页面会自动连接到 `localhost:8000`

### 方式2：通过HTTP访问
1. 启动服务器：
   ```bash
   python server.py
   ```
2. 浏览器访问：`http://localhost:8000`

## API接口

### 基础接口
- `GET /` - 主页
- `GET /status` - 服务器状态
- `GET /screenshot` - 获取桌面截图

### 多显示器接口
- `GET /screenshots/all` - 获取所有显示器截图
- `GET /screenshot/monitor/{monitor_index}` - 获取指定显示器截图
- `GET /monitors/config` - 获取显示器配置信息

### 监控接口
- `GET /system-info` - 获取系统资源信息
- `GET /test-network` - 测试网络连接
- `GET /force-redetect` - 强制重新检测显示器

### 调试接口
- `GET /debug/monitor/{monitor_index}` - 调试指定显示器
- `GET /screenshot-info` - 获取截图详细信息

### WebSocket
- `WS /ws` - 实时状态推送

## 系统监控功能

### 内存监控
- 实时内存使用率
- 总内存、已用内存、可用内存
- 自动更新（每5秒）

### CPU监控
- 实时CPU使用率
- CPU核心数、频率
- 自动更新（每5秒）

### 磁盘监控
- 磁盘使用率
- 总容量、已用空间、可用空间
- 自动更新（每5秒）

### 网络监控
- 网络连接状态
- 网络延迟
- 自动更新（每30秒）

## 技术架构

### 后端 (Python)
- **FastAPI**: 现代、快速的Web框架
- **WebSocket**: 实时双向通信
- **win32api**: Windows系统API调用
- **PIL**: 图像处理和截图
- **psutil**: 系统资源监控

### 前端 (HTML/CSS/JavaScript)
- **响应式设计**: 适配不同屏幕尺寸
- **实时更新**: WebSocket实时通信
- **多显示器布局**: 网格布局显示多个显示器
- **交互式控制**: 丰富的用户交互功能

## 故障排除

### 常见问题

1. **显示器检测不准确**
   - 点击"强制重新检测"按钮
   - 检查Windows显示设置
   - 查看系统日志获取详细信息

2. **截图显示不全**
   - 运行诊断脚本：`python deep_diagnosis.py`
   - 检查显示器配置信息
   - 确认显示器排列设置

3. **系统监控数据异常**
   - 检查psutil是否正确安装
   - 确认有足够的系统权限
   - 查看服务器日志

### 调试工具

- **深度诊断脚本**: `python deep_diagnosis.py`
- **显示器测试脚本**: `python test_monitor_capture.py`
- **前端调试按钮**: 使用界面上的调试功能

## 开发说明

### 项目结构
```
second-sight/
├── server.py              # 主服务器文件
├── index.html             # 前端界面
├── requirements.txt       # Python依赖
├── README.md             # 项目说明
├── deep_diagnosis.py     # 深度诊断脚本
├── test_monitor_capture.py # 显示器测试脚本
└── start_server.bat      # 启动脚本
```

### 扩展功能
- 支持更多显示器配置
- 添加更多系统监控指标
- 实现远程控制功能
- 添加用户认证和权限控制

## 许可证

MIT License 