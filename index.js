let ws = null;
let autoRefreshInterval = null;
let isConnected = false;

// 文件管理相关变量
let selectedFiles = []; // 当前选择的文件列表
let selectedPath = null; // 当前选择的目标路径
let selectedPathName = null; // 当前选择的路径名称

// 趋势图数据管理
let memoryTrendData = [];
let cpuTrendData = [];
let networkLatencyTrendData = [];
const MAX_TREND_POINTS = 20;
let lastSystemUpdateTime = 0;
const SYSTEM_UPDATE_INTERVAL = 5000; // 5秒更新间隔

// 绘制内存使用率趋势图
function drawMemoryTrendChart() {
    const canvas = document.getElementById('memory-trend-chart');
    if (!canvas || memoryTrendData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 固定数据范围为0-100
    const minValue = 0;
    const maxValue = 100;
    const range = maxValue - minValue;

    // 绘制网格线
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // 绘制趋势线
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    memoryTrendData.forEach((value, index) => {
        const x = (index / (memoryTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // 绘制数据点
    ctx.fillStyle = '#667eea';
    memoryTrendData.forEach((value, index) => {
        const x = (index / (memoryTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
    });
}

// 绘制CPU使用率趋势图
function drawCpuTrendChart() {
    const canvas = document.getElementById('cpu-trend-chart');
    if (!canvas || cpuTrendData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 固定数据范围为0-100
    const minValue = 0;
    const maxValue = 100;
    const range = maxValue - minValue;

    // 绘制网格线
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // 绘制趋势线
    ctx.strokeStyle = '#56ab2f';
    ctx.lineWidth = 2;
    ctx.beginPath();

    cpuTrendData.forEach((value, index) => {
        const x = (index / (cpuTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // 绘制数据点
    ctx.fillStyle = '#56ab2f';
    cpuTrendData.forEach((value, index) => {
        const x = (index / (cpuTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
    });
}

// 绘制网络延迟趋势图
function drawNetworkLatencyTrendChart() {
    const canvas = document.getElementById('network-latency-trend-chart');
    if (!canvas || networkLatencyTrendData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 固定数据范围为0-最大延迟值
    const minValue = 0;
    const maxValue = Math.max(...networkLatencyTrendData, 50); // 至少50ms，确保有足够范围
    const range = maxValue - minValue;

    // 绘制网格线
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // 绘制趋势线
    ctx.strokeStyle = '#f39c12';
    ctx.lineWidth = 2;
    ctx.beginPath();

    networkLatencyTrendData.forEach((value, index) => {
        const x = (index / (networkLatencyTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // 绘制数据点
    ctx.fillStyle = '#f39c12';
    networkLatencyTrendData.forEach((value, index) => {
        const x = (index / (networkLatencyTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
    });
}

// 添加内存使用率数据点
function addMemoryDataPoint(value) {
    if (typeof value === 'number' && !isNaN(value)) {
        memoryTrendData.push(value);

        // 保持最多 MAX_TREND_POINTS 个数据点
        if (memoryTrendData.length > MAX_TREND_POINTS) {
            memoryTrendData.shift();
        }

        // 重新绘制趋势图
        drawMemoryTrendChart();

        // 更新工具提示
        updateTrendChartTooltip();
    }
}

// 添加CPU使用率数据点
function addCpuDataPoint(value) {
    if (typeof value === 'number' && !isNaN(value)) {
        cpuTrendData.push(value);

        // 保持最多 MAX_TREND_POINTS 个数据点
        if (cpuTrendData.length > MAX_TREND_POINTS) {
            cpuTrendData.shift();
        }

        // 重新绘制趋势图
        drawCpuTrendChart();

        // 更新工具提示
        updateTrendChartTooltip();
    }
}

// 添加网络延迟数据点
function addNetworkLatencyDataPoint(value) {
    if (typeof value === 'number' && !isNaN(value)) {
        networkLatencyTrendData.push(value);

        // 保持最多 MAX_TREND_POINTS 个数据点
        if (networkLatencyTrendData.length > MAX_TREND_POINTS) {
            networkLatencyTrendData.shift();
        }

        // 重新绘制趋势图
        drawNetworkLatencyTrendChart();

        // 更新工具提示
        updateTrendChartTooltip();
    }
}

// 更新趋势图工具提示
function updateTrendChartTooltip() {
    const memoryCanvas = document.getElementById('memory-trend-chart');
    const cpuCanvas = document.getElementById('cpu-trend-chart');
    const networkLatencyCanvas = document.getElementById('network-latency-trend-chart');

    // 更新内存趋势图工具提示
    if (memoryCanvas) {
        if (memoryTrendData.length > 0) {
            const latest = memoryTrendData[memoryTrendData.length - 1];
            const min = Math.min(...memoryTrendData);
            const max = Math.max(...memoryTrendData);
            const avg = (memoryTrendData.reduce((a, b) => a + b, 0) / memoryTrendData.length).toFixed(1);

            memoryCanvas.title = `内存使用率趋势\n最新: ${latest}%\n最高: ${max}%\n最低: ${min}%\n平均: ${avg}%`;
        } else {
            memoryCanvas.title = '内存使用率趋势\n暂无数据';
        }
    }

    // 更新CPU趋势图工具提示
    if (cpuCanvas) {
        if (cpuTrendData.length > 0) {
            const latest = cpuTrendData[cpuTrendData.length - 1];
            const min = Math.min(...cpuTrendData);
            const max = Math.max(...cpuTrendData);
            const avg = (cpuTrendData.reduce((a, b) => a + b, 0) / cpuTrendData.length).toFixed(1);

            cpuCanvas.title = `CPU使用率趋势\n最新: ${latest}%\n最高: ${max}%\n最低: ${min}%\n平均: ${avg}%`;
        } else {
            cpuCanvas.title = 'CPU使用率趋势\n暂无数据';
        }
    }

    // 更新网络延迟趋势图工具提示
    if (networkLatencyCanvas) {
        if (networkLatencyTrendData.length > 0) {
            const latest = networkLatencyTrendData[networkLatencyTrendData.length - 1];
            const min = Math.min(...networkLatencyTrendData);
            const max = Math.max(...networkLatencyTrendData);
            const avg = (networkLatencyTrendData.reduce((a, b) => a + b, 0) / networkLatencyTrendData.length).toFixed(1);

            networkLatencyCanvas.title = `网络延迟趋势\n最新: ${latest}ms\n最高: ${max}ms\n最低: ${min}ms\n平均: ${avg}ms`;
        } else {
            networkLatencyCanvas.title = '网络延迟趋势\n暂无数据';
        }
    }
}

// 检查服务器状态
async function checkServerStatus() {
    try {
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/status`);
        const data = await response.json();
        addLog('连接', '服务器连接正常', 'success');
        return true;
    } catch (error) {
        addLog('连接', '无法连接到服务器，请确保服务器正在运行', 'error');
        return false;
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', function () {
    addLog('系统', '页面加载完成', 'success');

    // 初始化趋势图
    drawMemoryTrendChart();
    drawCpuTrendChart(); // 初始化CPU趋势图
    drawNetworkLatencyTrendChart(); // 初始化网络延迟趋势图
    updateTrendChartTooltip();

    // 检测环境并显示信息
    const environment = detectEnvironment();
    const serverUrl = getServerBaseUrl();
    addLog('系统', `服务器地址: ${serverUrl}`, 'info');

    // 检查服务器状态
    checkServerStatus().then(serverAvailable => {
        if (serverAvailable) {
            connectWebSocket();
            refreshAllMonitors(); // 默认加载多显示器模式
        } else {
            addLog('系统', '请先启动服务器: python server.py', 'warning');
        }
    });
});

// 检测运行环境
function detectEnvironment() {
    const isFileProtocol = window.location.protocol === 'file:';
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    if (isFileProtocol) {
        addLog('系统', '检测到文件协议模式，将使用本地服务器', 'info');
        return 'file';
    } else if (isLocalhost) {
        addLog('系统', '检测到本地服务器模式', 'info');
        return 'localhost';
    } else {
        addLog('系统', '检测到远程服务器模式', 'info');
        return 'remote';
    }
}

// 获取服务器基础URL
function getServerBaseUrl() {
    const environment = detectEnvironment();

    if (environment === 'file') {
        // 文件协议模式，使用默认的本地服务器地址
        return 'http://localhost:8000';
    } else {
        // HTTP协议模式，使用当前域名
        return `${window.location.protocol}//${window.location.host}`;
    }
}

// 获取WebSocket URL
function getWebSocketUrl() {
    const environment = detectEnvironment();

    if (environment === 'file') {
        // 文件协议模式，使用默认的本地服务器WebSocket地址
        return 'ws://localhost:8000/ws';
    } else {
        // HTTP协议模式，根据当前协议选择WebSocket协议
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws`;
    }
}

// WebSocket连接
function connectWebSocket() {
    const wsUrl = getWebSocketUrl();

    addLog('连接', `尝试连接到: ${wsUrl}`, 'info');

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = function () {
            isConnected = true;
            updateConnectionStatus(true);
            addLog('连接', 'WebSocket连接成功', 'success');
        };

        ws.onmessage = function (event) {
            try {
                const data = JSON.parse(event.data);
                updateStatus(data);
            } catch (e) {
                addLog('连接', '数据解析错误: ' + e.message, 'error');
            }
        };

        ws.onclose = function () {
            isConnected = false;
            updateConnectionStatus(false);
            addLog('连接', 'WebSocket连接断开', 'warning');

            // 尝试重新连接
            setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = function (error) {
            addLog('连接', 'WebSocket连接错误: ' + (error.message || '未知错误'), 'error');
        };
    } catch (error) {
        addLog('连接', '创建连接失败: ' + error.message, 'error');
    }
}

// 更新连接状态
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('server-status');
    const indicator = statusElement.querySelector('.connection-indicator');

    if (connected) {
        indicator.className = 'connection-indicator connected';
        statusElement.innerHTML = '<span class="connection-indicator connected"></span>已连接';
    } else {
        indicator.className = 'connection-indicator disconnected';
        statusElement.innerHTML = '<span class="connection-indicator disconnected"></span>未连接';
    }
}

// 网络状态映射
function getNetworkStatusText(status) {
    const statusMap = {
        'excellent': '优秀',
        'good': '良好',
        'fair': '一般',
        'poor': '较差',
        'disconnected': '断开连接',
        'unknown': '未知'
    };
    return statusMap[status] || status;
}

// 获取网络状态颜色
function getNetworkStatusColor(status) {
    const colorMap = {
        'excellent': '#27ae60',
        'good': '#2ecc71',
        'fair': '#f39c12',
        'poor': '#e67e22',
        'disconnected': '#e74c3c',
        'unknown': '#95a5a6'
    };
    return colorMap[status] || '#95a5a6';
}

// 更新状态信息
function updateStatus(data) {
    if (data.type === 'status') {
        document.getElementById('last-update').textContent = new Date(data.timestamp).toLocaleTimeString();

        // 从服务端获取真实的内存、CPU和磁盘使用率
        const memoryUsage = typeof data.memory_usage !== 'undefined' ? data.memory_usage : '-';
        const cpuUsage = typeof data.cpu_usage !== 'undefined' ? data.cpu_usage : '-';
        const diskUsage = typeof data.disk_usage !== 'undefined' ? data.disk_usage : '-';

        document.getElementById('status-memory-usage').textContent = memoryUsage + '%';
        document.getElementById('status-cpu-usage').textContent = cpuUsage + '%';
        document.getElementById('status-disk-usage').textContent = diskUsage + '%';

        // 添加内存和CPU使用率数据点到趋势图（每5秒更新一次）
        const currentTime = Date.now();
        if (currentTime - lastSystemUpdateTime >= SYSTEM_UPDATE_INTERVAL) {
            if (typeof data.memory_usage === 'number') {
                addMemoryDataPoint(data.memory_usage);
            }

            if (typeof data.cpu_usage === 'number') {
                addCpuDataPoint(data.cpu_usage);
            }

            // 更新最后更新时间
            lastSystemUpdateTime = currentTime;
        }

        // 更新真实网络状态
        if (data.network) {
            const networkStatusElement = document.getElementById('status-network-status');
            const networkLatencyElement = document.getElementById('status-network-latency');

            const statusText = getNetworkStatusText(data.network.status);
            const statusColor = getNetworkStatusColor(data.network.status);

            networkStatusElement.textContent = statusText;
            networkStatusElement.style.color = statusColor;

            if (data.network.latency >= 0) {
                networkLatencyElement.textContent = data.network.latency + 'ms';
                // 添加网络延迟数据点到趋势图
                addNetworkLatencyDataPoint(data.network.latency);
            } else {
                networkLatencyElement.textContent = '-';
            }
        }
    }
}

// 刷新截图
async function refreshScreenshot() {
    try {
        // 显示加载指示器
        const loadingIndicator = document.getElementById('loading-indicator');
        const screenshot = document.getElementById('screenshot');
        loadingIndicator.style.display = 'block';
        screenshot.style.opacity = '0.5';

        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshot`);
        const data = await response.json();

        if (data.image) {
            // 创建新图片对象以预加载
            const newImage = new Image();
            newImage.onload = function () {
                screenshot.src = this.src;
                screenshot.style.opacity = '1';
                loadingIndicator.style.display = 'none';
                addLog('截图', '刷新成功', 'success');
            };
            newImage.onerror = function () {
                loadingIndicator.style.display = 'none';
                screenshot.style.opacity = '1';
                addLog('截图', '图片加载失败', 'error');
            };
            newImage.src = 'data:image/png;base64,' + data.image;
        } else if (data.error) {
            loadingIndicator.style.display = 'none';
            screenshot.style.opacity = '1';
            addLog('截图', '刷新失败: ' + data.error, 'error');
        }
    } catch (error) {
        const loadingIndicator = document.getElementById('loading-indicator');
        const screenshot = document.getElementById('screenshot');
        loadingIndicator.style.display = 'none';
        screenshot.style.opacity = '1';
        addLog('截图', '网络错误: ' + error.message, 'error');
    }
}

// 开始自动刷新
function startAutoRefresh() {
    if (autoRefreshInterval) {
        addLog('自动刷新', '已经在运行中', 'warning');
        return;
    }

    autoRefreshInterval = setInterval(refreshAllMonitors, 1000); // 改为1秒间隔，与WebSocket频率一致
    addLog('自动刷新', '已启动 (1秒间隔)', 'success');
}

// 停止自动刷新
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        addLog('自动刷新', '已停止', 'info');
    }
}

// 重新连接服务器
async function reconnectServer() {
    addLog('连接', '正在重新连接服务器...', 'info');

    // 关闭现有连接
    if (ws) {
        ws.close();
    }

    // 检查服务器状态
    const serverAvailable = await checkServerStatus();
    if (serverAvailable) {
        connectWebSocket();
        refreshAllMonitors();
    }
}

// 测试网络连接
async function testNetwork() {
    try {
        addLog('网络', '正在测试网络连接...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/test-network`);
        const data = await response.json();

        if (data.network) {
            const statusText = getNetworkStatusText(data.network.status);
            const latency = data.network.latency >= 0 ? `${data.network.latency}ms` : '无响应';
            addLog('网络', `状态: ${statusText}, 延迟: ${latency}`, 'success');
        }
    } catch (error) {
        addLog('网络', '网络测试失败: ' + error.message, 'error');
    }
}

// 测试系统信息
async function testSystemInfo() {
    try {
        addLog('系统', '正在获取系统信息...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/system-info`);
        const data = await response.json();

        if (data.memory && data.cpu && data.disk) {
            let systemInfo = `系统资源信息:\n`;
            systemInfo += `内存: ${data.memory.usage_percent}% (${data.memory.used_gb}GB/${data.memory.total_gb}GB)\n`;
            systemInfo += `CPU: ${data.cpu.usage_percent}% (${data.cpu.count}核心, ${data.cpu.frequency_mhz}MHz)\n`;
            systemInfo += `磁盘: ${data.disk.usage_percent}% (${data.disk.used_gb}GB/${data.disk.total_gb}GB)`;
            addLog('系统', systemInfo, 'success');
        } else if (data.error) {
            addLog('系统', '获取系统信息失败: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('系统', '系统信息测试失败: ' + error.message, 'error');
    }
}

// 全屏查看截图
function toggleFullscreen() {
    const screenshot = document.getElementById('screenshot');

    if (!document.fullscreenElement) {
        // 进入全屏
        if (screenshot.requestFullscreen) {
            screenshot.requestFullscreen();
        } else if (screenshot.webkitRequestFullscreen) {
            screenshot.webkitRequestFullscreen();
        } else if (screenshot.msRequestFullscreen) {
            screenshot.msRequestFullscreen();
        }
        addLog('截图', '进入全屏模式', 'info');
    } else {
        // 退出全屏
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        addLog('截图', '退出全屏模式', 'info');
    }
}

// 获取截图信息
async function getScreenshotInfo() {
    try {
        addLog('截图', '正在获取截图信息...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshot-info`);
        const data = await response.json();

        if (data.virtual_screen) {
            let info = `虚拟屏幕: ${data.virtual_screen.width}x${data.virtual_screen.height} | 主屏幕: ${data.primary_screen.width}x${data.primary_screen.height} | 当前截图: ${data.current_screenshot.width}x${data.current_screenshot.height}`;
            addLog('截图', info, 'success');

            // 显示显示器详细信息
            if (data.monitors && data.monitors.length > 0) {
                addLog('截图', `检测到 ${data.monitor_count} 个显示器:`, 'info');
                data.monitors.forEach(monitor => {
                    const monitorInfo = `显示器 ${monitor.index + 1}${monitor.primary ? ' (主)' : ''}: ${monitor.width}x${monitor.height} 位置(${monitor.left},${monitor.top})`;
                    addLog('截图', monitorInfo, 'info');
                });
            }
        }
    } catch (error) {
        addLog('截图', '获取截图信息失败: ' + error.message, 'error');
    }
}

// 获取显示器配置信息
async function getMonitorsConfig() {
    try {
        addLog('显示器', '正在获取显示器配置信息...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/monitors/config`);
        const data = await response.json();

        if (data.system_info && data.monitors) {
            let configInfo = `系统信息:\n`;
            configInfo += `  显示器数量: ${data.system_info.monitor_count}\n`;
            configInfo += `  虚拟桌面: ${data.system_info.virtual_screen.width}x${data.system_info.virtual_screen.height} 位置(${data.system_info.virtual_screen.left},${data.system_info.virtual_screen.top})\n`;
            configInfo += `  主显示器: ${data.system_info.primary_screen.width}x${data.system_info.primary_screen.height}\n`;
            configInfo += `  检测方法: ${data.detection_method}\n\n`;

            configInfo += `显示器详情:\n`;
            data.monitors.forEach(monitor => {
                configInfo += `  显示器 ${monitor.index + 1}${monitor.primary ? ' (主显示器)' : ''}: \n`;
                configInfo += `    分辨率: ${monitor.width}x${monitor.height}\n`;
                configInfo += `    位置: (${monitor.left}, ${monitor.top})\n`;
                configInfo += `    区域: (${monitor.left}, ${monitor.top}, ${monitor.right}, ${monitor.bottom})\n`;
                configInfo += `    面积: ${monitor.area.toLocaleString()} 像素\n`;
            });

            addLog('显示器', configInfo, 'success');
        } else {
            addLog('显示器', '未获取到显示器配置信息', 'warning');
        }
    } catch (error) {
        addLog('显示器', '获取显示器配置信息失败: ' + error.message, 'error');
    }
}

// 刷新所有显示器截图
async function refreshAllMonitors() {
    try {
        addLog('截图', '正在获取所有显示器截图...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshots/all`);
        const data = await response.json();

        if (data.screenshots) {
            displayMultiMonitors(data.screenshots);
            addLog('截图', `成功获取 ${data.monitor_count} 个显示器截图`, 'success');
        }
    } catch (error) {
        addLog('截图', '获取多显示器截图失败: ' + error.message, 'error');
    }
}

// 显示多显示器截图
function displayMultiMonitors(screenshots) {
    const grid = document.getElementById('monitors-grid');
    grid.innerHTML = '';

    if (!screenshots || screenshots.length === 0) {
        grid.innerHTML = '<div class="monitor-loading"><div class="loading"></div>正在加载显示器信息...</div>';
        return;
    }

    screenshots.forEach((screenshot, index) => {
        const monitorDiv = document.createElement('div');
        monitorDiv.className = `monitor-item ${screenshot.primary ? 'primary' : ''}`;
        monitorDiv.id = `monitor-${screenshot.monitor_index}`;

        // 设置分辨率信息到右上角标签
        const monitorType = screenshot.primary ? '主显示器' : '副显示器';
        monitorDiv.setAttribute('data-resolution', `${monitorType}（${screenshot.width}×${screenshot.height}）`);

        const img = document.createElement('img');
        img.className = 'monitor-image';
        img.src = 'data:image/png;base64,' + screenshot.image;
        img.alt = `${monitorType} ${screenshot.monitor_index + 1}`;

        const controls = document.createElement('div');
        controls.className = 'monitor-controls';
        controls.innerHTML = `
            <button class="monitor-btn monitor-btn-refresh" onclick="refreshSingleMonitor(${screenshot.monitor_index})">
                🔄 刷新
            </button>
            <button class="monitor-btn monitor-btn-fullscreen" onclick="toggleMonitorFullscreen(${screenshot.monitor_index})">
                ⛶ 全屏
            </button>
            <button class="monitor-btn monitor-btn-toggle" id="toggle-btn-${screenshot.monitor_index}" onclick="toggleMonitorImage(${screenshot.monitor_index})">
                📷 收起
            </button>
        `;

        // 添加收起/展开功能
        setTimeout(() => {
            const imgElem = monitorDiv.querySelector('.monitor-image');
            const toggleBtn = controls.querySelector(`#toggle-btn-${screenshot.monitor_index}`);
            if (imgElem && toggleBtn) {
                toggleBtn.dataset.expanded = "true";
                toggleBtn.addEventListener('click', function () {
                    if (toggleBtn.dataset.expanded === "true") {
                        imgElem.style.display = "none";
                        toggleBtn.textContent = "展开";
                        toggleBtn.dataset.expanded = "false";
                    } else {
                        imgElem.style.display = "";
                        toggleBtn.textContent = "收起";
                        toggleBtn.dataset.expanded = "true";
                    }
                });
            }
        }, 0);

        monitorDiv.appendChild(img);
        monitorDiv.appendChild(controls);
        grid.appendChild(monitorDiv);
    });
}

// 刷新单个显示器
async function refreshSingleMonitor(monitorIndex) {
    try {
        const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
        if (!monitorDiv) {
            addLog('截图', `找不到显示器 ${monitorIndex + 1} 的容器`, 'error');
            return;
        }

        // 显示加载状态
        const img = monitorDiv.querySelector('.monitor-image');
        const originalSrc = img.src;
        img.style.opacity = '0.5';

        addLog('截图', `正在刷新显示器 ${monitorIndex + 1}...`, 'info');

        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshot/monitor/${monitorIndex}`);
        const data = await response.json();

        if (data.image) {
            // 创建新图片对象以预加载
            const newImage = new Image();
            newImage.onload = function () {
                img.src = this.src;
                img.style.opacity = '1';

                // 更新时间戳
                const info = monitorDiv.querySelector('.monitor-info');
                info.innerHTML = `
                            <span>更新时间: ${new Date().toLocaleTimeString()}</span>
                        `;

                addLog('截图', `显示器 ${monitorIndex + 1} 刷新成功`, 'success');
            };
            newImage.onerror = function () {
                img.src = originalSrc;
                img.style.opacity = '1';
                addLog('截图', `显示器 ${monitorIndex + 1} 图片加载失败`, 'error');
            };
            newImage.src = 'data:image/png;base64,' + data.image;
        } else if (data.error) {
            img.src = originalSrc;
            img.style.opacity = '1';
            addLog('截图', `显示器 ${monitorIndex + 1} 刷新失败: ${data.error}`, 'error');
        }
    } catch (error) {
        addLog('截图', `显示器 ${monitorIndex + 1} 刷新失败: ${error.message}`, 'error');
    }
}

// 切换显示器全屏
function toggleMonitorFullscreen(monitorIndex) {
    const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
    if (!monitorDiv) {
        addLog('截图', `找不到显示器 ${monitorIndex + 1} 的容器`, 'error');
        return;
    }

    const img = monitorDiv.querySelector('.monitor-image');
    if (!document.fullscreenElement) {
        // 进入全屏
        if (img.requestFullscreen) {
            img.requestFullscreen();
        } else if (img.webkitRequestFullscreen) {
            img.webkitRequestFullscreen();
        } else if (img.msRequestFullscreen) {
            img.msRequestFullscreen();
        }
        addLog('截图', `进入显示器 ${monitorIndex + 1} 全屏模式`, 'info');
    } else {
        // 退出全屏
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        addLog('截图', `退出显示器 ${monitorIndex + 1} 全屏模式`, 'info');
    }
}

// 调试显示器 (模拟刷新单个显示器)
async function debugMonitor(monitorIndex) {
    try {
        addLog('调试', `正在调试显示器 ${monitorIndex + 1}...`, 'info');
        const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
        if (!monitorDiv) {
            addLog('调试', `找不到显示器 ${monitorIndex + 1} 的容器`, 'error');
            return;
        }

        const img = monitorDiv.querySelector('.monitor-image');
        const originalSrc = img.src;
        img.style.opacity = '0.5';

        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshot/monitor/${monitorIndex}`);
        const data = await response.json();

        if (data.image) {
            const newImage = new Image();
            newImage.onload = function () {
                img.src = this.src;
                img.style.opacity = '1';
                addLog('调试', `显示器 ${monitorIndex + 1} 调试成功`, 'success');
            };
            newImage.onerror = function () {
                img.src = originalSrc;
                img.style.opacity = '1';
                addLog('调试', `显示器 ${monitorIndex + 1} 调试失败: 图片加载失败`, 'error');
            };
            newImage.src = 'data:image/png;base64,' + data.image;
        } else if (data.error) {
            img.src = originalSrc;
            img.style.opacity = '1';
            addLog('调试', `显示器 ${monitorIndex + 1} 调试失败: ${data.error}`, 'error');
        }
    } catch (error) {
        addLog('调试', `显示器 ${monitorIndex + 1} 调试失败: ${error.message}`, 'error');
    }
}

// 强制重新检测显示器
async function forceRedetect() {
    try {
        addLog('显示器', '正在强制重新检测显示器...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/force-redetect`);
        const data = await response.json();

        if (data.message) {
            addLog('显示器', data.message, 'success');

            // 显示重新检测的结果
            if (data.monitors) {
                let redetectInfo = `重新检测结果:\n`;
                data.monitors.forEach(monitor => {
                    redetectInfo += `  显示器 ${monitor.index + 1}${monitor.primary ? ' (主显示器)' : ''}: ${monitor.width}x${monitor.height} 位置(${monitor.left},${monitor.top})\n`;
                });
                addLog('显示器', redetectInfo, 'info');
            }

            // 刷新所有显示器截图
            setTimeout(() => {
                refreshAllMonitors();
            }, 1000);
        } else if (data.error) {
            addLog('显示器', '显示器重新检测失败: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('显示器', '强制重新检测失败: ' + error.message, 'error');
    }
}

// 添加日志
function addLog(source, message, type = 'info') {
    const logContainer = document.getElementById('log-container');
    const timestamp = new Date().toLocaleString('zh-CN', { hour12: false });
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.textContent = `[${timestamp}] [${source}] ${message}`;

    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;

    // 限制日志条目数量
    while (logContainer.children.length > 50) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// 显示通知提示
function showNotification(message, type = 'info', duration = 3000) {
    // 移除现有的通知
    const existingNotification = document.querySelector('.notification-popup');
    if (existingNotification) {
        existingNotification.remove();
    }
    
    // 创建通知元素
    const notification = document.createElement('div');
    notification.className = `notification-popup ${type}`;
    
    // 设置图标和样式
    let icon = 'ℹ️';
    if (type === 'success') icon = '✅';
    else if (type === 'error') icon = '❌';
    else if (type === 'warning') icon = '⚠️';
    
    notification.innerHTML = `
        <div class="notification-content">
            <span class="notification-icon">${icon}</span>
            <span class="notification-message">${message}</span>
            <button class="notification-close" onclick="this.parentElement.parentElement.remove()">×</button>
        </div>
    `;
    
    // 添加到页面
    document.body.appendChild(notification);
    
    // 显示动画
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    // 自动隐藏
    if (duration > 0) {
        setTimeout(() => {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, 300);
        }, duration);
    }
}

// 页面卸载时清理
window.addEventListener('beforeunload', function () {
    if (ws) {
        ws.close();
    }
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

// 监听全屏状态变化
document.addEventListener('fullscreenchange', function () {
    if (!document.fullscreenElement) {
        addLog('截图', '已退出全屏模式', 'info');
    }
});

// 切换显示器图片的收起/展开状态
function toggleMonitorImage(monitorIndex) {
    const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
    if (!monitorDiv) {
        addLog('截图', `找不到显示器 ${monitorIndex + 1} 的容器`, 'error');
        return;
    }

    const img = monitorDiv.querySelector('.monitor-image');
    const toggleBtn = document.getElementById(`toggle-btn-${monitorIndex}`);
    
    if (!img || !toggleBtn) {
        addLog('截图', `显示器 ${monitorIndex + 1} 的元素不完整`, 'error');
        return;
    }

    // 检查当前状态
    const isCollapsed = img.style.display === 'none' || monitorDiv.classList.contains('collapsed');
    
    if (isCollapsed) {
        // 展开：显示图片
        monitorDiv.classList.remove('collapsed');
        img.style.display = 'block';
        img.classList.add('expanding');
        
        // 使用requestAnimationFrame确保动画流畅
        requestAnimationFrame(() => {
            img.classList.remove('expanding');
            img.classList.add('expanded');
            img.style.opacity = '1';
        });
        
        toggleBtn.innerHTML = '📷 收起';
        toggleBtn.classList.remove('collapsed');
        addLog('截图', `展开显示器 ${monitorIndex + 1}`, 'info');
    } else {
        // 收起：隐藏图片
        img.style.opacity = '0';
        img.classList.remove('expanded');
        img.classList.add('expanding');
        
        setTimeout(() => {
            img.style.display = 'none';
            monitorDiv.classList.add('collapsed');
        }, 300);
        
        toggleBtn.innerHTML = '👁️ 展开';
        toggleBtn.classList.add('collapsed');
        addLog('截图', `收起显示器 ${monitorIndex + 1}`, 'info');
    }
}

// ==================== 文件上传功能 ====================

// 文件选择事件监听
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOMContentLoaded event fired'); // Debug log
    
    const fileInput = document.getElementById('fileInput');
    const pathInput = document.getElementById('pathInput');
    
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelection);
    }
    
    if (pathInput) {
        pathInput.addEventListener('change', handlePathSelectionEvent);
    }
    
    // 初始化上传按钮状态
    updateFileSelectionUI();
    
    // 初始化路径选择按钮状态
    updatePathSelectionUI();
    
    // 直接为路径按钮添加点击事件监听器
    const pathBtn = document.getElementById('pathBtn');
    if (pathBtn) {
        console.log('Found pathBtn element, adding click listener'); // Debug log
        pathBtn.addEventListener('click', function(e) {
            console.log('Path button clicked!'); // Debug log
            e.preventDefault();
            e.stopPropagation();
            
            // 总是打开模态框，无论是否已有选择的路径
            openPathModal();
        });
    } else {
        console.error('pathBtn element not found!'); // Debug log
    }
    
    // 自动加载文件列表，无需点击刷新按钮
    loadFileList();
    
    // 添加点击外部关闭模态框的事件监听
    document.addEventListener('click', function(event) {
        const modal = document.getElementById('pathModal');
        if (modal && modal.style.display === 'flex') {
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent && !modalContent.contains(event.target)) {
                closePathModal();
            }
        }
    });
    
    // 添加ESC键关闭模态框的事件监听
    document.addEventListener('keydown', function(event) {
        if (event.key === 'Escape') {
            const modal = document.getElementById('pathModal');
            if (modal && modal.style.display === 'flex') {
                closePathModal();
            }
        }
    });
});

// 处理合并后的文件上传按钮
function handleFileUpload() {
    // 如果没有选择文件，先触发文件选择
    if (selectedFiles.length === 0) {
        document.getElementById('fileInput').click();
        return;
    }
    
    // 如果已经有文件选择，直接上传
    uploadFiles();
}

// 处理文件选择
function handleFileSelection(event) {
    const files = Array.from(event.target.files);
    const oversizedFiles = [];
    
    selectedFiles = files.filter(file => {
        // 检查文件大小 (100MB限制)
        if (file.size > 100 * 1024 * 1024) {
            oversizedFiles.push(file.name);
            return false;
        }
        return true;
    });
    
    // 显示超大文件的警告
    if (oversizedFiles.length > 0) {
        const warningMsg = `文件 ${oversizedFiles.join(', ')} 超过100MB限制，已跳过`;
        addLog('文件上传', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 4000);
    }
    
    updateFileSelectionUI();
}

// 处理路径选择按钮点击 - 现在显示下拉框
// 全局变量用于路径导航
let currentModalPath = '';
let pathHistory = [];

// 打开路径选择模态框
function openPathModal() {
    console.log('openPathModal() called'); // Debug log
    
    const modal = document.getElementById('pathModal');
    console.log('Modal element:', modal); // Debug log
    
    if (!modal) {
        console.error('Modal element not found!');
        return;
    }
    
    console.log('Setting modal display to flex'); // Debug log
    modal.style.display = 'flex';
    
    // 重新显示目标路径元素
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'block';
    }
    
    // 重置路径导航历史
    pathHistory = [];
    console.log('Reset path history:', pathHistory);
    
    console.log('Loading modal path list for current path:', selectedPath); // Debug log
    // 加载当前选中的路径，如果没有则加载根目录
    loadModalPathList(selectedPath || '');
}

// 关闭路径选择模态框
function closePathModal() {
    const modal = document.getElementById('pathModal');
    modal.style.display = 'none';
    
    // 隐藏目标路径元素
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'none';
    }
}

// 加载系统目录列表
async function loadSystemDirectories(path = '') {
    console.log('loadSystemDirectories() called with path:', path);
    
    try {
        const pathList = document.getElementById('modalPathList');
        const currentPathElement = document.getElementById('modalCurrentPath');
        const upButton = document.getElementById('upButton');
        
        // 保存当前选中的路径信息，用于在加载后恢复选中状态
        const currentSelectedPath = selectedPath;
        const currentSelectedPathName = selectedPathName;
        
        // 显示加载状态
        pathList.innerHTML = '<div class="loading-placeholder">正在加载系统目录列表...</div>';
        
        // 构建请求URL
        const url = path ? `${getServerBaseUrl()}/system-directories?path=${encodeURIComponent(path)}` : `${getServerBaseUrl()}/system-directories`;
        // console.log('DEBUG: Requesting URL:', url);
        // console.log('DEBUG: Original path:', path);
        // console.log('DEBUG: Encoded path:', encodeURIComponent(path));
        
        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 更新当前路径显示
        currentModalPath = data.current_path;
        const displayPath = data.current_path ? `📂 ${data.current_path}` : '📂 系统根目录';
        currentPathElement.innerHTML = `<span>${displayPath}</span>`;
        
        // 更新上级目录按钮
        console.log('System path navigation debug:', {
            can_go_up: data.can_go_up,
            current_path: data.current_path
        });
        
        if (data.can_go_up) {
            upButton.style.display = 'inline-block';
            upButton.title = '返回上级目录';
            upButton.innerText = '⬆️ 上级目录';
            upButton.onclick = function() {
                loadSystemDirectories(data.parent_path);
            };
            console.log('Showing up button for system directories');
        } else if (!data.current_path || data.current_path === '') {
            // 在根目录时显示"跳至根目录"按钮
            upButton.style.display = 'inline-block';
            upButton.title = '跳至根目录';
            upButton.innerText = '🏠 跳至根目录';
            upButton.onclick = function() {
                loadSystemDirectories('');
            };
            console.log('Showing return to root button');
        } else {
            upButton.style.display = 'none';
            console.log('Hiding up button for system root');
        }
        
        // 填充路径列表
        populateSystemPathList(data.items, currentSelectedPath);
        
    } catch (error) {
        console.error('加载系统目录列表失败:', error);
        
        const pathList = document.getElementById('modalPathList');
        let errorMessage = error.message;
        
        // 如果是网络错误，提供更友好的提示
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage = '无法连接到服务器，请确保服务器正在运行';
        }
        
        pathList.innerHTML = `
            <div class="loading-placeholder" style="color: #dc3545;">
                加载失败: ${errorMessage}
            </div>
        `;
        
        showNotification('加载系统目录列表失败: ' + errorMessage, 'error', 3000);
        addLog('路径选择', '加载系统目录列表失败: ' + errorMessage, 'error');
    }
}

// 填充系统路径列表
function populateSystemPathList(items, currentSelectedPath) {
    const pathList = document.getElementById('modalPathList');
    
    if (!items || items.length === 0) {
        pathList.innerHTML = '<div class="empty-placeholder">当前目录下无文件夹</div>';
        return;
    }
    
    let html = '';
    items.forEach(item => {
        // 根据类型选择不同的图标
        let icon = '📁'; // 默认文件夹图标
        if (item.type === 'drive') {
            icon = '💾'; // 盘符图标
        }
        
        html += `
            <div class="path-item" 
                 onclick="selectSystemPathItem(this, '${item.path}', '${item.name}')" 
                 ondblclick="navigateToSystemPath('${item.path}')"
                 title="单击选择，双击进入: ${item.name}">
                <div class="path-name">
                    ${item.name}
                </div>
                <div class="file-count">${item.file_count || 0}</div>
            </div>
        `;
    });
    
    pathList.innerHTML = html;
    
    // 恢复选中状态
    if (currentSelectedPath && currentSelectedPath.trim() !== '') {
        const pathItems = pathList.querySelectorAll('.path-item');
        pathItems.forEach(item => {
            try {
                const itemPath = item.getAttribute('onclick').match(/'([^']+)'/)[1];
                if (itemPath === currentSelectedPath) {
                    item.classList.add('selected');
                }
            } catch (e) {
                // 忽略解析错误
            }
        });
    }
}

// 选中系统路径项
function selectSystemPathItem(element, path, name) {
    // 移除所有其他项的选中状态
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });
    
    // 添加当前项的选中状态
    element.classList.add('selected');
    
    // 存储选中的路径信息
    selectedPath = path;
    selectedPathName = name;
    
    // 更新路径选择UI
    updatePathSelectionUI();
}

// 导航到系统路径
function navigateToSystemPath(path) {
    // console.log('navigateToSystemPath called with path:', path);
    loadSystemDirectories(path);
}

// 加载模态框路径列表
async function loadModalPathList(path = '') {
    console.log('loadModalPathList() called with path:', path); // Debug log
    
    try {
        const pathList = document.getElementById('modalPathList');
        const currentPathElement = document.getElementById('modalCurrentPath');
        const upButton = document.getElementById('upButton');
        
        // 保存当前选中的路径信息，用于在加载后恢复选中状态
        const currentSelectedPath = selectedPath;
        const currentSelectedPathName = selectedPathName;
        
        // 显示加载状态
        pathList.innerHTML = '<div class="loading-placeholder">正在加载目录列表...</div>';
        
        // 构建请求URL
        const url = path ? `${getServerBaseUrl()}/directories?path=${encodeURIComponent(path)}` : `${getServerBaseUrl()}/directories`;
        if (path === '') {
            console.log('path is empty');
            upButton.style.display = 'inline-block';
            upButton.innerText = '🏠 跳至根目录';
            upButton.onclick = function() {
                loadSystemDirectories('');
            };
        }

        const response = await fetch(url);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        // 更新当前路径显示
        currentModalPath = data.current_path;
        const displayPath = data.current_path ? `📂 Downloads/${data.current_path}` : '📂 Downloads';
        currentPathElement.innerHTML = `<span>${displayPath}</span>`;
        
        // 更新上级目录按钮 - 显示逻辑改进
        console.log('Path navigation debug:', {
            can_go_up: data.can_go_up,
            pathHistory_length: pathHistory.length,
            current_path: data.current_path,
            pathHistory: pathHistory
        });
        
        if (data.can_go_up || pathHistory.length > 0) {
            upButton.style.display = 'inline-block';
            upButton.title = '返回上级目录';
            console.log('Showing up button');
        } else {
            // console.log(data.items);
        }
        
        // 填充路径列表
        populateModalPathList(data.items, currentSelectedPath);
        
    } catch (error) {
        console.error('加载路径列表失败:', error);
        
        const pathList = document.getElementById('modalPathList');
        let errorMessage = error.message;
        
        // 如果是网络错误，提供更友好的提示
        if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage = '无法连接到服务器，请确保服务器正在运行';
        }
        
        pathList.innerHTML = `
            <div class="loading-placeholder" style="color: #dc3545;">
                加载失败: ${errorMessage}
            </div>
        `;
        
        showNotification('加载路径列表失败: ' + errorMessage, 'error', 3000);
        addLog('路径选择', '加载路径列表失败: ' + errorMessage, 'error');
    }
}

// 填充模态框路径列表
function populateModalPathList(items, currentSelectedPath) {
    const pathList = document.getElementById('modalPathList');
    
    if (!items || items.length === 0) {
        pathList.innerHTML = '<div class="empty-placeholder">当前目录下无文件夹</div>';
        return;
    }
    
    let html = '';
    items.forEach(item => {
        // 使用服务器返回的 path，它已经包含了正确的相对路径
        const itemPath = item.path || (currentModalPath ? `${currentModalPath}/${item.name}` : item.name);
        html += `
            <div class="path-item" 
                 onclick="selectModalPathItem(this, '${itemPath}', '${item.name}')" 
                 ondblclick="navigateToPath('${itemPath}')"
                 title="单击选择，双击进入: ${item.name}">
                <div class="path-name">
                    ${item.name}
                </div>
                <div class="file-count">${item.file_count || 0}</div>
            </div>
        `;
    });
    
    pathList.innerHTML = html;
    
    // 恢复选中状态
    if (currentSelectedPath && currentSelectedPath.trim() !== '') {
        const pathItems = pathList.querySelectorAll('.path-item');
        pathItems.forEach(item => {
            try {
                const itemPath = item.getAttribute('onclick').match(/'([^']+)'/)[1];
                if (itemPath === currentSelectedPath) {
                    item.classList.add('selected');
                }
            } catch (e) {
                // 忽略解析错误
            }
        });
    }
}

// 选中模态框路径项
function selectModalPathItem(element, path, name) {
    // 移除所有其他项的选中状态
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });
    
    // 添加当前项的选中状态
    element.classList.add('selected');
    
    // 存储选中的路径信息
    selectedPath = path;
    selectedPathName = name;
    
    // 更新路径选择UI
    updatePathSelectionUI();
}

// 导航到指定路径
function navigateToPath(path) {
    console.log('Navigating to path:', path);
    // 保存当前路径到历史记录
    if (currentModalPath !== '') {
        pathHistory.push(currentModalPath);
    }
    loadModalPathList(path);
}

// 导航到上级目录
function navigateUp() {
    if (pathHistory.length > 0) {
        const parentPath = pathHistory.pop();
        console.log('Navigating up to:', parentPath);
        loadModalPathList(parentPath);
    } else {
        // 如果没有历史记录，直接导航到根目录
        console.log('Navigating to root directory');
        loadModalPathList('');
    }
}

// 刷新路径列表
function refreshPathList() {
    console.log('Refreshing path list for:', currentModalPath);
    loadModalPathList(currentModalPath);
}

// 选择当前路径并关闭模态框
function selectCurrentPath() {
    console.log('Selecting current path:', currentModalPath);
    console.log('Currently selected path:', selectedPath);
    
    // 如果用户已经选中了某个路径，使用选中的路径；否则使用当前浏览的路径
    const finalSelectedPath = selectedPath || currentModalPath || '';
    
    // 设置选中的路径
    selectedPath = finalSelectedPath;
    
    // 更新UI
    updatePathSelectionUI();
    
    // 隐藏目标路径元素
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'none';
    }
    
    // 关闭模态框
    closePathModal();
    
    // 显示成功消息
    let pathDisplay;
    if (selectedPath && (selectedPath.startsWith('/') || selectedPath.startsWith('C:\\'))) {
        // 系统路径
        pathDisplay = selectedPath;
    } else {
        // Downloads路径
        pathDisplay = selectedPath ? `Downloads/${selectedPath}` : 'Downloads';
    }
    const successMsg = `已选择路径: ${pathDisplay}`;
    addLog('路径选择', successMsg, 'info');
    showNotification(successMsg, 'info', 3000);
    
    // 自动刷新文件列表到选中的路径
    loadFileList();
}

// 处理路径选择事件 (保留用于文件选择的情况)
function handlePathSelectionEvent(event) {
    const file = event.target.files[0];
    
    if (!file) {
        return;
    }
    
    // 获取文件名作为路径提示
    const fileName = file.name;
    
    // 使用prompt让用户确认或修改路径
    const customPath = prompt(`检测到文件: ${fileName}\n请输入目标路径 (例如: Documents/MyFiles 或留空使用默认Downloads目录):`);
    
    if (customPath !== null) { // 用户点击了确定
        if (customPath.trim() === '') {
            // 用户输入了空路径，清除选择
            clearSelectedPath();
        } else {
            // 设置选中的路径
            selectedPath = customPath.trim();
            
            // 更新UI显示
            updatePathSelectionUI();
            
            // 显示成功消息
            const successMsg = `已设置目标路径: ${selectedPath}`;
            addLog('路径选择', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);
            
            // 自动刷新文件列表
            loadFileList();
        }
    }
    
    // 清除文件选择，避免影响后续操作
    event.target.value = '';
}

// 更新路径选择UI
function updatePathSelectionUI() {
    console.log('updatePathSelectionUI() called'); // Debug log
    
    const pathInfo = document.getElementById('pathInfo');
    const currentPath = document.getElementById('currentPath');
    const pathBtn = document.getElementById('pathBtn');
    
    console.log('pathBtn element:', pathBtn); // Debug log
    
    if (selectedPath) {
        pathInfo.style.display = 'block';
        
        // 显示路径信息
        let displayPath;
        if (selectedPath.startsWith('/') || selectedPath.startsWith('C:\\')) {
            // 系统路径
            displayPath = selectedPath;
            pathBtn.innerHTML = '📁 系统路径';
            pathBtn.style.background = 'linear-gradient(135deg, #ffc107 0%, #fd7e14 100%)';
        } else {
            // Downloads路径
            displayPath = selectedPath ? `Downloads/${selectedPath}` : 'Downloads';
            pathBtn.innerHTML = '已选路径';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        }
        
        currentPath.textContent = displayPath;
    } else {
        pathInfo.style.display = 'none';
        pathBtn.innerHTML = '设置路径';
        pathBtn.style.background = '';
    }
}

// 清除选中的路径
function clearSelectedPath() {
    selectedPath = null;
    selectedPathName = null;
    
    // 清除所有路径项的选中状态
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });
    
    updatePathSelectionUI();
    
    // 隐藏目标路径元素
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'none';
    }
    
    const successMsg = '已清除路径设置，返回默认Downloads目录';
    addLog('路径选择', successMsg, 'info');
    showNotification(successMsg, 'info', 3000);
    
    // 自动刷新文件列表
    loadFileList();
}

// 删除选中的文件
function removeSelectedFile(fileIndex) {
    if (fileIndex >= 0 && fileIndex < selectedFiles.length) {
        const removedFile = selectedFiles[fileIndex];
        selectedFiles.splice(fileIndex, 1);
        
        // 显示删除成功消息
        const successMsg = `已从上传列表中移除: ${removedFile.name}`;
        addLog('文件管理', successMsg, 'info');
        showNotification(successMsg, 'info', 2000);
        
        // 更新UI
        updateFileSelectionUI();
    }
}

// 更新文件选择UI
function updateFileSelectionUI() {
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadInfo = document.getElementById('uploadInfo');
    
    if (selectedFiles.length > 0) {
        uploadBtn.disabled = false;
        uploadInfo.style.display = 'block';
        
        // 创建文件列表HTML
        let fileListHTML = `<div style="margin-bottom: 8px;"><span style="font-weight: bold;">已选择 ${selectedFiles.length} 个文件:</span></div>`;
        
        selectedFiles.forEach((file, index) => {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            fileListHTML += `
                <div class="selected-file-item">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-size">(${sizeMB}MB)</div>
                    <button 
                        class="delete-btn"
                        onclick="removeSelectedFile(${index})" 
                        title="删除此文件"
                    >
                        ✕
                    </button>
                </div>
            `;
        });
        
        uploadInfo.innerHTML = fileListHTML;
        
        // 更新按钮文本，表示可以上传
        uploadBtn.innerHTML = '⬆️ 上传';
    } else {
        uploadBtn.disabled = false; // 按钮不再禁用，而是用于选择文件
        uploadInfo.style.display = 'none';
        
        // 更新按钮文本，表示可以选择文件
        uploadBtn.innerHTML = '文件上传';
    }
}

// 上传文件
async function uploadFiles() {
    if (selectedFiles.length === 0) {
        const warningMsg = '没有选择文件';
        addLog('文件上传', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 3000);
        return;
    }
    
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');
    
    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '⏳ 上传中...';
        uploadProgress.style.display = 'block';
        
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
        // 如果有选择的文件夹，添加到请求中
        if (selectedPath) {
            formData.append('folder_path', selectedPath);
        }
        
        const xhr = new XMLHttpRequest();
        
        // 监听上传进度
        xhr.upload.addEventListener('progress', function(event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressFill.style.width = percentComplete + '%';
                progressText.textContent = Math.round(percentComplete) + '%';
            }
        });
        
        // 监听上传完成
        xhr.addEventListener('load', function() {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    addLog('文件上传', response.message, 'success');
                    showNotification(response.message, 'success', 5000);
                    
                    // 清空选择
                    selectedFiles = [];
                    document.getElementById('fileInput').value = '';
                    updateFileSelectionUI();
                    
                    // 刷新文件列表
                    loadFileList();
                    
                } catch (error) {
                    const errorMsg = '解析响应失败: ' + error.message;
                    addLog('文件上传', errorMsg, 'error');
                    showNotification(errorMsg, 'error', 5000);
                }
            } else {
                const errorMsg = '上传失败: HTTP ' + xhr.status;
                addLog('文件上传', errorMsg, 'error');
                showNotification(errorMsg, 'error', 5000);
            }
            
            // 重置UI
            uploadProgress.style.display = 'none';
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
            updateFileSelectionUI();
        });
        
        // 监听上传错误
        xhr.addEventListener('error', function() {
            const errorMsg = '网络错误，上传失败';
            addLog('文件上传', errorMsg, 'error');
            showNotification(errorMsg, 'error', 5000);
            uploadProgress.style.display = 'none';
            updateFileSelectionUI();
        });
        
        // 发送请求
        xhr.open('POST', getServerBaseUrl() + '/upload/multiple');
        xhr.send(formData);
        
    } catch (error) {
        const errorMsg = '上传失败: ' + error.message;
        addLog('文件上传', errorMsg, 'error');
        showNotification(errorMsg, 'error', 5000);
        uploadProgress.style.display = 'none';
        updateFileSelectionUI();
    }
}

// 加载文件列表
async function loadFileList() {
    const fileList = document.getElementById('fileList');
    
    try {
        fileList.innerHTML = '<div class="file-list-placeholder">加载中...</div>';
        
        // 构建请求URL，包含文件夹路径参数
        let url = getServerBaseUrl() + '/files';
        if (selectedPath) {
            url += `?folder=${encodeURIComponent(selectedPath)}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.files && data.files.length > 0) {
            fileList.innerHTML = '';
            
            // 显示当前文件夹信息
            const folderHeader = document.createElement('div');
            folderHeader.style.cssText = 'padding: 8px; background: #e9ecef; border-radius: 4px; margin-bottom: 8px; font-size: 12px; color: #495057;';
            
            // 构建完整的文件夹路径显示
            let folderDisplay;
            if (data.current_folder && data.current_folder !== 'Downloads') {
                folderDisplay = `Downloads/${data.current_folder}`;
            } else {
                folderDisplay = 'Downloads';
            }
            
            folderHeader.innerHTML = `📁 当前文件夹: ${folderDisplay} (${data.files.length} 个文件)`;
            fileList.appendChild(folderHeader);
            
            data.files.forEach(file => {
                const fileItem = createFileItem(file);
                fileList.appendChild(fileItem);
            });
            
            addLog('文件管理', `已加载 ${data.files.length} 个文件`, 'info');
        } else {
            // 构建完整的文件夹路径显示
            let folderDisplay;
            if (data.current_folder && data.current_folder !== 'Downloads') {
                folderDisplay = `Downloads/${data.current_folder}`;
            } else {
                folderDisplay = 'Downloads';
            }
            fileList.innerHTML = `<div class="file-list-placeholder">📁 ${folderDisplay} 文件夹中暂无文件</div>`;
        }
        
    } catch (error) {
        fileList.innerHTML = '<div class="file-list-placeholder">加载失败: ' + error.message + '</div>';
        addLog('文件管理', '加载文件列表失败: ' + error.message, 'error');
    }
}

// 创建文件项
function createFileItem(file) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    
    const uploadTime = new Date(file.upload_time).toLocaleString('zh-CN', { hour12: false });
    
    // 检查是否是系统路径
    const isSystemPath = selectedPath && (selectedPath.startsWith('/') || selectedPath.startsWith('C:\\'));
    
    let actionButtons = '';
    if (!isSystemPath) {
        actionButtons = `
            <button class="file-btn file-btn-download" onclick="downloadFile('${file.filename}')" title="下载">
                📥
            </button>
            <button class="file-btn file-btn-delete" onclick="deleteFile('${file.filename}')" title="删除">
                🗑️
            </button>
        `;
    } else {
        actionButtons = `
            <span style="color: #6c757d; font-size: 12px;">系统文件</span>
        `;
    }
    
    fileItem.innerHTML = `
        <div class="file-info">
            <div class="file-name">${file.filename}</div>
            <div class="file-details">
                <span>大小: ${file.size_mb}MB</span>
                <span>日期: ${uploadTime}</span>
            </div>
        </div>
        <div class="file-actions">
            ${actionButtons}
        </div>
    `;
    
    return fileItem;
}

// 下载文件
async function downloadFile(filename) {
    try {
        // 构建请求URL，包含文件夹路径参数
        let url = getServerBaseUrl() + `/files/${filename}`;
        if (selectedPath) {
            url += `?folder=${encodeURIComponent(selectedPath)}`;
        }
        
        const response = await fetch(url);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            const successMsg = `文件 ${filename} 下载成功`;
            addLog('文件管理', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);
        } else {
            const errorMsg = `下载文件 ${filename} 失败: HTTP ${response.status}`;
            addLog('文件管理', errorMsg, 'error');
            showNotification(errorMsg, 'error', 5000);
        }
    } catch (error) {
        const errorMsg = `下载文件 ${filename} 失败: ${error.message}`;
        addLog('文件管理', errorMsg, 'error');
        showNotification(errorMsg, 'error', 5000);
    }
}

// 删除文件
async function deleteFile(filename) {
    if (!confirm(`确定要删除文件 ${filename} 吗？`)) {
        return;
    }
    
    try {
        // 构建请求URL，包含文件夹路径参数
        let url = getServerBaseUrl() + `/files/${filename}`;
        if (selectedPath) {
            url += `?folder=${encodeURIComponent(selectedPath)}`;
        }
        
        const response = await fetch(url, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            const data = await response.json();
            addLog('文件管理', data.message, 'success');
            showNotification(data.message, 'success', 3000);
            
            // 刷新文件列表
            loadFileList();
        } else {
            const errorData = await response.json();
            const errorMsg = `删除文件失败: ${errorData.detail}`;
            addLog('文件管理', errorMsg, 'error');
            showNotification(errorMsg, 'error', 5000);
        }
    } catch (error) {
        const errorMsg = `删除文件失败: ${error.message}`;
        addLog('文件管理', errorMsg, 'error');
        showNotification(errorMsg, 'error', 5000);
    }
}