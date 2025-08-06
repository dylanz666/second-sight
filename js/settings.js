// 设置模块 - 质量设置和缓存管理功能

// 打开质量设置
async function openQualitySettings() {
    const modal = document.getElementById('qualitySettingsModal');
    modal.style.display = 'flex';

            // 获取当前设置
        try {
            const response = await fetch(`${getServerBaseUrl()}/quality-settings`);
            const data = await response.json();
            
            // 调试：记录后端返回的数据
            console.log('后端返回的质量设置数据:', data);
            addLog('设置', `获取到后端数据: ${JSON.stringify(data)}`, 'info');

            // 从嵌套的settings对象中获取实际设置
            const settings = data.settings || data;
            
            // 填充设置值 - 使用从后端获取的实际数据
            document.getElementById('singleMonitorWidth').value = settings.single_monitor?.max_width || settings.max_width || 1920;
            document.getElementById('singleMonitorHeight').value = settings.single_monitor?.max_height || settings.max_height || 1080;
            document.getElementById('desktopWidth').value = settings.desktop?.max_width || 1920;
            document.getElementById('desktopHeight').value = settings.desktop?.max_height || 1080;
            document.getElementById('imageFormat').value = settings.use_jpeg ? 'jpeg' : 'png';
            document.getElementById('pngQuality').value = settings.png_quality || 60;
            document.getElementById('jpegQuality').value = settings.jpeg_quality || 60;
            document.getElementById('compressionLevel').value = settings.compression_level || 6;
            document.getElementById('optimizePng').checked = settings.optimize || false;

            // 更新显示值 - 使用从后端获取的实际值
            const pngQualityValue = settings.png_quality || 60;
            const jpegQualityValue = settings.jpeg_quality || 60;
            const compressionLevelValue = settings.compression_level || 6;
            
            // 强制更新显示值
            const pngQualityValueElement = document.getElementById('pngQualityValue');
            const jpegQualityValueElement = document.getElementById('jpegQualityValue');
            const compressionLevelValueElement = document.getElementById('compressionLevelValue');
            
            pngQualityValueElement.textContent = pngQualityValue;
            jpegQualityValueElement.textContent = jpegQualityValue;
            compressionLevelValueElement.textContent = compressionLevelValue;
            
            // 强制触发重绘
            pngQualityValueElement.style.display = 'none';
            pngQualityValueElement.offsetHeight; // 触发重排
            pngQualityValueElement.style.display = '';
            
            jpegQualityValueElement.style.display = 'none';
            jpegQualityValueElement.offsetHeight; // 触发重排
            jpegQualityValueElement.style.display = '';
            
            compressionLevelValueElement.style.display = 'none';
            compressionLevelValueElement.offsetHeight; // 触发重排
            compressionLevelValueElement.style.display = '';
            
            // 调试：记录设置后的值
            addLog('设置', `PNG质量设置为: ${pngQualityValue}, JPEG质量设置为: ${jpegQualityValue}, 优化设置为: ${settings.optimize}`, 'info');

        // 设置滑块事件监听器
        setupQualitySettingsSliders();

    } catch (error) {
        addLog('设置', '获取质量设置失败: ' + error.message, 'error');
        showNotification('获取质量设置失败', 'error', 3000);
    }
}

// 关闭质量设置
function closeQualitySettings() {
    const modal = document.getElementById('qualitySettingsModal');
    modal.style.display = 'none';
}

// 设置质量设置滑块
function setupQualitySettingsSliders() {
    const pngQualitySlider = document.getElementById('pngQuality');
    const jpegQualitySlider = document.getElementById('jpegQuality');
    const compressionLevelSlider = document.getElementById('compressionLevel');

    // 移除现有的事件监听器（如果存在）
    pngQualitySlider.removeEventListener('input', pngQualitySlider._inputHandler);
    jpegQualitySlider.removeEventListener('input', jpegQualitySlider._inputHandler);
    compressionLevelSlider.removeEventListener('input', compressionLevelSlider._inputHandler);

    // 创建新的事件处理器
    pngQualitySlider._inputHandler = function() {
        document.getElementById('pngQualityValue').textContent = this.value;
    };
    jpegQualitySlider._inputHandler = function() {
        document.getElementById('jpegQualityValue').textContent = this.value;
    };
    compressionLevelSlider._inputHandler = function() {
        document.getElementById('compressionLevelValue').textContent = this.value;
    };

    // 添加事件监听器
    pngQualitySlider.addEventListener('input', pngQualitySlider._inputHandler);
    jpegQualitySlider.addEventListener('input', jpegQualitySlider._inputHandler);
    compressionLevelSlider.addEventListener('input', compressionLevelSlider._inputHandler);
}

// 保存质量设置
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
            addLog('设置', '质量设置保存成功', 'success');
            showNotification('质量设置保存成功', 'success', 3000);
            closeQualitySettings();
        } else {
            const errorData = await response.json();
            addLog('设置', '保存质量设置失败: ' + (errorData.detail || '未知错误'), 'error');
            showNotification('保存质量设置失败', 'error', 3000);
        }
    } catch (error) {
        addLog('设置', '保存质量设置失败: ' + error.message, 'error');
        showNotification('保存质量设置失败', 'error', 3000);
    }
}

// 打开缓存管理
async function openCacheManager() {
    const modal = document.getElementById('cacheManagerModal');
    modal.style.display = 'flex';

    // 刷新缓存统计
    await refreshCacheStats();
}

// 关闭缓存管理
function closeCacheManager() {
    const modal = document.getElementById('cacheManagerModal');
    modal.style.display = 'none';
}

// 刷新缓存统计
async function refreshCacheStats() {
    try {
        const response = await fetch(`${getServerBaseUrl()}/cache/stats`);
        const stats = await response.json();

        document.getElementById('currentCacheSize').textContent = stats.current_size || 0;
        document.getElementById('maxCacheSizeDisplay').textContent = stats.max_size || 100;
        document.getElementById('cacheHitRate').textContent = stats.hit_rate ? `${(stats.hit_rate * 100).toFixed(1)}%` : '0%';
        document.getElementById('totalRequests').textContent = stats.total_requests || 0;
        document.getElementById('cacheHits').textContent = stats.cache_hits || 0;

        addLog('缓存', '缓存统计刷新成功', 'info');
    } catch (error) {
        addLog('缓存', '刷新缓存统计失败: ' + error.message, 'error');
        showNotification('刷新缓存统计失败', 'error', 3000);
    }
}

// 清除缓存
async function clearCache() {
    if (!confirm('确定要清除所有缓存吗？\n\n这将删除所有缓存的截图数据。')) {
        return;
    }

    try {
        const response = await fetch(`${getServerBaseUrl()}/cache/clear`, {
            method: 'POST'
        });

        if (response.ok) {
            const result = await response.json();
            addLog('缓存', '缓存清除成功', 'success');
            showNotification('缓存清除成功', 'success', 3000);

            // 刷新缓存统计
            await refreshCacheStats();
        } else {
            const errorData = await response.json();
            addLog('缓存', '清除缓存失败: ' + (errorData.detail || '未知错误'), 'error');
            showNotification('清除缓存失败', 'error', 3000);
        }
    } catch (error) {
        addLog('缓存', '清除缓存失败: ' + error.message, 'error');
        showNotification('清除缓存失败', 'error', 3000);
    }
} 