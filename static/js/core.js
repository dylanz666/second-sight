// Core Module - Global Variables and Basic Functions

// Global Variables
let ws = null;
let autoRefreshInterval = null;
let isConnected = false;

// Track collapsed monitors
let collapsedMonitors = new Set();
let totalMonitorCount = 0; // Total number of monitors
let autoCollapseInitialized = false; // Whether auto-collapse has been executed

// File management related variables
let selectedFiles = []; // Currently selected file list
let selectedPath = null; // Currently selected target path
let selectedPathName = null; // Currently selected path name
let lastSelectedPath = null; // Backup of the last selected path for debugging

// Modal state saving variables
let modalOriginalPath = null; // Original path when opening the modal
let modalOriginalPathName = null; // Original path name when opening the modal
let modalOriginalCurrentPath = null; // Original currentModalPath value when opening the modal

// Trend chart data management
let memoryTrendData = [];
let cpuTrendData = [];
let networkLatencyTrendData = [];
const MAX_TREND_POINTS = 20;
let lastSystemUpdateTime = 0;
const SYSTEM_UPDATE_INTERVAL = 5000; // 5 seconds update interval

// Global variables for path navigation
let currentModalPath = '';
let pathHistory = [];

// Check if all monitors are collapsed
function areAllMonitorsCollapsed() {
    return collapsedMonitors.size === totalMonitorCount && totalMonitorCount > 0;
}

// Automatically collapse non-primary monitors
function autoCollapseNonPrimaryMonitors(screenshots) {
    if (!screenshots || screenshots.length <= 1) {
        return; // No need to process if there is only one monitor or no monitors
    }

    // Check if it has already been initialized (to avoid repeated collapsing)
    if (autoCollapseInitialized) {
        return; // Auto-collapse has already been executed, avoid repeating
    }

    // Find the primary monitor
    const primaryMonitor = screenshots.find(screenshot => screenshot.primary);
    if (!primaryMonitor) {
        return; // No primary monitor found
    }

    // Collapse all non-primary monitors
    screenshots.forEach(screenshot => {
        if (!screenshot.primary) {
            collapsedMonitors.add(screenshot.monitor_index);
        }
    });

    // Mark that auto-collapse has been executed
    autoCollapseInitialized = true;
    
    addLog('System', `Detected ${screenshots.length} monitors, automatically collapsed ${screenshots.length - 1} secondary monitors`, 'info');
    
    // Delay synchronization to the backend to avoid affecting the current display logic
    setTimeout(() => {
        syncCollapsedMonitorsToBackend();
    }, 500);
}

// Detect the running environment
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

// Get the server base URL
function getServerBaseUrl() {
    const environment = detectEnvironment();

    if (environment === 'file') {
        // File protocol mode, use the default local server address
        return 'http://localhost:8000';
    } else {
        // HTTP protocol mode, use the current domain name
        return `${window.location.protocol}//${window.location.host}`;
    }
}

// Get WebSocket URL
function getWebSocketUrl() {
    const environment = detectEnvironment();

    if (environment === 'file') {
        // File protocol mode, use the default local server WebSocket address
        return 'ws://localhost:8000/ws';
    } else {
        // HTTP protocol mode, choose WebSocket protocol based on the current protocol
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${protocol}//${window.location.host}/ws`;
    }
}

// Check server status
async function checkServerStatus() {
    try {
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/status`);
        const data = await response.json();
        addLog('Connection', 'Server connection is normal', 'success');
        return true;
    } catch (error) {
        addLog('Connection', 'Unable to connect to the server, please ensure the server is running', 'error');
        return false;
    }
}

// Synchronize the collapsed monitor status to the backend
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
            addLog('System', `Collapsed status synchronized to backend: ${data.collapsed_monitors.length} monitors`, 'info');
        } else {
            addLog('System', 'Failed to synchronize collapsed status to backend', 'error');
        }
    } catch (error) {
        addLog('System', `Error synchronizing collapsed status to backend: ${error.message}`, 'error');
    }
}

// Reset all collapsed monitor statuses
function resetCollapsedMonitors() {
    collapsedMonitors.clear();
    autoCollapseInitialized = false; // Reset auto-collapse flag to allow re-execution of auto-collapse
    // Synchronize to backend
    syncCollapsedMonitorsToBackend();
    addLog('System', 'All monitor collapsed statuses have been reset', 'info');
    
    // If the current display is a placeholder, refresh the screenshots
    if (totalMonitorCount > 0) {
        setTimeout(() => {
            refreshAllMonitors();
        }, 100);
    }
}

// Clean up on page unload
window.addEventListener('beforeunload', function () {
    if (ws) {
        ws.close();
    }
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

// Listen for fullscreen state changes
document.addEventListener('fullscreenchange', function () {
    if (!document.fullscreenElement) {
        addLog('Screenshot', 'Exited fullscreen mode', 'info');
    }
});