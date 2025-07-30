let ws = null;
let autoRefreshInterval = null;
let isConnected = false;

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
    const timestamp = new Date().toLocaleTimeString();
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

// 全局变量
let selectedFiles = [];

// 文件选择事件监听
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelection);
    }
});

// 处理文件选择
function handleFileSelection(event) {
    const files = Array.from(event.target.files);
    const oversizedFiles = [];
    
    selectedFiles = files.filter(file => {
        // 检查文件大小 (50MB限制)
        if (file.size > 50 * 1024 * 1024) {
            oversizedFiles.push(file.name);
            return false;
        }
        return true;
    });
    
    // 显示超大文件的警告
    if (oversizedFiles.length > 0) {
        const warningMsg = `文件 ${oversizedFiles.join(', ')} 超过50MB限制，已跳过`;
        addLog('文件上传', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 4000);
    }
    
    updateFileSelectionUI();
}

// 更新文件选择UI
function updateFileSelectionUI() {
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadInfo = document.getElementById('uploadInfo');
    const selectedFilesCount = document.getElementById('selectedFilesCount');
    
    if (selectedFiles.length > 0) {
        uploadBtn.disabled = false;
        uploadInfo.style.display = 'block';
        selectedFilesCount.textContent = selectedFiles.length;
        
        // 显示文件信息
        const fileInfoText = selectedFiles.map(file => {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            return `${file.name} (${sizeMB}MB)`;
        }).join(', ');
        
        uploadInfo.innerHTML = `<span id="selectedFilesCount">${selectedFiles.length}</span> 个文件已选择<br><small>${fileInfoText}</small>`;
    } else {
        uploadBtn.disabled = true;
        uploadInfo.style.display = 'none';
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
        uploadBtn.textContent = '⏳ 上传中...';
        uploadProgress.style.display = 'block';
        
        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });
        
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
            uploadBtn.disabled = false;
            uploadBtn.textContent = '⬆️ 上传文件';
            uploadProgress.style.display = 'none';
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
        });
        
        // 监听上传错误
        xhr.addEventListener('error', function() {
            const errorMsg = '网络错误，上传失败';
            addLog('文件上传', errorMsg, 'error');
            showNotification(errorMsg, 'error', 5000);
            uploadBtn.disabled = false;
            uploadBtn.textContent = '⬆️ 上传文件';
            uploadProgress.style.display = 'none';
        });
        
        // 发送请求
        xhr.open('POST', getServerBaseUrl() + '/upload/multiple');
        xhr.send(formData);
        
    } catch (error) {
        const errorMsg = '上传失败: ' + error.message;
        addLog('文件上传', errorMsg, 'error');
        showNotification(errorMsg, 'error', 5000);
        uploadBtn.disabled = false;
        uploadBtn.textContent = '⬆️ 上传文件';
        uploadProgress.style.display = 'none';
    }
}

// 加载文件列表
async function loadFileList() {
    const fileList = document.getElementById('fileList');
    
    try {
        fileList.innerHTML = '<div class="file-list-placeholder">加载中...</div>';
        
        const response = await fetch(getServerBaseUrl() + '/files');
        const data = await response.json();
        
        if (data.files && data.files.length > 0) {
            fileList.innerHTML = '';
            
            data.files.forEach(file => {
                const fileItem = createFileItem(file);
                fileList.appendChild(fileItem);
            });
            
            addLog('文件管理', `已加载 ${data.files.length} 个文件`, 'info');
        } else {
            fileList.innerHTML = '<div class="file-list-placeholder">暂无文件</div>';
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
    
    const uploadTime = new Date(file.upload_time).toLocaleString();
    
    fileItem.innerHTML = `
        <div class="file-info">
            <div class="file-name">${file.filename}</div>
            <div class="file-details">
                <span>大小: ${file.size_mb}MB</span>
                <span>上传: ${uploadTime}</span>
            </div>
        </div>
        <div class="file-actions">
            <button class="file-btn file-btn-download" onclick="downloadFile('${file.filename}')" title="下载">
                📥
            </button>
            <button class="file-btn file-btn-delete" onclick="deleteFile('${file.filename}')" title="删除">
                🗑️
            </button>
        </div>
    `;
    
    return fileItem;
}

// 下载文件
async function downloadFile(filename) {
    try {
        const response = await fetch(getServerBaseUrl() + `/files/${filename}`);
        
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
        const response = await fetch(getServerBaseUrl() + `/files/${filename}`, {
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