// 显示器模块 - 显示器截图和显示功能

// 刷新截图
async function refreshScreenshot() {
    try {
        const screenshot = document.getElementById('screenshot');
        
        // 如果当前处于全屏状态，暂停自动刷新
        if (document.fullscreenElement === screenshot) {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
                addLog('截图', '检测到全屏状态，已暂停自动刷新', 'info');
            }
            return;
        }
        
        // 显示加载指示器
        const loadingIndicator = document.getElementById('loading-indicator');
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

// 切换自动刷新状态
function toggleAutoRefresh() {
    const autoRefreshBtn = document.getElementById('autoRefreshBtn');
    
    if (autoRefreshInterval) {
        // 当前正在自动刷新，停止它
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        autoRefreshBtn.textContent = '🔄 自动刷新';
        autoRefreshBtn.className = 'btn btn-primary';
        addLog('自动刷新', '已停止', 'info');
    } else {
        // 当前未自动刷新，启动它
        autoRefreshInterval = setInterval(refreshAllMonitors, 800); // 0.8秒间隔，与WebSocket频率一致
        autoRefreshBtn.textContent = '⏸️ 停止刷新';
        autoRefreshBtn.className = 'btn btn-danger';
        addLog('自动刷新', '已启动 (0.5秒间隔)', 'success');
    }
}

// 开始自动刷新
function startAutoRefresh() {
    if (autoRefreshInterval) {
        addLog('自动刷新', '已经在运行中', 'warning');
        return;
    }

    autoRefreshInterval = setInterval(refreshAllMonitors, 800); // 0.8秒间隔，与WebSocket频率一致
    addLog('自动刷新', '已启动 (1秒间隔)', 'success');
    
    // 更新按钮状态
    const autoRefreshBtn = document.getElementById('autoRefreshBtn');
    if (autoRefreshBtn) {
        autoRefreshBtn.textContent = '⏸️ 停止刷新';
        autoRefreshBtn.className = 'btn btn-danger';
    }
}

// 停止自动刷新
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        addLog('自动刷新', '已停止', 'info');
        
        // 更新按钮状态
        const autoRefreshBtn = document.getElementById('autoRefreshBtn');
        if (autoRefreshBtn) {
            autoRefreshBtn.textContent = '🔄 自动刷新';
            autoRefreshBtn.className = 'btn btn-primary';
        }
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
        // 检查是否所有显示器都被收起
        if (areAllMonitorsCollapsed()) {
            // 所有显示器都被收起时，不调用API，直接显示占位符
            addLog('截图', '所有显示器都已收起，跳过截图获取', 'info');
            displayCollapsedMonitorsPlaceholder();
            return;
        }

        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshots/all`, {
            timeout: 10000 // 10秒超时
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();

        // 使用API返回的总显示器数量，而不是当前活跃的显示器数量
        if (data.total_monitor_count !== undefined) {
            totalMonitorCount = data.total_monitor_count;
        }
        
        if (data.screenshots && data.screenshots.length > 0) {
            displayMultiMonitors(data.screenshots);
        } else if (data.screenshots && data.screenshots.length === 0) {
            // 如果返回空数组，检查是否所有显示器都被收起
            if (areAllMonitorsCollapsed()) {
                addLog('调试', '检测到所有显示器都已收起，显示占位符', 'info');
                displayCollapsedMonitorsPlaceholder();
            } else {
                // 如果没有显示器数据但也不是全部收起，显示加载状态
                addLog('调试', 'API返回空数组但并非全部收起，显示加载状态', 'info');
                const grid = document.getElementById('monitors-grid');
                grid.innerHTML = '<div class="monitor-loading"><div class="loading"></div>正在加载显示器信息...</div>';
            }
        } else {
            // 处理其他情况
            addLog('调试', 'API返回数据格式异常', 'info');
            const grid = document.getElementById('monitors-grid');
            grid.innerHTML = '<div class="monitor-loading"><div class="loading"></div>正在加载显示器信息...</div>';
        }
    } catch (error) {
        addLog('截图', '获取多显示器截图失败: ' + error.message, 'error');
        // 显示错误状态
        const grid = document.getElementById('monitors-grid');
        grid.innerHTML = '<div class="monitor-error">❌ 获取显示器信息失败，请检查服务器连接</div>';
    }
}

// 显示多显示器截图
function displayMultiMonitors(screenshots) {
    const grid = document.getElementById('monitors-grid');
    
    if (!screenshots || screenshots.length === 0) {
        grid.innerHTML = '<div class="monitor-loading"><div class="loading"></div>正在加载显示器信息...</div>';
        return;
    }

    // 自动收起非主显示器（仅在首次检测到多个显示器时）
    autoCollapseNonPrimaryMonitors(screenshots);

    // 检查是否有任何显示器处于全屏状态
    const hasFullscreenMonitor = document.fullscreenElement && 
        document.fullscreenElement.classList && 
        document.fullscreenElement.classList.contains('monitor-image');
    
    // 如果没有任何显示器处于全屏状态，正常重建DOM
    if (!hasFullscreenMonitor) {
        grid.innerHTML = '';
        
        // 为所有显示器创建元素，包括被收起的显示器
        for (let i = 0; i < totalMonitorCount; i++) {
            const screenshot = screenshots.find(s => s.monitor_index === i);
            if (screenshot) {
                // 如果API返回了这个显示器的数据，使用真实数据
                createMonitorElement(screenshot, i, grid);
            } else if (collapsedMonitors.has(i)) {
                // 如果显示器被收起且API没有返回数据，创建占位元素
                createCollapsedMonitorElement(i, grid);
            }
        }
        return;
    }

    // 如果有显示器处于全屏状态，采用保守更新策略
    screenshots.forEach((screenshot, index) => {
        const existingMonitorDiv = document.getElementById(`monitor-${screenshot.monitor_index}`);
        
        if (existingMonitorDiv) {
            // 更新现有显示器元素
            updateExistingMonitorElement(screenshot, existingMonitorDiv);
        } else {
            // 如果显示器不存在，创建新的
            createMonitorElement(screenshot, index, grid);
        }
    });
}

// 创建新的显示器元素
function createMonitorElement(screenshot, index, grid) {
    const monitorDiv = document.createElement('div');
    monitorDiv.className = `monitor-item ${screenshot.primary ? 'primary' : ''}`;
    monitorDiv.id = `monitor-${screenshot.monitor_index}`;

    // 设置分辨率信息到右上角标签
    const monitorType = screenshot.primary ? '主显示器' : '副显示器';
    monitorDiv.setAttribute('data-resolution', `${monitorType}（${screenshot.width}×${screenshot.height}）`);

    const img = document.createElement('img');
    img.className = 'monitor-image';
    
    // 检查显示器是否被收起
    const isCollapsed = collapsedMonitors.has(screenshot.monitor_index);
    
    if (isCollapsed) {
        // 如果被收起，使用占位图片
        img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOWZhIi8+PHRleHQgeD0iNDAwIiB5PSIzMDAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5YyF5a2Q5YyF5a2Q8L3RleHQ+PC9zdmc+';
        img.style.display = 'none';
        monitorDiv.classList.add('collapsed');
    } else {
        // 如果活跃，使用实际截图
        if (screenshot.image) {
            img.src = 'data:image/png;base64,' + screenshot.image;
            img.style.display = 'block';
        } else {
            // 如果没有截图数据，也显示占位符
            img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOWZhIi8+PHRleHQgeD0iNDAwIiB5PSIzMDAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5YyF5a2Q5YyF5a2Q8L3RleHQ+PC9zdmc+';
            img.style.display = 'none';
            monitorDiv.classList.add('collapsed');
        }
    }
    
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
            ${isCollapsed ? '👁️ 展开' : '📷 收起'}
        </button>
    `;

    // 设置按钮状态
    const toggleBtn = controls.querySelector(`#toggle-btn-${screenshot.monitor_index}`);
    if (isCollapsed) {
        toggleBtn.classList.add('collapsed');
        toggleBtn.dataset.expanded = "false";
    } else {
        toggleBtn.classList.remove('collapsed');
        toggleBtn.dataset.expanded = "true";
    }

    monitorDiv.appendChild(img);
    monitorDiv.appendChild(controls);
    grid.appendChild(monitorDiv);
}

// 为被收起的显示器创建占位元素
function createCollapsedMonitorElement(monitorIndex, grid) {
    const monitorDiv = document.createElement('div');
    monitorDiv.className = 'monitor-item collapsed';
    monitorDiv.id = `monitor-${monitorIndex}`;

    // 设置分辨率信息到右上角标签（使用默认值）
    monitorDiv.setAttribute('data-resolution', `副显示器（收起状态）`);

    const img = document.createElement('img');
    img.className = 'monitor-image';
    img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOWZhIi8+PHRleHQgeD0iNDAwIiB5PSIzMDAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5YyF5a2Q5YyF5a2Q8L3RleHQ+PC9zdmc+';
    img.style.display = 'none';
    img.alt = `副显示器 ${monitorIndex + 1}`;

    const controls = document.createElement('div');
    controls.className = 'monitor-controls';
    controls.innerHTML = `
        <button class="monitor-btn monitor-btn-refresh" onclick="refreshSingleMonitor(${monitorIndex})">
            🔄 刷新
        </button>
        <button class="monitor-btn monitor-btn-fullscreen" onclick="toggleMonitorFullscreen(${monitorIndex})">
            ⛶ 全屏
        </button>
        <button class="monitor-btn monitor-btn-toggle collapsed" id="toggle-btn-${monitorIndex}" onclick="toggleMonitorImage(${monitorIndex})" data-expanded="false">
            👁️ 展开
        </button>
    `;

    monitorDiv.appendChild(img);
    monitorDiv.appendChild(controls);
    grid.appendChild(monitorDiv);
}

// 更新现有的显示器元素
function updateExistingMonitorElement(screenshot, monitorDiv) {
    const img = monitorDiv.querySelector('.monitor-image');
    if (!img) return;

    // 检查显示器是否被收起
    const isCollapsed = collapsedMonitors.has(screenshot.monitor_index);
    
    // 如果图片当前处于全屏状态，跳过更新
    if (document.fullscreenElement === img) {
        addLog('截图', `显示器 ${screenshot.monitor_index + 1} 处于全屏状态，跳过更新`, 'info');
        return;
    }
    
    if (isCollapsed) {
        // 如果被收起，使用占位图片
        img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOWZhIi8+PHRleHQgeD0iNDAwIiB5PSIzMDAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5YyF5a2Q5YyF5a2Q8L3RleHQ+PC9zdmc+';
        img.style.display = 'none';
        monitorDiv.classList.add('collapsed');
    } else {
        // 如果活跃，使用实际截图
        if (screenshot.image) {
            img.src = 'data:image/png;base64,' + screenshot.image;
            img.style.display = 'block';
        } else {
            // 如果没有截图数据，也显示占位符
            img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAwIiBoZWlnaHQ9IjYwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjhmOWZhIi8+PHRleHQgeD0iNDAwIiB5PSIzMDAiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxOCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSI+5YyF5a2Q5YyF5a2Q8L3RleHQ+PC9zdmc+';
            img.style.display = 'none';
            monitorDiv.classList.add('collapsed');
        }
    }
    
    // 更新按钮状态
    const toggleBtn = monitorDiv.querySelector(`#toggle-btn-${screenshot.monitor_index}`);
    if (toggleBtn) {
        if (isCollapsed) {
            toggleBtn.classList.add('collapsed');
            toggleBtn.dataset.expanded = "false";
            toggleBtn.textContent = '👁️ 展开';
        } else {
            toggleBtn.classList.remove('collapsed');
            toggleBtn.dataset.expanded = "true";
            toggleBtn.textContent = '📷 收起';
        }
    }
    
    // 更新分辨率信息
    const monitorType = screenshot.primary ? '主显示器' : '副显示器';
    monitorDiv.setAttribute('data-resolution', `${monitorType}（${screenshot.width}×${screenshot.height}）`);
}

// 显示所有显示器收起时的占位符
function displayCollapsedMonitorsPlaceholder() {
    const grid = document.getElementById('monitors-grid');
    grid.innerHTML = '';

    // 创建占位符显示
    const placeholderDiv = document.createElement('div');
    placeholderDiv.className = 'monitor-item collapsed-placeholder';
    placeholderDiv.innerHTML = `
        <div class="collapsed-placeholder-content">
            <div class="collapsed-placeholder-icon">📷</div>
            <div class="collapsed-placeholder-text">所有显示器都已收起</div>
            <div class="collapsed-placeholder-subtext">点击下方按钮可重新显示所有显示器截图</div>
            <button class="btn btn-primary expand-all-btn" onclick="resetCollapsedMonitors()" style="margin-top: 20px;">
                👁️ 展开所有显示器
            </button>
        </div>
    `;

    grid.appendChild(placeholderDiv);
}

// 刷新单个显示器
async function refreshSingleMonitor(monitorIndex) {
    try {
        const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
        if (!monitorDiv) {
            addLog('截图', `找不到显示器 ${monitorIndex + 1} 的容器`, 'error');
            return;
        }

        // 检查显示器是否被收起
        if (collapsedMonitors.has(monitorIndex)) {
            addLog('截图', `显示器 ${monitorIndex + 1} 已被收起，无法刷新`, 'warning');
            return;
        }

        const img = monitorDiv.querySelector('.monitor-image');
        
        // 如果当前处于全屏状态，暂停自动刷新
        if (document.fullscreenElement === img) {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
                addLog('截图', `检测到显示器 ${monitorIndex + 1} 全屏状态，已暂停自动刷新`, 'info');
            }
            return;
        }
        
        // 显示加载状态
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
                if (info) {
                    info.innerHTML = `
                                <span>更新时间: ${new Date().toLocaleTimeString()}</span>
                            `;
                }

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

    // 检查显示器是否被收起
    if (collapsedMonitors.has(monitorIndex)) {
        addLog('截图', `显示器 ${monitorIndex + 1} 已被收起，无法全屏查看`, 'warning');
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
        
        // 如果当前处于全屏状态，暂停调试
        if (document.fullscreenElement === img) {
            addLog('调试', `显示器 ${monitorIndex + 1} 当前处于全屏状态，暂停调试以避免退出全屏`, 'info');
            return;
        }
        
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
    const isCollapsed = collapsedMonitors.has(monitorIndex);

    if (isCollapsed) {
        // 展开：显示图片
        collapsedMonitors.delete(monitorIndex);
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
        toggleBtn.dataset.expanded = "true";
        addLog('截图', `展开显示器 ${monitorIndex + 1}，将重新获取截图`, 'info');
        
        // 同步到后端
        syncCollapsedMonitorsToBackend();
        
        // 检查是否从全部收起状态恢复，如果是则刷新显示
        if (areAllMonitorsCollapsed() === false && totalMonitorCount > 0) {
            // 从全部收起状态恢复，需要重新获取截图
            setTimeout(() => {
                refreshAllMonitors();
            }, 100);
        }
    } else {
        // 收起：隐藏图片但保持显示器元素可见
        collapsedMonitors.add(monitorIndex);
        img.style.opacity = '0';
        img.classList.remove('expanded');
        img.classList.add('expanding');

        setTimeout(() => {
            img.style.display = 'none';
            monitorDiv.classList.add('collapsed');
        }, 300);

        toggleBtn.innerHTML = '👁️ 展开';
        toggleBtn.classList.add('collapsed');
        toggleBtn.dataset.expanded = "false";
        addLog('截图', `收起显示器 ${monitorIndex + 1}，将停止获取截图`, 'info');
        
        // 同步到后端
        syncCollapsedMonitorsToBackend();
        
        // 检查是否所有显示器都被收起
        if (areAllMonitorsCollapsed()) {
            addLog('截图', '所有显示器都已收起，将停止自动刷新', 'info');
            // 显示占位符
            setTimeout(() => {
                displayCollapsedMonitorsPlaceholder();
            }, 300);
        }
    }
} 