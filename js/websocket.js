// WebSocket模块 - 连接和状态更新功能

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