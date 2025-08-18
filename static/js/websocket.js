// WebSocket Module - Connection and status update functionality

// WebSocket connection
function connectWebSocket() {
    const wsUrl = getWebSocketUrl();

    addLog('Connection', `Attempting to connect to: ${wsUrl}`, 'info');

    try {
        ws = new WebSocket(wsUrl);

        ws.onopen = function () {
            isConnected = true;
            updateConnectionStatus(true);
            addLog('Connection', 'WebSocket connection successful', 'success');
        };

        ws.onmessage = function (event) {
            try {
                const data = JSON.parse(event.data);
                updateStatus(data);
            } catch (e) {
                addLog('Connection', 'Data parsing error: ' + e.message, 'error');
            }
        };

        ws.onclose = function () {
            isConnected = false;
            updateConnectionStatus(false);
            addLog('Connection', 'WebSocket connection disconnected', 'warning');

            // Attempt reconnection
            setTimeout(connectWebSocket, 3000);
        };

        ws.onerror = function (error) {
            addLog('Connection', 'WebSocket connection error: ' + (error.message || 'Unknown error'), 'error');
        };
    } catch (error) {
        addLog('Connection', 'Failed to create connection: ' + error.message, 'error');
    }
}

// Update connection status
function updateConnectionStatus(connected) {
    const statusElement = document.getElementById('server-status');
    const indicator = statusElement.querySelector('.connection-indicator');

    if (connected) {
        indicator.className = 'connection-indicator connected';
        statusElement.innerHTML = '<span class="connection-indicator connected"></span>Connected';
    } else {
        indicator.className = 'connection-indicator disconnected';
        statusElement.innerHTML = '<span class="connection-indicator disconnected"></span>Disconnected';
    }
}

// Network status mapping
function getNetworkStatusText(status) {
    const statusMap = {
        'excellent': 'Excellent',
        'good': 'Good',
        'fair': 'Fair',
        'poor': 'Poor',
        'disconnected': 'Disconnected',
        'unknown': 'Unknown'
    };
    return statusMap[status] || status;
}

// Get network status color
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

// Update status information
function updateStatus(data) {
    if (data.type === 'status') {
        document.getElementById('last-update').textContent = new Date(data.timestamp).toLocaleTimeString();

        // Get real memory, CPU and disk usage from server
        const memoryUsage = typeof data.memory_usage !== 'undefined' ? data.memory_usage : '-';
        const cpuUsage = typeof data.cpu_usage !== 'undefined' ? data.cpu_usage : '-';
        const diskUsage = typeof data.disk_usage !== 'undefined' ? data.disk_usage : '-';

        document.getElementById('status-memory-usage').textContent = memoryUsage + '%';
        document.getElementById('status-cpu-usage').textContent = cpuUsage + '%';
        document.getElementById('status-disk-usage').textContent = diskUsage + '%';

        // Add memory and CPU usage data points to trend chart (update every 5 seconds)
        const currentTime = Date.now();
        if (currentTime - lastSystemUpdateTime >= SYSTEM_UPDATE_INTERVAL) {
            if (typeof data.memory_usage === 'number') {
                addMemoryDataPoint(data.memory_usage);
            }

            if (typeof data.cpu_usage === 'number') {
                addCpuDataPoint(data.cpu_usage);
            }

            // Update last update time
            lastSystemUpdateTime = currentTime;
        }

        // Update real network status
        if (data.network) {
            const networkStatusElement = document.getElementById('status-network-status');
            const networkLatencyElement = document.getElementById('status-network-latency');

            const statusText = getNetworkStatusText(data.network.status);
            const statusColor = getNetworkStatusColor(data.network.status);

            networkStatusElement.textContent = statusText;
            networkStatusElement.style.color = statusColor;

            if (data.network.latency >= 0) {
                networkLatencyElement.textContent = data.network.latency + 'ms';
                // Add network latency data point to trend chart
                addNetworkLatencyDataPoint(data.network.latency);
            } else {
                networkLatencyElement.textContent = '-';
            }
        }
    }
}

// Reconnect to server
async function reconnectServer() {
    addLog('Connection', 'Reconnecting to server...', 'info');

    // Close existing connection
    if (ws) {
        ws.close();
    }

    // Check server status
    const serverAvailable = await checkServerStatus();
    if (serverAvailable) {
        connectWebSocket();
        refreshAllMonitors();
    }
}

// Test network connection
async function testNetwork() {
    try {
        addLog('Network', 'Testing network connection...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/test-network`);
        const data = await response.json();

        if (data.network) {
            const statusText = getNetworkStatusText(data.network.status);
            const latency = data.network.latency >= 0 ? `${data.network.latency}ms` : 'No response';
            addLog('Network', `Status: ${statusText}, Latency: ${latency}`, 'success');
        }
    } catch (error) {
        addLog('Network', 'Network test failed: ' + error.message, 'error');
    }
}

// Test system information
async function testSystemInfo() {
    try {
        addLog('System', 'Retrieving system information...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/system-info`);
        const data = await response.json();

        if (data.memory && data.cpu && data.disk) {
            let systemInfo = `System resource information:\n`;
            systemInfo += `Memory: ${data.memory.usage_percent}% (${data.memory.used_gb}GB/${data.memory.total_gb}GB)\n`;
            systemInfo += `CPU: ${data.cpu.usage_percent}% (${data.cpu.count} cores, ${data.cpu.frequency_mhz}MHz)\n`;
            systemInfo += `Disk: ${data.disk.usage_percent}% (${data.disk.used_gb}GB/${data.disk.total_gb}GB)`;
            addLog('System', systemInfo, 'success');
        } else if (data.error) {
            addLog('System', 'Failed to retrieve system information: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('System', 'System information test failed: ' + error.message, 'error');
    }
}
