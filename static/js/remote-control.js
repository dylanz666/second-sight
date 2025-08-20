// ==================== Remote Control Functionality ====================

// Remote control related variables
let isRemoteControlEnabled = false;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;

// Initialize remote control
function initRemoteControl() {
    setupScreenshotClickEvents();
    setupDragEvents();
    window.addLog && window.addLog('Remote Control', 'Remote control functionality initialized', 'info');
}

// Toggle remote control state
function toggleRemoteControl() {
    isRemoteControlEnabled = !isRemoteControlEnabled;
    const panel = document.getElementById('remoteControlPanel');
    const btn = document.getElementById('remoteControlBtn');
    if (isRemoteControlEnabled) {
        panel.style.display = 'block';
        btn.classList.add('remote-control-active');
        btn.textContent = '🖱️ Disable Control';
        enableScreenshotControl();
        window.addLog && window.addLog('Remote Control', 'Remote control enabled', 'success');
        window.showNotification && window.showNotification('Remote control enabled, click screenshot to operate', 'success');
    } else {
        panel.style.display = 'none';
        btn.classList.remove('remote-control-active');
        btn.textContent = '🖱️ Remote Control';
        disableScreenshotControl();
        window.addLog && window.addLog('Remote Control', 'Remote control disabled', 'info');
        window.showNotification && window.showNotification('Remote control disabled', 'info');
    }
}

function enableScreenshotControl() {
    const screenshots = document.querySelectorAll('.screenshot-image, .monitor-image');
    screenshots.forEach(img => {
        img.classList.add('remote-control-enabled');
    });
}

function disableScreenshotControl() {
    const screenshots = document.querySelectorAll('.screenshot-image, .monitor-image');
    screenshots.forEach(img => {
        img.classList.remove('remote-control-enabled');
    });
}

function setupScreenshotClickEvents() {
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            mutation.addedNodes.forEach((node) => {
                if (node.nodeType === Node.ELEMENT_NODE) {
                    const images = node.querySelectorAll ? node.querySelectorAll('.screenshot-image, .monitor-image') : [];
                    images.forEach(setupImageEvents);
                }
            });
        });
    });
    observer.observe(document.body, { childList: true, subtree: true });
    const existingImages = document.querySelectorAll('.screenshot-image, .monitor-image');
    existingImages.forEach(setupImageEvents);
}

function setupImageEvents(img) {
    if (!img) return;
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        img.addEventListener(eventName, preventDefaults, false);
    });

    img.removeEventListener('click', handleScreenshotClick);
    img.removeEventListener('dblclick', handleScreenshotDoubleClick);
    img.removeEventListener('contextmenu', handleScreenshotRightClick);
    img.removeEventListener('mousedown', handleScreenshotMouseDown);
    img.removeEventListener('mousemove', handleScreenshotMouseMove);
    img.removeEventListener('mouseup', handleScreenshotMouseUp);
    img.removeEventListener('wheel', handleScreenshotWheel);
    img.removeEventListener('drop', handleScreenshotDrop);
    img.addEventListener('click', handleScreenshotClick, { passive: true });
    img.addEventListener('dblclick', handleScreenshotDoubleClick, { passive: true });
    img.addEventListener('contextmenu', handleScreenshotRightClick, { passive: true });
    img.addEventListener('mousedown', handleScreenshotMouseDown, { passive: true });
    img.addEventListener('mousemove', handleScreenshotMouseMove, { passive: true });
    img.addEventListener('mouseup', handleScreenshotMouseUp, { passive: true });
    img.addEventListener('wheel', handleScreenshotWheel, { passive: true });
    img.addEventListener('drop', handleScreenshotDrop, { passive: true });
}

function handleScreenshotClick(event) {
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Calculate percentage position
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;

    const monitorIndex = getMonitorIndexFromImage(event.target);
    console.log(`Preparing to send remote click: Pixels(${x.toFixed(1)}, ${y.toFixed(1)}), Percentage(${percentX.toFixed(2)}%, ${percentY.toFixed(2)}%), Monitor index: ${monitorIndex}`);
    sendRemoteClick(percentX, percentY, monitorIndex, true); // Add percentage flag
}

function handleScreenshotDoubleClick(event) {
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Calculate percentage position
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;

    const monitorIndex = getMonitorIndexFromImage(event.target);
    sendRemoteDoubleClick(percentX, percentY, monitorIndex, true);
}

function handleScreenshotRightClick(event) {
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Calculate percentage position
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;

    const monitorIndex = getMonitorIndexFromImage(event.target);
    sendRemoteRightClick(percentX, percentY, monitorIndex, true);
}

function handleScreenshotMouseDown(event) {
    if (event.button === 0) {
        isDragging = true;
        const rect = event.target.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;

        // Save percentage position
        dragStartX = (x / rect.width) * 100;
        dragStartY = (y / rect.height) * 100;
    }
}

function handleScreenshotMouseMove(event) {
    // Optional: Visual feedback during dragging
}

function handleScreenshotMouseUp(event) {
    isDragging = false;
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Calculate percentage of end position
    const endX = (x / rect.width) * 100;
    const endY = (y / rect.height) * 100;

    const monitorIndex = getMonitorIndexFromImage(event.target);

    // Calculate distance using percentages
    const distance = Math.sqrt((endX - dragStartX) ** 2 + (endY - dragStartY) ** 2);
    if (distance > 2) { // Smaller percentage threshold
        sendRemoteDrag(dragStartX, dragStartY, endX, endY, monitorIndex, true);
    }
}

function handleScreenshotWheel(event) {
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Calculate percentage position
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;

    const monitorIndex = getMonitorIndexFromImage(event.target);
    const clicks = event.deltaY > 0 ? -3 : 3;
    sendRemoteScroll(percentX, percentY, clicks, monitorIndex, true);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleScreenshotDrop(event) {
    const dt = event.dataTransfer;
    const files = dt.files;

    dropToUploadFiles(files);
}

function setupDragEvents() {
    document.addEventListener('mouseup', () => {
        isDragging = false;
    });
}

function getMonitorIndexFromImage(img) {
    const monitorItem = img.closest('.monitor-item');
    if (monitorItem) {
        const dataIndex = monitorItem.getAttribute('data-monitor-index');
        if (dataIndex) {
            return parseInt(dataIndex);
        }
    }
    return 0;
}

async function sendRemoteClick(x, y, monitorIndex = 0, usePercentage = false) {
    try {
        const coordType = usePercentage ? 'percentage' : 'pixel';
        const serverUrl = window.getServerBaseUrl() + '/remote/click';

        const response = await fetch(serverUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                x,
                y,
                monitor_index: monitorIndex,
                use_percentage: usePercentage
            })
        });

        const result = await response.json();

        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Click successful: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)})`, 'success');
            console.log('Remote click successful');
        } else {
            window.addLog && window.addLog('Remote Control', `Click failed: ${result.message}`, 'error');
            console.error('Remote click failed:', result.message);
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Click operation failed: ${error.message}`, 'error');
        console.error('Failed to send remote click request:', error);
    }
}

async function sendRemoteDoubleClick(x, y, monitorIndex = 0, usePercentage = false) {
    try {
        const response = await fetch(window.getServerBaseUrl() + '/remote/double-click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                x,
                y,
                monitor_index: monitorIndex,
                use_percentage: usePercentage
            })
        });
        const result = await response.json();
        const coordType = usePercentage ? 'percentage' : 'pixel';
        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Double click successful: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)})`, 'success');
        } else {
            window.addLog && window.addLog('Remote Control', `Double click failed: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Double click operation failed: ${error.message}`, 'error');
    }
}

async function sendRemoteRightClick(x, y, monitorIndex = 0, usePercentage = false) {
    try {
        const response = await fetch(window.getServerBaseUrl() + '/remote/right-click', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                x,
                y,
                monitor_index: monitorIndex,
                use_percentage: usePercentage
            })
        });
        const result = await response.json();
        const coordType = usePercentage ? 'percentage' : 'pixel';
        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Right click successful: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)})`, 'success');
        } else {
            window.addLog && window.addLog('Remote Control', `Right click failed: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Right click operation failed: ${error.message}`, 'error');
    }
}

async function sendRemoteDrag(startX, startY, endX, endY, monitorIndex = 0, usePercentage = false) {
    try {
        const response = await fetch(window.getServerBaseUrl() + '/remote/drag', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                start_x: startX,
                start_y: startY,
                end_x: endX,
                end_y: endY,
                monitor_index: monitorIndex,
                use_percentage: usePercentage
            })
        });
        const result = await response.json();
        const coordType = usePercentage ? 'percentage' : 'pixel';
        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Drag successful: ${coordType}(${startX.toFixed(2)}, ${startY.toFixed(2)}) -> (${endX.toFixed(2)}, ${endY.toFixed(2)})`, 'success');
        } else {
            window.addLog && window.addLog('Remote Control', `Drag failed: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Drag operation failed: ${error.message}`, 'error');
    }
}

async function sendRemoteScroll(x, y, clicks, monitorIndex = 0, usePercentage = false) {
    try {
        const response = await fetch(window.getServerBaseUrl() + '/remote/scroll', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                x,
                y,
                clicks,
                monitor_index: monitorIndex,
                use_percentage: usePercentage
            })
        });
        const result = await response.json();
        const coordType = usePercentage ? 'percentage' : 'pixel';
        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Scroll operation successful: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)}) scroll ${clicks}`, 'success');
        } else {
            window.addLog && window.addLog('Remote Control', `Scroll operation failed: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Scroll operation failed: ${error.message}`, 'error');
    }
}

async function sendRemoteText() {
    const textInput = document.getElementById('remoteTextInput');
    const text = textInput.value.trim();
    if (!text) {
        window.showNotification && window.showNotification('Please enter text to send', 'warning');
        return;
    }
    try {
        const response = await fetch(window.getServerBaseUrl() + '/remote/type', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const result = await response.json();
        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Text sent successfully: ${text}`, 'success');
            window.showNotification && window.showNotification('Text sent successfully', 'success');
            textInput.value = '';
        } else {
            window.addLog && window.addLog('Remote Control', `Text sending failed: ${result.message}`, 'error');
            window.showNotification && window.showNotification('Text sending failed', 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Text sending failed: ${error.message}`, 'error');
        window.showNotification && window.showNotification('Text sending failed', 'error');
    }
}

// For debugging remote keyboard actions
function waitFiveSeconds() {
    console.log('Waiting 5 seconds to ensure previous operations are completed...');
    return new Promise(resolve => setTimeout(resolve, 5000));
}

async function sendRemoteKey(key) {
    try {
        const response = await fetch(window.getServerBaseUrl() + '/remote/press-key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ key })
        });
        const result = await response.json();
        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Key pressed successfully: ${key}`, 'success');
        } else {
            window.addLog && window.addLog('Remote Control', `Key press failed: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Key press operation failed: ${error.message}`, 'error');
    }
}

async function sendRemoteHotkey(keys) {
    try {
        const response = await fetch(window.getServerBaseUrl() + '/remote/hotkey', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keys })
        });
        const result = await response.json();
        if (result.success) {
            window.addLog && window.addLog('Remote Control', `Hotkey pressed successfully: ${keys.join('+')}`, 'success');
        } else {
            window.addLog && window.addLog('Remote Control', `Hotkey press failed: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('Remote Control', `Hotkey operation failed: ${error.message}`, 'error');
    }
}

// Mount to window for external calls
window.initRemoteControl = initRemoteControl;
window.toggleRemoteControl = toggleRemoteControl;
window.sendRemoteText = sendRemoteText;
window.sendRemoteKey = sendRemoteKey;
window.sendRemoteHotkey = sendRemoteHotkey;