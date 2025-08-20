// Monitor module - Monitor screenshot and display functionality

// Refresh screenshot
async function refreshScreenshot() {
    try {
        const screenshot = document.getElementById('screenshot');

        // If currently in fullscreen mode, pause auto-refresh
        if (document.fullscreenElement === screenshot) {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
                addLog('Screenshot', 'Fullscreen mode detected, auto-refresh paused', 'info');
            }
            return;
        }

        // Show loading indicator
        const loadingIndicator = document.getElementById('loading-indicator');
        loadingIndicator.style.display = 'block';
        screenshot.style.opacity = '0.5';

        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshot`);
        const data = await response.json();

        if (data.image) {
            // Create new image object for preloading
            const newImage = new Image();
            newImage.onload = function () {
                screenshot.src = this.src;
                screenshot.style.opacity = '1';
                loadingIndicator.style.display = 'none';
                addLog('Screenshot', 'Refresh successful', 'success');
            };
            newImage.onerror = function () {
                loadingIndicator.style.display = 'none';
                screenshot.style.opacity = '1';
                addLog('Screenshot', 'Image loading failed', 'error');
            };
            newImage.src = 'data:image/png;base64,' + data.image;
        } else if (data.error) {
            loadingIndicator.style.display = 'none';
            screenshot.style.opacity = '1';
            addLog('Screenshot', 'Refresh failed: ' + data.error, 'error');
        }
    } catch (error) {
        const loadingIndicator = document.getElementById('loading-indicator');
        const screenshot = document.getElementById('screenshot');
        loadingIndicator.style.display = 'none';
        screenshot.style.opacity = '1';
        addLog('Screenshot', 'Network error: ' + error.message, 'error');
    }
}

// Toggle auto-refresh status
function toggleAutoRefresh() {
    const autoRefreshBtn = document.getElementById('autoRefreshBtn');

    if (autoRefreshInterval) {
        // Currently auto-refreshing, stop it
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        autoRefreshBtn.textContent = '🔄 Auto Refresh';
        autoRefreshBtn.className = 'btn btn-primary';
        addLog('Auto Refresh', 'Stopped', 'info');
    } else {
        // Not currently auto-refreshing, start it
        autoRefreshInterval = setInterval(refreshAllMonitors, 500); // 0.5 second interval
        autoRefreshBtn.textContent = '⏸️ Stop Refresh';
        autoRefreshBtn.className = 'btn btn-danger';
        addLog('Auto Refresh', 'Started (0.5s interval)', 'success');
    }
}

// Start auto-refresh
function startAutoRefresh() {
    if (autoRefreshInterval) {
        addLog('Auto Refresh', 'Already running', 'warning');
        return;
    }

    autoRefreshInterval = setInterval(refreshAllMonitors, 500); // 0.5 second interval
    addLog('Auto Refresh', 'Started (1s interval)', 'success');

    // Update button status
    const autoRefreshBtn = document.getElementById('autoRefreshBtn');
    if (autoRefreshBtn) {
        autoRefreshBtn.textContent = '⏸️ Stop Refresh';
        autoRefreshBtn.className = 'btn btn-danger';
    }
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        addLog('Auto Refresh', 'Stopped', 'info');

        // Update button status
        const autoRefreshBtn = document.getElementById('autoRefreshBtn');
        if (autoRefreshBtn) {
            autoRefreshBtn.textContent = '🔄 Auto Refresh';
            autoRefreshBtn.className = 'btn btn-primary';
        }
    }
}

// Get screenshot information
async function getScreenshotInfo() {
    try {
        addLog('Screenshot', 'Retrieving screenshot information...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshot-info`);
        const data = await response.json();

        if (data.virtual_screen) {
            let info = `Virtual Screen: ${data.virtual_screen.width}x${data.virtual_screen.height} | Primary Screen: ${data.primary_screen.width}x${data.primary_screen.height} | Current Screenshot: ${data.current_screenshot.width}x${data.current_screenshot.height}`;
            addLog('Screenshot', info, 'success');

            // Display monitor details
            if (data.monitors && data.monitors.length > 0) {
                addLog('Screenshot', `Detected ${data.monitor_count} monitors:`, 'info');
                data.monitors.forEach(monitor => {
                    const monitorInfo = `Monitor ${monitor.index + 1}${monitor.primary ? ' (Primary)' : ''}: ${monitor.width}x${monitor.height} Position(${monitor.left},${monitor.top})`;
                    addLog('Screenshot', monitorInfo, 'info');
                });
            }
        }
    } catch (error) {
        addLog('Screenshot', 'Failed to retrieve screenshot information: ' + error.message, 'error');
    }
}

// Get monitor configuration information
async function getMonitorsConfig() {
    try {
        addLog('Monitor', 'Retrieving monitor configuration information...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/monitors/config`);
        const data = await response.json();

        if (data.system_info && data.monitors) {
            let configInfo = `System Information:\n`;
            configInfo += `  Monitor Count: ${data.system_info.monitor_count}\n`;
            configInfo += `  Virtual Desktop: ${data.system_info.virtual_screen.width}x${data.system_info.virtual_screen.height} Position(${data.system_info.virtual_screen.left},${data.system_info.virtual_screen.top})\n`;
            configInfo += `  Primary Monitor: ${data.system_info.primary_screen.width}x${data.system_info.primary_screen.height}\n`;
            configInfo += `  Detection Method: ${data.detection_method}\n\n`;

            configInfo += `Monitor Details:\n`;
            data.monitors.forEach(monitor => {
                configInfo += `  Monitor ${monitor.index + 1}${monitor.primary ? ' (Primary)' : ''}: \n`;
                configInfo += `    Resolution: ${monitor.width}x${monitor.height}\n`;
                configInfo += `    Position: (${monitor.left}, ${monitor.top})\n`;
                configInfo += `    Area: (${monitor.left}, ${monitor.top}, ${monitor.right}, ${monitor.bottom})\n`;
                configInfo += `    Pixel Area: ${monitor.area.toLocaleString()}\n`;
            });

            addLog('Monitor', configInfo, 'success');
        } else {
            addLog('Monitor', 'No monitor configuration information retrieved', 'warning');
        }
    } catch (error) {
        addLog('Monitor', 'Failed to retrieve monitor configuration: ' + error.message, 'error');
    }
}

// Refresh all monitor screenshots
async function refreshAllMonitors() {
    try {
        // Check if all monitors are collapsed
        if (areAllMonitorsCollapsed()) {
            // When all monitors are collapsed, don't call API, show placeholder directly
            addLog('Screenshot', 'All monitors are collapsed, skipping screenshot retrieval', 'info');
            displayCollapsedMonitorsPlaceholder();
            return;
        }

        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshots/all`, {
            timeout: 10000 // 10 second timeout
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        // Use total monitor count returned by API instead of currently active count
        if (data.total_monitor_count !== undefined) {
            totalMonitorCount = data.total_monitor_count;
        }

        if (data.screenshots && data.screenshots.length > 0) {
            displayMultiMonitors(data.screenshots);
        } else if (data.screenshots && data.screenshots.length === 0) {
            // If empty array is returned, check if all monitors are collapsed
            if (areAllMonitorsCollapsed()) {
                addLog('Debug', 'Detected all monitors collapsed, showing placeholder', 'info');
                displayCollapsedMonitorsPlaceholder();
            } else {
                // If no monitor data but not all collapsed, show loading state
                addLog('Debug', 'API returned empty array but not all collapsed, showing loading state', 'info');
                const grid = document.getElementById('monitors-grid');
                grid.innerHTML = '<div class="monitor-loading"><div class="loading"></div>Loading monitor information...</div>';
            }
        } else {
            // Handle other cases
            addLog('Debug', 'API returned data in unexpected format', 'info');
            const grid = document.getElementById('monitors-grid');
            grid.innerHTML = '<div class="monitor-loading"><div class="loading"></div>Loading monitor information...</div>';
        }
    } catch (error) {
        addLog('Screenshot', 'Failed to retrieve multi-monitor screenshots: ' + error.message, 'error');
        // Show error state
        const grid = document.getElementById('monitors-grid');
        grid.innerHTML = '<div class="monitor-error">❌ Failed to retrieve monitor information, please check server connection</div>';
    }
}

// Display multi-monitor screenshots
function displayMultiMonitors(screenshots) {
    const grid = document.getElementById('monitors-grid');

    if (!screenshots || screenshots.length === 0) {
        grid.innerHTML = '<div class="monitor-loading"><div class="loading"></div>Loading monitor information...</div>';
        return;
    }

    // Auto-collapse non-primary monitors (only when multiple monitors are first detected)
    autoCollapseNonPrimaryMonitors(screenshots);

    // Check if any monitor is in fullscreen state
    const hasFullscreenMonitor = document.fullscreenElement &&
        document.fullscreenElement.classList &&
        document.fullscreenElement.classList.contains('monitor-image');

    // If no monitors are in fullscreen state, rebuild DOM normally
    if (!hasFullscreenMonitor) {
        grid.innerHTML = '';

        // Create elements for all monitors, including collapsed ones
        for (let i = 0; i < totalMonitorCount; i++) {
            const screenshot = screenshots.find(s => s.monitor_index === i);
            if (screenshot) {
                // Use real data if API returned data for this monitor
                createMonitorElement(screenshot, i, grid);
            } else if (collapsedMonitors.has(i)) {
                // Create placeholder element if monitor is collapsed and API didn't return data
                createCollapsedMonitorElement(i, grid);
            }
        }
        return;
    }

    // If any monitor is in fullscreen state, use conservative update strategy
    screenshots.forEach((screenshot, index) => {
        const existingMonitorDiv = document.getElementById(`monitor-${screenshot.monitor_index}`);

        if (existingMonitorDiv) {
            // Update existing monitor element
            updateExistingMonitorElement(screenshot, existingMonitorDiv);
        } else {
            // Create new if monitor doesn't exist
            createMonitorElement(screenshot, index, grid);
        }
    });
}

// Create new monitor element
function createMonitorElement(screenshot, index, grid) {
    const monitorDiv = document.createElement('div');
    monitorDiv.className = `monitor-item ${screenshot.primary ? 'primary' : ''}`;
    monitorDiv.id = `monitor-${screenshot.monitor_index}`;

    // Set resolution information to top-right label
    const monitorType = screenshot.primary ? 'Primary Monitor' : 'Secondary Monitor';
    monitorDiv.setAttribute('data-resolution', `${monitorType} (${screenshot.width}×${screenshot.height})`);

    const img = document.createElement('img');
    img.className = 'monitor-image';

    // Check if monitor is collapsed
    const isCollapsed = collapsedMonitors.has(screenshot.monitor_index);

    if (isCollapsed) {
        // Use placeholder image if collapsed
        img.src = '';
        img.style.display = 'none';
        monitorDiv.classList.add('collapsed');
    } else {
        // Use actual screenshot if active
        if (screenshot.image) {
            img.src = 'data:image/png;base64,' + screenshot.image;
            img.style.display = 'block';
        } else {
            // Show placeholder if no screenshot data
            img.src = '';
            img.style.display = 'none';
            monitorDiv.classList.add('collapsed');
        }
    }

    img.alt = `${monitorType} ${screenshot.monitor_index + 1}`;

    const controls = document.createElement('div');
    controls.className = 'monitor-controls';
    controls.innerHTML = `
        <button class="monitor-btn monitor-btn-refresh" onclick="refreshSingleMonitor(${screenshot.monitor_index})">
            🔄 Refresh
        </button>
        <button class="monitor-btn monitor-btn-fullscreen" onclick="toggleMonitorFullscreen(${screenshot.monitor_index})">
            ⛶ Fullscreen
        </button>
        <button class="monitor-btn monitor-btn-toggle" id="toggle-btn-${screenshot.monitor_index}" onclick="toggleMonitorImage(${screenshot.monitor_index})">
            ${isCollapsed ? '👁️ Expand' : '📷 Collapse'}
        </button>
    `;

    // Set button state
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

// Create placeholder element for collapsed monitor
function createCollapsedMonitorElement(monitorIndex, grid) {
    const monitorDiv = document.createElement('div');
    monitorDiv.className = 'monitor-item collapsed';
    monitorDiv.id = `monitor-${monitorIndex}`;

    // Set resolution information to top-right label (using default)
    monitorDiv.setAttribute('data-resolution', 'Secondary Monitor (Collapsed)');

    const img = document.createElement('img');
    img.className = 'monitor-image';
    img.src = '';
    img.style.display = 'none';
    img.alt = `Secondary Monitor ${monitorIndex + 1}`;

    const controls = document.createElement('div');
    controls.className = 'monitor-controls';
    controls.innerHTML = `
        <button class="monitor-btn monitor-btn-refresh" onclick="refreshSingleMonitor(${monitorIndex})">
            🔄 Refresh
        </button>
        <button class="monitor-btn monitor-btn-fullscreen" onclick="toggleMonitorFullscreen(${monitorIndex})">
            ⛶ Fullscreen
        </button>
        <button class="monitor-btn monitor-btn-toggle collapsed" id="toggle-btn-${monitorIndex}" onclick="toggleMonitorImage(${monitorIndex})" data-expanded="false">
            👁️ Expand
        </button>
    `;

    monitorDiv.appendChild(img);
    monitorDiv.appendChild(controls);
    grid.appendChild(monitorDiv);
}

// Update existing monitor element
function updateExistingMonitorElement(screenshot, monitorDiv) {
    const img = monitorDiv.querySelector('.monitor-image');
    if (!img) return;

    // Check if monitor is collapsed
    const isCollapsed = collapsedMonitors.has(screenshot.monitor_index);

    // Skip update if image is currently in fullscreen
    if (document.fullscreenElement === img) {
        addLog('Screenshot', `Monitor ${screenshot.monitor_index + 1} is in fullscreen, skipping update`, 'info');
        return;
    }

    if (isCollapsed) {
        // Use placeholder image if collapsed
        img.src = '';
        img.style.display = 'none';
        monitorDiv.classList.add('collapsed');
    } else {
        // Use actual screenshot if active
        if (screenshot.image) {
            img.src = 'data:image/png;base64,' + screenshot.image;
            img.style.display = 'block';
        } else {
            // Show placeholder if no screenshot data
            img.src = '';
            img.style.display = 'none';
            monitorDiv.classList.add('collapsed');
        }
    }

    // Update button state
    const toggleBtn = monitorDiv.querySelector(`#toggle-btn-${screenshot.monitor_index}`);
    if (toggleBtn) {
        if (isCollapsed) {
            toggleBtn.classList.add('collapsed');
            toggleBtn.dataset.expanded = "false";
            toggleBtn.textContent = '👁️ Expand';
        } else {
            toggleBtn.classList.remove('collapsed');
            toggleBtn.dataset.expanded = "true";
            toggleBtn.textContent = '📷 Collapse';
        }
    }

    // Update resolution information
    const monitorType = screenshot.primary ? 'Primary Monitor' : 'Secondary Monitor';
    monitorDiv.setAttribute('data-resolution', `${monitorType} (${screenshot.width}×${screenshot.height})`);
}

// Display placeholder when all monitors are collapsed
function displayCollapsedMonitorsPlaceholder() {
    const grid = document.getElementById('monitors-grid');
    grid.innerHTML = '';

    // Create placeholder display
    const placeholderDiv = document.createElement('div');
    placeholderDiv.className = 'monitor-item collapsed-placeholder';
    placeholderDiv.innerHTML = `
        <div class="collapsed-placeholder-content">
            <div class="collapsed-placeholder-icon">📷</div>
            <div class="collapsed-placeholder-text">All monitors are collapsed</div>
            <div class="collapsed-placeholder-subtext">Click the button below to start displaying monitor screenshots</div>
            <button class="btn btn-primary expand-all-btn" onclick="resetCollapsedMonitors()" style="margin-top: 20px;">
                👁️ Expand All Monitors
            </button>
        </div>
    `;

    grid.appendChild(placeholderDiv);
}

// Refresh single monitor
async function refreshSingleMonitor(monitorIndex) {
    try {
        const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
        if (!monitorDiv) {
            addLog('Screenshot', `Container for monitor ${monitorIndex + 1} not found`, 'error');
            return;
        }

        // Check if monitor is collapsed
        if (collapsedMonitors.has(monitorIndex)) {
            addLog('Screenshot', `Monitor ${monitorIndex + 1} is collapsed, cannot refresh`, 'warning');
            return;
        }

        const img = monitorDiv.querySelector('.monitor-image');

        // If currently in fullscreen mode, pause auto-refresh
        if (document.fullscreenElement === img) {
            if (autoRefreshInterval) {
                clearInterval(autoRefreshInterval);
                autoRefreshInterval = null;
                addLog('Screenshot', `Fullscreen detected on monitor ${monitorIndex + 1}, auto-refresh paused`, 'info');
            }
            return;
        }

        // Show loading state
        const originalSrc = img.src;
        img.style.opacity = '0.5';

        addLog('Screenshot', `Refreshing monitor ${monitorIndex + 1}...`, 'info');

        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/screenshot/monitor/${monitorIndex}`);
        const data = await response.json();

        if (data.image) {
            // Create new image object for preloading
            const newImage = new Image();
            newImage.onload = function () {
                img.src = this.src;
                img.style.opacity = '1';

                // Update timestamp
                const info = monitorDiv.querySelector('.monitor-info');
                if (info) {
                    info.innerHTML = `
                                <span>Update time: ${new Date().toLocaleTimeString()}</span>
                            `;
                }

                addLog('Screenshot', `Monitor ${monitorIndex + 1} refreshed successfully`, 'success');
            };
            newImage.onerror = function () {
                img.src = originalSrc;
                img.style.opacity = '1';
                addLog('Screenshot', `Monitor ${monitorIndex + 1} image failed to load`, 'error');
            };
            newImage.src = 'data:image/png;base64,' + data.image;
        } else if (data.error) {
            img.src = originalSrc;
            img.style.opacity = '1';
            addLog('Screenshot', `Monitor ${monitorIndex + 1} refresh failed: ${data.error}`, 'error');
        }
    } catch (error) {
        addLog('Screenshot', `Monitor ${monitorIndex + 1} refresh failed: ${error.message}`, 'error');
    }
}

// Toggle monitor fullscreen
function toggleMonitorFullscreen(monitorIndex) {
    const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
    if (!monitorDiv) {
        addLog('Screenshot', `Container for monitor ${monitorIndex + 1} not found`, 'error');
        return;
    }

    // Check if monitor is collapsed
    if (collapsedMonitors.has(monitorIndex)) {
        addLog('Screenshot', `Monitor ${monitorIndex + 1} is collapsed, cannot view in fullscreen`, 'warning');
        return;
    }

    const img = monitorDiv.querySelector('.monitor-image');
    if (!document.fullscreenElement) {
        // Enter fullscreen
        if (img.requestFullscreen) {
            img.requestFullscreen();
        } else if (img.webkitRequestFullscreen) {
            img.webkitRequestFullscreen();
        } else if (img.msRequestFullscreen) {
            img.msRequestFullscreen();
        }
        addLog('Screenshot', `Entered fullscreen mode for monitor ${monitorIndex + 1}`, 'info');
    } else {
        // Exit fullscreen
        if (document.exitFullscreen) {
            document.exitFullscreen();
        } else if (document.webkitExitFullscreen) {
            document.webkitExitFullscreen();
        } else if (document.msExitFullscreen) {
            document.msExitFullscreen();
        }
        addLog('Screenshot', `Exited fullscreen mode for monitor ${monitorIndex + 1}`, 'info');
    }
}

// Debug monitor (simulate refreshing single monitor)
async function debugMonitor(monitorIndex) {
    try {
        addLog('Debug', `Debugging monitor ${monitorIndex + 1}...`, 'info');
        const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
        if (!monitorDiv) {
            addLog('Debug', `Container for monitor ${monitorIndex + 1} not found`, 'error');
            return;
        }

        const img = monitorDiv.querySelector('.monitor-image');

        // If currently in fullscreen state, pause debugging
        if (document.fullscreenElement === img) {
            addLog('Debug', `Monitor ${monitorIndex + 1} is currently in fullscreen, pausing debug to avoid exiting fullscreen`, 'info');
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
                addLog('Debug', `Monitor ${monitorIndex + 1} debug successful`, 'success');
            };
            newImage.onerror = function () {
                img.src = originalSrc;
                img.style.opacity = '1';
                addLog('Debug', `Monitor ${monitorIndex + 1} debug failed: Image load failed`, 'error');
            };
            newImage.src = 'data:image/png;base64,' + data.image;
        } else if (data.error) {
            img.src = originalSrc;
            img.style.opacity = '1';
            addLog('Debug', `Monitor ${monitorIndex + 1} debug failed: ${data.error}`, 'error');
        }
    } catch (error) {
        addLog('Debug', `Monitor ${monitorIndex + 1} debug failed: ${error.message}`, 'error');
    }
}

// Force redetect monitors
async function forceRedetect() {
    try {
        addLog('Monitor', 'Force redetecting monitors...', 'info');
        const serverUrl = getServerBaseUrl();
        const response = await fetch(`${serverUrl}/force-redetect`);
        const data = await response.json();

        if (data.message) {
            addLog('Monitor', data.message, 'success');

            // Display redetection results
            if (data.monitors) {
                let redetectInfo = `Redetection results:\n`;
                data.monitors.forEach(monitor => {
                    redetectInfo += `  Monitor ${monitor.index + 1}${monitor.primary ? ' (Primary)' : ''}: ${monitor.width}x${monitor.height} Position(${monitor.left},${monitor.top})\n`;
                });
                addLog('Monitor', redetectInfo, 'info');
            }

            // Refresh all monitor screenshots
            setTimeout(() => {
                refreshAllMonitors();
            }, 1000);
        } else if (data.error) {
            addLog('Monitor', 'Monitor redetection failed: ' + data.error, 'error');
        }
    } catch (error) {
        addLog('Monitor', 'Force redetection failed: ' + error.message, 'error');
    }
}

// Toggle monitor image collapse/expand state
function toggleMonitorImage(monitorIndex) {
    const monitorDiv = document.getElementById(`monitor-${monitorIndex}`);
    if (!monitorDiv) {
        addLog('Screenshot', `Container for monitor ${monitorIndex + 1} not found`, 'error');
        return;
    }

    const img = monitorDiv.querySelector('.monitor-image');
    const toggleBtn = document.getElementById(`toggle-btn-${monitorIndex}`);

    if (!img || !toggleBtn) {
        addLog('Screenshot', `Elements for monitor ${monitorIndex + 1} are incomplete`, 'error');
        return;
    }

    // Check current state
    const isCollapsed = collapsedMonitors.has(monitorIndex);

    if (isCollapsed) {
        // Expand: show image
        collapsedMonitors.delete(monitorIndex);
        monitorDiv.classList.remove('collapsed');
        img.style.display = 'block';
        img.classList.add('expanding');

        // Use requestAnimationFrame for smooth animation
        requestAnimationFrame(() => {
            img.classList.remove('expanding');
            img.classList.add('expanded');
            img.style.opacity = '1';
        });

        toggleBtn.innerHTML = '📷 Collapse';
        toggleBtn.classList.remove('collapsed');
        toggleBtn.dataset.expanded = "true";
        addLog('Screenshot', `Expanded monitor ${monitorIndex + 1}, will reload screenshot`, 'info');

        // Sync to backend
        syncCollapsedMonitorsToBackend();

        // Check if recovering from fully collapsed state, refresh display if so
        if (areAllMonitorsCollapsed() === false && totalMonitorCount > 0) {
            // Recovering from fully collapsed state, need to reload screenshots
            setTimeout(() => {
                refreshAllMonitors();
            }, 100);
        }
    } else {
        // Collapse: hide image but keep monitor element visible
        collapsedMonitors.add(monitorIndex);
        img.style.opacity = '0';
        img.classList.remove('expanded');
        img.classList.add('expanding');

        setTimeout(() => {
            img.style.display = 'none';
            monitorDiv.classList.add('collapsed');
        }, 300);

        toggleBtn.innerHTML = '👁️ Expand';
        toggleBtn.classList.add('collapsed');
        toggleBtn.dataset.expanded = "false";
        addLog('Screenshot', `Collapsed monitor ${monitorIndex + 1}, will stop retrieving screenshots`, 'info');

        // Sync to backend
        syncCollapsedMonitorsToBackend();

        // Check if all monitors are collapsed
        if (areAllMonitorsCollapsed()) {
            addLog('Screenshot', 'All monitors collapsed, will stop auto-refresh', 'info');
            // Show placeholder
            setTimeout(() => {
                displayCollapsedMonitorsPlaceholder();
            }, 300);
        }
    }
}