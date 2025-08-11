// ==================== 远程控制功能 ====================

// 远程控制相关变量
let isRemoteControlEnabled = false;
let isDragging = false;
let dragStartX = 0;
let dragStartY = 0;

// 初始化远程控制
function initRemoteControl() {
    setupScreenshotClickEvents();
    setupDragEvents();
    window.addLog && window.addLog('远程控制', '远程控制功能已初始化', 'info');
}

// 切换远程控制状态
function toggleRemoteControl() {
    isRemoteControlEnabled = !isRemoteControlEnabled;
    const panel = document.getElementById('remoteControlPanel');
    const btn = document.getElementById('remoteControlBtn');
    if (isRemoteControlEnabled) {
        panel.style.display = 'block';
        btn.classList.add('remote-control-active');
        btn.textContent = '🖱️ 关闭控制';
        enableScreenshotControl();
        window.addLog && window.addLog('远程控制', '远程控制已启用', 'success');
        window.showNotification && window.showNotification('远程控制已启用，点击截图进行操作', 'success');
    } else {
        panel.style.display = 'none';
        btn.classList.remove('remote-control-active');
        btn.textContent = '🖱️ 远程控制';
        disableScreenshotControl();
        window.addLog && window.addLog('远程控制', '远程控制已禁用', 'info');
        window.showNotification && window.showNotification('远程控制已禁用', 'info');
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
    img.removeEventListener('click', handleScreenshotClick);
    img.removeEventListener('dblclick', handleScreenshotDoubleClick);
    img.removeEventListener('contextmenu', handleScreenshotRightClick);
    img.removeEventListener('mousedown', handleScreenshotMouseDown);
    img.removeEventListener('mousemove', handleScreenshotMouseMove);
    img.removeEventListener('mouseup', handleScreenshotMouseUp);
    img.removeEventListener('wheel', handleScreenshotWheel);
    img.addEventListener('click', handleScreenshotClick);
    img.addEventListener('dblclick', handleScreenshotDoubleClick);
    img.addEventListener('contextmenu', handleScreenshotRightClick);
    img.addEventListener('mousedown', handleScreenshotMouseDown);
    img.addEventListener('mousemove', handleScreenshotMouseMove);
    img.addEventListener('mouseup', handleScreenshotMouseUp);
    img.addEventListener('wheel', handleScreenshotWheel);
}

function handleScreenshotClick(event) {
    if (!isRemoteControlEnabled) {
        console.log('远程控制未启用，忽略点击');
        return;
    }
    event.preventDefault();
    event.stopPropagation();
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // 计算百分比位置
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;
    
    const monitorIndex = getMonitorIndexFromImage(event.target);
    console.log(`准备发送远程点击: 像素(${x.toFixed(1)}, ${y.toFixed(1)}), 百分比(${percentX.toFixed(2)}%, ${percentY.toFixed(2)}%), 监视器索引: ${monitorIndex}`);
    sendRemoteClick(percentX, percentY, monitorIndex, true); // 添加百分比标志
}

function handleScreenshotDoubleClick(event) {
    if (!isRemoteControlEnabled) return;
    event.preventDefault();
    event.stopPropagation();
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // 计算百分比位置
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;
    
    const monitorIndex = getMonitorIndexFromImage(event.target);
    sendRemoteDoubleClick(percentX, percentY, monitorIndex, true);
}

function handleScreenshotRightClick(event) {
    if (!isRemoteControlEnabled) return;
    event.preventDefault();
    event.stopPropagation();
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // 计算百分比位置
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;
    
    const monitorIndex = getMonitorIndexFromImage(event.target);
    sendRemoteRightClick(percentX, percentY, monitorIndex, true);
}

function handleScreenshotMouseDown(event) {
    if (!isRemoteControlEnabled) return;
    if (event.button === 0) {
        isDragging = true;
        const rect = event.target.getBoundingClientRect();
        const x = event.clientX - rect.left;
        const y = event.clientY - rect.top;
        
        // 保存百分比位置
        dragStartX = (x / rect.width) * 100;
        dragStartY = (y / rect.height) * 100;
    }
}

function handleScreenshotMouseMove(event) {
    if (!isRemoteControlEnabled || !isDragging) return;
    // 可选：拖拽时的视觉反馈
}

function handleScreenshotMouseUp(event) {
    if (!isRemoteControlEnabled || !isDragging) return;
    isDragging = false;
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // 计算结束位置的百分比
    const endX = (x / rect.width) * 100;
    const endY = (y / rect.height) * 100;
    
    const monitorIndex = getMonitorIndexFromImage(event.target);
    
    // 使用百分比计算距离
    const distance = Math.sqrt((endX - dragStartX) ** 2 + (endY - dragStartY) ** 2);
    if (distance > 2) { // 百分比阈值调小
        sendRemoteDrag(dragStartX, dragStartY, endX, endY, monitorIndex, true);
    }
}

function handleScreenshotWheel(event) {
    if (!isRemoteControlEnabled) return;
    event.preventDefault();
    event.stopPropagation();
    const rect = event.target.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    
    // 计算百分比位置
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;
    
    const monitorIndex = getMonitorIndexFromImage(event.target);
    const clicks = event.deltaY > 0 ? -3 : 3;
    sendRemoteScroll(percentX, percentY, clicks, monitorIndex, true);
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
        const coordType = usePercentage ? '百分比' : '像素';
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
            window.addLog && window.addLog('远程控制', `点击成功: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)})`, 'success');
            console.log('远程点击成功');
        } else {
            window.addLog && window.addLog('远程控制', `点击失败: ${result.message}`, 'error');
            console.error('远程点击失败:', result.message);
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `点击操作失败: ${error.message}`, 'error');
        console.error('发送远程点击请求失败:', error);
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
        const coordType = usePercentage ? '百分比' : '像素';
        if (result.success) {
            window.addLog && window.addLog('远程控制', `双击成功: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)})`, 'success');
        } else {
            window.addLog && window.addLog('远程控制', `双击失败: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `双击操作失败: ${error.message}`, 'error');
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
        const coordType = usePercentage ? '百分比' : '像素';
        if (result.success) {
            window.addLog && window.addLog('远程控制', `右键点击成功: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)})`, 'success');
        } else {
            window.addLog && window.addLog('远程控制', `右键点击失败: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `右键点击操作失败: ${error.message}`, 'error');
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
        const coordType = usePercentage ? '百分比' : '像素';
        if (result.success) {
            window.addLog && window.addLog('远程控制', `拖拽成功: ${coordType}(${startX.toFixed(2)}, ${startY.toFixed(2)}) -> (${endX.toFixed(2)}, ${endY.toFixed(2)})`, 'success');
        } else {
            window.addLog && window.addLog('远程控制', `拖拽失败: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `拖拽操作失败: ${error.message}`, 'error');
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
        const coordType = usePercentage ? '百分比' : '像素';
        if (result.success) {
            window.addLog && window.addLog('远程控制', `滚轮操作成功: ${coordType}(${x.toFixed(2)}, ${y.toFixed(2)}) 滚动 ${clicks}`, 'success');
        } else {
            window.addLog && window.addLog('远程控制', `滚轮操作失败: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `滚轮操作失败: ${error.message}`, 'error');
    }
}

async function sendRemoteText() {
    const textInput = document.getElementById('remoteTextInput');
    const text = textInput.value.trim();
    if (!text) {
        window.showNotification && window.showNotification('请输入要发送的文本', 'warning');
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
            window.addLog && window.addLog('远程控制', `文本发送成功: ${text}`, 'success');
            window.showNotification && window.showNotification('文本发送成功', 'success');
            textInput.value = '';
        } else {
            window.addLog && window.addLog('远程控制', `文本发送失败: ${result.message}`, 'error');
            window.showNotification && window.showNotification('文本发送失败', 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `文本发送失败: ${error.message}`, 'error');
        window.showNotification && window.showNotification('文本发送失败', 'error');
    }
}

// 调试远程 keyboard 动作用
function waitFiveSeconds() {
    console.log('等待5秒钟以确保前面的操作完成...');
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
            window.addLog && window.addLog('远程控制', `按键成功: ${key}`, 'success');
        } else {
            window.addLog && window.addLog('远程控制', `按键失败: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `按键操作失败: ${error.message}`, 'error');
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
            window.addLog && window.addLog('远程控制', `组合键成功: ${keys.join('+')}`, 'success');
        } else {
            window.addLog && window.addLog('远程控制', `组合键失败: ${result.message}`, 'error');
        }
    } catch (error) {
        window.addLog && window.addLog('远程控制', `组合键操作失败: ${error.message}`, 'error');
    }
}

// 挂载到 window 以便外部调用
window.initRemoteControl = initRemoteControl;
window.toggleRemoteControl = toggleRemoteControl;
window.sendRemoteText = sendRemoteText;
window.sendRemoteKey = sendRemoteKey;
window.sendRemoteHotkey = sendRemoteHotkey;
