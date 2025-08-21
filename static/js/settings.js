// Settings Module - Quality settings and cache management functionality

// Open quality settings
async function openQualitySettings() {
    const modal = document.getElementById('qualitySettingsModal');
    modal.style.display = 'flex';

    // Get current settings
    try {
        const response = await fetch(`${getServerBaseUrl()}/quality-settings`);
        const data = await response.json();

        // Debug: Log data returned from backend
        // console.log('Quality settings data from backend:', data);
        addLog('Settings', `Received backend data: ${JSON.stringify(data)}`, 'info');

        // Get actual settings from nested settings object
        const settings = data.settings || data;

        // Populate setting values - using actual data from backend
        document.getElementById('singleMonitorWidth').value = settings.single_monitor?.max_width || settings.max_width || 1920;
        document.getElementById('singleMonitorHeight').value = settings.single_monitor?.max_height || settings.max_height || 1080;
        document.getElementById('desktopWidth').value = settings.desktop?.max_width || 1920;
        document.getElementById('desktopHeight').value = settings.desktop?.max_height || 1080;
        document.getElementById('imageFormat').value = settings.use_jpeg ? 'jpeg' : 'png';
        document.getElementById('pngQuality').value = settings.png_quality || 60;
        document.getElementById('jpegQuality').value = settings.jpeg_quality || 60;
        document.getElementById('compressionLevel').value = settings.compression_level || 6;
        document.getElementById('optimizePng').checked = settings.optimize || false;

        // Update display values - using actual values from backend
        const pngQualityValue = settings.png_quality || 60;
        const jpegQualityValue = settings.jpeg_quality || 60;
        const compressionLevelValue = settings.compression_level || 6;

        // Force update display values
        const pngQualityValueElement = document.getElementById('pngQualityValue');
        const jpegQualityValueElement = document.getElementById('jpegQualityValue');
        const compressionLevelValueElement = document.getElementById('compressionLevelValue');

        pngQualityValueElement.textContent = pngQualityValue;
        jpegQualityValueElement.textContent = jpegQualityValue;
        compressionLevelValueElement.textContent = compressionLevelValue;

        // Force repaint
        pngQualityValueElement.style.display = 'none';
        pngQualityValueElement.offsetHeight; // Trigger reflow
        pngQualityValueElement.style.display = '';

        jpegQualityValueElement.style.display = 'none';
        jpegQualityValueElement.offsetHeight; // Trigger reflow
        jpegQualityValueElement.style.display = '';

        compressionLevelValueElement.style.display = 'none';
        compressionLevelValueElement.offsetHeight; // Trigger reflow
        compressionLevelValueElement.style.display = '';

        // Debug: Log set values
        addLog('Settings', `PNG quality set to: ${pngQualityValue}, JPEG quality set to: ${jpegQualityValue}, Optimization set to: ${settings.optimize}`, 'info');

        // Set up slider event listeners
        setupQualitySettingsSliders();

    } catch (error) {
        addLog('Settings', 'Failed to retrieve quality settings: ' + error.message, 'error');
        showNotification('Failed to retrieve quality settings', 'error', 3000);
    }
}

// Close quality settings
function closeQualitySettings() {
    const modal = document.getElementById('qualitySettingsModal');
    modal.style.display = 'none';
}

// Set up quality settings sliders
function setupQualitySettingsSliders() {
    const pngQualitySlider = document.getElementById('pngQuality');
    const jpegQualitySlider = document.getElementById('jpegQuality');
    const compressionLevelSlider = document.getElementById('compressionLevel');

    // Remove existing event listeners if any
    pngQualitySlider.removeEventListener('input', pngQualitySlider._inputHandler);
    jpegQualitySlider.removeEventListener('input', jpegQualitySlider._inputHandler);
    compressionLevelSlider.removeEventListener('input', compressionLevelSlider._inputHandler);

    // Create new event handlers
    pngQualitySlider._inputHandler = function () {
        document.getElementById('pngQualityValue').textContent = this.value;
    };
    jpegQualitySlider._inputHandler = function () {
        document.getElementById('jpegQualityValue').textContent = this.value;
    };
    compressionLevelSlider._inputHandler = function () {
        document.getElementById('compressionLevelValue').textContent = this.value;
    };

    // Add event listeners
    pngQualitySlider.addEventListener('input', pngQualitySlider._inputHandler);
    jpegQualitySlider.addEventListener('input', jpegQualitySlider._inputHandler);
    compressionLevelSlider.addEventListener('input', compressionLevelSlider._inputHandler);
}

// Save quality settings
async function saveQualitySettings() {
    const settings = {
        max_width: parseInt(document.getElementById('singleMonitorWidth').value),
        max_height: parseInt(document.getElementById('singleMonitorHeight').value),
        desktop: {
            max_width: parseInt(document.getElementById('desktopWidth').value),
            max_height: parseInt(document.getElementById('desktopHeight').value)
        },
        use_jpeg: document.getElementById('imageFormat').value === 'jpeg',
        png_quality: parseInt(document.getElementById('pngQuality').value),
        jpeg_quality: parseInt(document.getElementById('jpegQuality').value),
        compression_level: parseInt(document.getElementById('compressionLevel').value),
        optimize: document.getElementById('optimizePng').checked
    };

    try {
        const response = await fetch(`${getServerBaseUrl()}/quality-settings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(settings)
        });

        if (response.ok) {
            const result = await response.json();
            addLog('Settings', 'Quality settings saved successfully', 'success');
            showNotification('Quality settings saved successfully', 'success', 3000);
            closeQualitySettings();
        } else {
            const errorData = await response.json();
            addLog('Settings', 'Failed to save quality settings: ' + (errorData.detail || 'Unknown error'), 'error');
            showNotification('Failed to save quality settings', 'error', 3000);
        }
    } catch (error) {
        addLog('Settings', 'Failed to save quality settings: ' + error.message, 'error');
        showNotification('Failed to save quality settings', 'error', 3000);
    }
}

// Open cache manager
async function openCacheManager() {
    const modal = document.getElementById('cacheManagerModal');
    modal.style.display = 'flex';

    // Debug: Log opening cache manager
    addLog('Cache', 'Opening cache manager modal', 'info');

    // Refresh cache statistics
    await refreshCacheStats();
}

// Close cache manager
function closeCacheManager() {
    const modal = document.getElementById('cacheManagerModal');
    modal.style.display = 'none';
}

// Refresh cache statistics
async function refreshCacheStats() {
    try {
        const serverUrl = getServerBaseUrl();

        // Use correct API paths
        const possiblePaths = [
            '/cache-stats',
            '/cache/stats',
            '/api/cache/stats',
            '/cache/statistics',
            '/cache/info',
            '/stats/cache',
            '/cache',
            '/api/stats',
            '/stats',
            '/system/cache',
            '/system/stats'
        ];

        let response = null;
        let apiUrl = '';

        // Try each possible path
        for (const path of possiblePaths) {
            apiUrl = `${serverUrl}${path}`;
            addLog('Cache', `Trying API path: ${apiUrl}`, 'info');

            try {
                response = await fetch(apiUrl);
                if (response.ok) {
                    addLog('Cache', `Found valid API path: ${apiUrl}`, 'success');
                    break;
                } else {
                    addLog('Cache', `Path ${apiUrl} returned ${response.status}`, 'info');
                }
            } catch (error) {
                addLog('Cache', `Request to path ${apiUrl} failed: ${error.message}`, 'info');
            }
        }

        if (!response || !response.ok) {
            addLog('Cache', `All API paths failed, last attempt: ${apiUrl}`, 'error');

            // Show message
            const currentCacheSizeElement = document.getElementById('currentCacheSize');
            const maxCacheSizeElement = document.getElementById('maxCacheSizeDisplay');
            const cacheHitRateElement = document.getElementById('cacheHitRate');
            const totalRequestsElement = document.getElementById('totalRequests');
            const cacheHitsElement = document.getElementById('cacheHits');

            if (currentCacheSizeElement) currentCacheSizeElement.textContent = 'API not implemented';
            if (maxCacheSizeElement) maxCacheSizeElement.textContent = 'API not implemented';
            if (cacheHitRateElement) cacheHitRateElement.textContent = 'API not implemented';
            if (totalRequestsElement) totalRequestsElement.textContent = 'API not implemented';
            if (cacheHitsElement) cacheHitsElement.textContent = 'API not implemented';

            showNotification('Cache management API not implemented, please contact backend developer', 'warning', 5000);
            return;
        }

        const data = await response.json();

        // Debug: Log data returned from backend
        // console.log('Cache statistics data from backend:', data);
        addLog('Cache', `Received cache data: ${JSON.stringify(data)}`, 'info');

        // Handle possible data structure differences
        const stats = data.stats || data;

        // Update UI display
        const currentSize = stats.current_size || stats.cache_size || 0;
        const maxSize = stats.max_size || stats.max_cache_size || 100;
        const hitRate = stats.hit_rate || 0;
        const totalRequests = stats.total_requests || stats.requests || 0;
        const cacheHits = stats.cache_hits || stats.hits || 0;

        // Debug: Check if DOM elements exist
        const currentCacheSizeElement = document.getElementById('currentCacheSize');
        const maxCacheSizeElement = document.getElementById('maxCacheSizeDisplay');
        const cacheHitRateElement = document.getElementById('cacheHitRate');
        const totalRequestsElement = document.getElementById('totalRequests');
        const cacheHitsElement = document.getElementById('cacheHits');

        if (!currentCacheSizeElement) {
            addLog('Cache', 'Error: Could not find currentCacheSize element', 'error');
        }
        if (!maxCacheSizeElement) {
            addLog('Cache', 'Error: Could not find maxCacheSizeDisplay element', 'error');
        }
        if (!cacheHitRateElement) {
            addLog('Cache', 'Error: Could not find cacheHitRate element', 'error');
        }
        if (!totalRequestsElement) {
            addLog('Cache', 'Error: Could not find totalRequests element', 'error');
        }
        if (!cacheHitsElement) {
            addLog('Cache', 'Error: Could not find cacheHits element', 'error');
        }

        // Update UI display
        if (currentCacheSizeElement) currentCacheSizeElement.textContent = currentSize;
        if (maxCacheSizeElement) maxCacheSizeElement.textContent = maxSize;
        if (cacheHitRateElement) cacheHitRateElement.textContent = hitRate ? `${(hitRate * 100).toFixed(1)}%` : '0%';
        if (totalRequestsElement) totalRequestsElement.textContent = totalRequests;
        if (cacheHitsElement) cacheHitsElement.textContent = cacheHits;

        // Debug: Log set values
        addLog('Cache', `Current cache count: ${currentSize}, Max cache count: ${maxSize}, Hit rate: ${hitRate}`, 'info');

        addLog('Cache', 'Cache statistics refreshed successfully', 'info');

        // Debug: Verify UI update
        setTimeout(() => {
            const currentCacheSizeElement = document.getElementById('currentCacheSize');
            if (currentCacheSizeElement) {
                addLog('Cache', `UI display value: ${currentCacheSizeElement.textContent}`, 'info');
            }
        }, 100);

    } catch (error) {
        addLog('Cache', 'Failed to refresh cache statistics: ' + error.message, 'error');
        showNotification('Failed to refresh cache statistics', 'error', 3000);
    }
}

// Clear cache
async function clearCache() {
    if (!confirm('Are you sure you want to clear all cache?\n\nThis will delete all cached screenshot data.')) {
        return;
    }

    try {
        const serverUrl = getServerBaseUrl();

        // Use correct clear cache API paths
        const possibleClearPaths = [
            '/clear-cache',
            '/cache/clear',
            '/api/cache/clear',
            '/cache/delete',
            '/cache/remove',
            '/cache'
        ];

        let response = null;
        let apiUrl = '';

        // Try each possible path
        for (const path of possibleClearPaths) {
            apiUrl = `${serverUrl}${path}`;
            addLog('Cache', `Trying clear cache API path: ${apiUrl}`, 'info');

            try {
                response = await fetch(apiUrl, { method: 'POST' });
                if (response.ok) {
                    addLog('Cache', `Found valid clear cache API path: ${apiUrl}`, 'success');
                    break;
                } else {
                    addLog('Cache', `Clear cache path ${apiUrl} returned ${response.status}`, 'info');
                }
            } catch (error) {
                addLog('Cache', `Request to clear cache path ${apiUrl} failed: ${error.message}`, 'info');
            }
        }

        if (!response || !response.ok) {
            addLog('Cache', `All clear cache API paths failed, last attempt: ${apiUrl}`, 'error');
            showNotification('Clear cache API not implemented, please contact backend developer', 'warning', 5000);
            return;
        }

        // If we get here, we found a valid API path
        const result = await response.json();
        addLog('Cache', 'Cache cleared successfully', 'success');
        showNotification('Cache cleared successfully', 'success', 3000);

        // Refresh cache statistics
        await refreshCacheStats();
    } catch (error) {
        addLog('Cache', 'Failed to clear cache: ' + error.message, 'error');
        showNotification('Failed to clear cache', 'error', 3000);
    }
}

// Test cache statistics (for debugging)
async function testCacheStats() {
    addLog('Cache', 'Starting cache statistics test...', 'info');
    await refreshCacheStats();
}
