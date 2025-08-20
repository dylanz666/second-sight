// UI Utility Module - UI-related functions such as logs, notifications, etc.

// Add log entry
function addLog(source, message, type = 'info') {
    const logContainer = document.getElementById('log-container');
    const timestamp = new Date().toLocaleString('en-US', { hour12: false });
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.textContent = `[${timestamp}] [${source}] ${message}`;

    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;

    // Limit number of log entries
    while (logContainer.children.length > 50) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// Show notification prompt
function showNotification(message, type = 'info', duration = 3000) {
    // Remove existing notification
    const existingNotification = document.querySelector('.notification-popup');
    if (existingNotification) {
        existingNotification.remove();
    }

    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification-popup ${type}`;

    // Set icon and style
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

    // Add to page
    document.body.appendChild(notification);

    // Show animation
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);

    // Auto-hide
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

// Unified function to update modal path display
function updateModalPathDisplay(path) {
    const pathInput = document.getElementById('modalCurrentPathInput');

    let displayText = '';
    if (path && path !== '') {
        // Check if it's a system path
        const isSystemPath = path.startsWith('/') || /^[A-Z]:\\/.test(path) || path === 'My Computer';
        if (isSystemPath) {
            displayText = `📂 ${path}`;
        } else {
            // Downloads path
            displayText = `📂 Downloads\\${path}`;
        }
    } else {
        // When no path is selected, default to showing Downloads directory
        displayText = `📂 Downloads`;
    }

    // Update input box value
    if (pathInput) {
        pathInput.value = displayText;

        // Ensure event listeners remain effective
        setupPathInputEventListeners();
    }
}

// Show modal loading state
function showModalLoading() {
    const loadingOverlay = document.getElementById('modalLoadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

// Hide modal loading state
function hideModalLoading() {
    const loadingOverlay = document.getElementById('modalLoadingOverlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

// Set up fullscreen state listener
function setupFullscreenListener() {
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    document.addEventListener('mozfullscreenchange', handleFullscreenChange);
    document.addEventListener('MSFullscreenChange', handleFullscreenChange);
}

// Handle fullscreen state changes
function handleFullscreenChange() {
    if (!document.fullscreenElement &&
        !document.webkitFullscreenElement &&
        !document.mozFullScreenElement &&
        !document.msFullscreenElement) {
        addLog('Screenshot', 'Exited fullscreen mode', 'info');
    }
}

// View screenshot in fullscreen
function toggleFullscreen() {
    const screenshot = document.getElementById('screenshot');

    if (!document.fullscreenElement) {
        // Enter fullscreen
        if (screenshot.requestFullscreen) {
            screenshot.requestFullscreen();
        } else if (screenshot.webkitRequestFullscreen) {
            screenshot.webkitRequestFullscreen();
        } else if (screenshot.msRequestFullscreen) {
            screenshot.msRequestFullscreen();
        }
        addLog('Screenshot', 'Entered fullscreen mode', 'info');
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        addLog('Screenshot', 'Exited fullscreen mode', 'info');
    }
}