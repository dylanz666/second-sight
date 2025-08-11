// 核心模块 - 全局变量和基础功能

// 全局变量
let ws = null;
let autoRefreshInterval = null;
let isConnected = false;

// 跟踪被收起的显示器
let collapsedMonitors = new Set();
let totalMonitorCount = 0; // 总显示器数量
let autoCollapseInitialized = false; // 是否已执行过自动收起

// 文件管理相关变量
let selectedFiles = []; // 当前选择的文件列表
let selectedPath = null; // 当前选择的目标路径
let selectedPathName = null; // 当前选择的路径名称
let lastSelectedPath = null; // 备份最后选择的路径，用于调试

// 模态框状态保存变量
let modalOriginalPath = null; // 打开模态框时的原始路径
let modalOriginalPathName = null; // 打开模态框时的原始路径名称
let modalOriginalCurrentPath = null; // 打开模态框时的原始currentModalPath值

// 趋势图数据管理
let memoryTrendData = [];
let cpuTrendData = [];
let networkLatencyTrendData = [];
const MAX_TREND_POINTS = 20;
let lastSystemUpdateTime = 0;
const SYSTEM_UPDATE_INTERVAL = 5000; // 5秒更新间隔

// 全局变量用于路径导航
let currentModalPath = '';
let pathHistory = [];

// 检查是否所有显示器都被收起
function areAllMonitorsCollapsed() {
    return collapsedMonitors.size === totalMonitorCount && totalMonitorCount > 0;
}

// 自动收起非主显示器
function autoCollapseNonPrimaryMonitors(screenshots) {
    if (!screenshots || screenshots.length <= 1) {
        return; // 只有一个显示器或没有显示器时不需要处理
    }

    // 检查是否已经初始化过（避免重复收起）
    if (autoCollapseInitialized) {
        return; // 已经执行过自动收起，避免重复执行
    }

    // 找到主显示器
    const primaryMonitor = screenshots.find(screenshot => screenshot.primary);
    if (!primaryMonitor) {
        return; // 没有找到主显示器
    }

    // 收起所有非主显示器
    screenshots.forEach(screenshot => {
        if (!screenshot.primary) {
            collapsedMonitors.add(screenshot.monitor_index);
        }
    });

    // 标记已执行过自动收起
    autoCollapseInitialized = true;
    
    addLog('系统', `检测到 ${screenshots.length} 个显示器，已自动收起 ${screenshots.length - 1} 个副显示器`, 'info');
    
    // 延迟同步到后端，避免影响当前的显示逻辑
    setTimeout(() => {
        syncCollapsedMonitorsToBackend();
    }, 500);
}

// 检测运行环境
function detectEnvironment() {
    const isFileProtocol = window.location.protocol === 'file:';
    const isLocalhost = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';

    if (isFileProtocol) {
        return 'file';
    } else if (isLocalhost) {
        return 'localhost';
    } else {
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

// 同步被收起的显示器状态到后端
async function syncCollapsedMonitorsToBackend() {
    try {
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/collapsed-monitors`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                collapsed_monitors: Array.from(collapsedMonitors)
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            addLog('系统', `已同步收起状态到后端: ${data.collapsed_monitors.length} 个显示器`, 'info');
        } else {
            addLog('系统', '同步收起状态到后端失败', 'error');
        }
    } catch (error) {
        addLog('系统', `同步收起状态到后端出错: ${error.message}`, 'error');
    }
}

// 重置所有被收起的显示器状态
function resetCollapsedMonitors() {
    collapsedMonitors.clear();
    autoCollapseInitialized = false; // 重置自动收起标志，允许重新执行自动收起
    // 同步到后端
    syncCollapsedMonitorsToBackend();
    addLog('系统', '已重置所有显示器收起状态', 'info');
    
    // 如果当前显示的是占位符，则重新获取截图
    if (totalMonitorCount > 0) {
        setTimeout(() => {
            refreshAllMonitors();
        }, 100);
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