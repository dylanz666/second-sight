// 文件管理工具模块 - 文件列表、上传、下载等功能

// 上传文件
async function uploadFiles() {
    if (selectedFiles.length === 0) {
        const warningMsg = '没有选择文件';
        addLog('上传文件', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 3000);
        return;
    }

    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '⏳ 上传中...';
        uploadProgress.style.display = 'block';

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        // 如果有选择的文件夹，添加到请求中
        if (selectedPath !== null && selectedPath !== undefined) {
            formData.append('folder_path', selectedPath);
        }

        const xhr = new XMLHttpRequest();

        // 监听上传进度
        xhr.upload.addEventListener('progress', function (event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressFill.style.width = percentComplete + '%';
                progressText.textContent = Math.round(percentComplete) + '%';
            }
        });

        // 监听上传完成
        xhr.addEventListener('load', function () {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    addLog('上传文件', response.message, 'success');
                    showNotification(response.message, 'success', 5000);

                    // 清空选择
                    selectedFiles = [];
                    document.getElementById('fileInput').value = '';
                    updateFileSelectionUI();

                    // 刷新文件列表
                    loadFileList();

                } catch (error) {
                    const errorMsg = '解析响应失败: ' + error.message;
                    addLog('上传文件', errorMsg, 'error');
                    showNotification(errorMsg, 'error', 5000);
                }
            } else {
                const errorMsg = '上传失败: HTTP ' + xhr.status;
                addLog('上传文件', errorMsg, 'error');
                showNotification(errorMsg, 'error', 5000);
            }

            // 重置UI
            uploadProgress.style.display = 'none';
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
            updateFileSelectionUI();
        });

        // 监听上传错误
        xhr.addEventListener('error', function () {
            const errorMsg = '网络错误，上传失败';
            addLog('上传文件', errorMsg, 'error');
            showNotification(errorMsg, 'error', 5000);
            uploadProgress.style.display = 'none';
            updateFileSelectionUI();
        });

        // 发送请求
        xhr.open('POST', getServerBaseUrl() + '/upload/multiple');
        xhr.send(formData);

    } catch (error) {
        const errorMsg = '上传失败: ' + error.message;
        addLog('上传文件', errorMsg, 'error');
        showNotification(errorMsg, 'error', 5000);
        uploadProgress.style.display = 'none';
        updateFileSelectionUI();
    }
}

// 加载文件列表
async function loadFileList() {
    const fileList = document.getElementById('fileList');

    fileList.innerHTML = '<div class="file-list-placeholder">加载中...</div>';

    // 构建请求URL，包含文件夹路径参数
    let url = getServerBaseUrl() + '/files';
    if (selectedPath !== null && selectedPath !== undefined) {
        url += `?folder=${encodeURIComponent(selectedPath)}`;
    }

    // 创建AbortController用于超时控制
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15秒超时

    try {
        const response = await fetch(url, {
            signal: controller.signal
        });

        // 清除超时定时器
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (data.files && data.files.length > 0) {
            fileList.innerHTML = '';

            // 显示当前文件夹信息
            const folderHeader = document.createElement('div');
            folderHeader.style.cssText = 'padding: 8px; background: #e9ecef; border-radius: 4px; margin-bottom: 8px; font-size: 12px; color: #495057;';

            // 构建完整的文件夹路径显示
            let folderDisplay;
            // 检查是否是系统路径（包括所有盘符）
            const isSystemFolder = data.current_folder && (
                data.current_folder.startsWith('/') ||
                /^[A-Z]:\\/.test(data.current_folder) // 使用正则表达式匹配任意盘符
            );

            if (isSystemFolder) {
                // 系统路径
                folderDisplay = data.current_folder;
            } else if (data.current_folder && data.current_folder !== 'Downloads') {
                // Downloads子目录
                folderDisplay = `Downloads/${data.current_folder}`;
            } else {
                // Downloads根目录
                folderDisplay = 'Downloads';
            }

            folderHeader.innerHTML = `<span>📁 当前文件夹: ${folderDisplay} (${data.files.length} 个文件)</span>`;
            fileList.appendChild(folderHeader);

            data.files.forEach(file => {
                const fileItem = createFileItem(file);
                fileList.appendChild(fileItem);
            });

            addLog('文件管理', `已加载 ${data.files.length} 个文件`, 'info');
        } else {
            // 构建完整的文件夹路径显示
            let folderDisplay;
            // 检查是否是系统路径（包括所有盘符）
            const isSystemFolder = data.current_folder && (
                data.current_folder.startsWith('/') ||
                /^[A-Z]:\\/.test(data.current_folder) || data.current_folder === '我的电脑'
            );

            if (isSystemFolder) {
                // 系统路径
                folderDisplay = data.current_folder;
                fileList.innerHTML = `<div class="file-list-placeholder">🏠 ${folderDisplay} 下暂无文件</div>`;
                return;
            }
            if (data.current_folder && data.current_folder !== 'Downloads') {
                // Downloads子目录
                folderDisplay = `Downloads/${data.current_folder}`;
            } else {
                // Downloads根目录
                folderDisplay = 'Downloads';
            }
            fileList.innerHTML = `<div class="file-list-placeholder">📁 ${folderDisplay} 文件夹下暂无文件</div>`;
        }

    } catch (error) {
        // 清除超时定时器
        clearTimeout(timeoutId);

        let userFriendlyMessage = '';

        // 根据错误类型提供用户友好的提示
        if (error.name === 'AbortError') {
            userFriendlyMessage = '请求超时，请检查网络连接或稍后重试';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            userFriendlyMessage = '无法连接到服务器，请确保服务器正在运行';
        } else if (error.message.includes('status: 403')) {
            userFriendlyMessage = '没有权限访问此目录的文件，请选择其他路径';
        } else if (error.message.includes('status: 404')) {
            userFriendlyMessage = '目录不存在或已被删除';
        } else if (error.message.includes('status: 408')) {
            userFriendlyMessage = '请求超时，请稍后重试';
        } else if (error.message.includes('status: 500')) {
            userFriendlyMessage = '服务器内部错误，请稍后重试';
        } else {
            userFriendlyMessage = '加载文件列表失败，请重试';
        }

        fileList.innerHTML = `<div class="error-placeholder">${userFriendlyMessage}</div>`;
        addLog('文件管理', userFriendlyMessage, 'error');
        showNotification(userFriendlyMessage, 'error', 3000);
    }
}

// 创建文件项
function createFileItem(file) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';

    const uploadTime = new Date(file.upload_time).toLocaleString('zh-CN', { hour12: false });

    // 转义文件名中的特殊字符，防止JavaScript语法错误
    const escapedFilename = file.filename.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

    fileItem.innerHTML = `
        <div class="file-info">
            <div class="file-name">${file.filename}</div>
            <div class="file-details">
                <span>大小: ${file.size_mb}MB</span>
                <span>日期: ${uploadTime}</span>
            </div>
        </div>
        <div class="file-actions">
            <button class="file-btn file-btn-download" onclick="downloadFile('${escapedFilename}')" title="下载">📥</button>
            <button class="file-btn file-btn-delete" onclick="deleteFile('${escapedFilename}')" title="删除">🗑️</button>
        </div>
    `;

    return fileItem;
}

// 下载文件
async function downloadFile(filename) {
    try {
        // 构建请求URL，包含文件夹路径参数
        let url = getServerBaseUrl() + `/files/${filename}`;
        if (selectedPath !== null && selectedPath !== undefined) {
            url += `?folder=${encodeURIComponent(selectedPath)}`;
        }

        const response = await fetch(url);

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            const successMsg = `文件 ${filename} 下载成功`;
            addLog('文件管理', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);
        } else {
            const errorMsg = `下载文件 ${filename} 失败: HTTP ${response.status}`;
            addLog('文件管理', errorMsg, 'error');
            showNotification(errorMsg, 'error', 3000);
        }
    } catch (error) {
        const errorMsg = `下载文件 ${filename} 失败: ${error.message}`;
        addLog('文件管理', errorMsg, 'error');
        showNotification(errorMsg, 'error', 3000);
    }
}

// 删除文件
async function deleteFile(filename) {
    if (!confirm(`确定要删除文件 "${filename}" 吗？\n\n此操作不可撤销！`)) {
        return;
    }

    try {
        // 构建请求URL，包含文件夹路径参数
        let url = getServerBaseUrl() + `/files/${filename}`;
        if (selectedPath !== null && selectedPath !== undefined) {
            url += `?folder=${encodeURIComponent(selectedPath)}`;
        }

        const response = await fetch(url, {
            method: 'DELETE'
        });

        if (response.ok) {
            const successMsg = `文件 ${filename} 删除成功`;
            addLog('文件管理', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);

            // 刷新文件列表
            loadFileList();
        } else {
            const errorData = await response.json();
            const errorMsg = `删除文件 ${filename} 失败: ${errorData.detail || '未知错误'}`;
            addLog('文件管理', errorMsg, 'error');
            showNotification(errorMsg, 'error', 3000);
        }
    } catch (error) {
        const errorMsg = `删除文件 ${filename} 失败: ${error.message}`;
        addLog('文件管理', errorMsg, 'error');
        showNotification(errorMsg, 'error', 3000);
    }
}

// 删除文件夹
async function deleteFolder(folderPath) {
    const decodedPath = decodeURIComponent(folderPath);

    // 检查是否为关键系统路径
    const criticalPaths = ['C:\\', 'D:\\', 'E:\\', 'F:\\', '/', '/home', '/root', 'Downloads'];
    if (criticalPaths.some(criticalPath => decodedPath === criticalPath || decodedPath.startsWith(criticalPath + '/'))) {
        showNotification('不能删除系统关键目录', 'error', 3000);
        addLog('文件管理', `尝试删除关键目录被阻止: ${decodedPath}`, 'warning');
        return;
    }

    // 确认删除
    if (!confirm(`确定要删除文件夹 "${decodedPath}" 吗？\n\n此操作不可撤销！`)) {
        return;
    }

    try {
        const response = await fetch(`${getServerBaseUrl()}/delete_folder`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                folder_path: decodedPath
            })
        });

        if (response.ok) {
            const result = await response.json();
            showNotification(`文件夹 "${decodedPath}" 删除成功`, 'success', 3000);
            addLog('文件管理', `删除文件夹成功: ${decodedPath}`, 'info');

            // 如果删除的是当前选中的路径，清除选择
            if (selectedPath === decodedPath) {
                selectedPath = null;
                selectedPathName = null;
                updateCreateFolderLocation();
            }

            // 刷新路径列表
            refreshPathList();
        } else {
            const errorData = await response.json();
            showNotification(`删除失败: ${errorData.detail || '未知错误'}`, 'error', 3000);
            addLog('文件管理', `删除文件夹失败: ${decodedPath} - ${errorData.detail}`, 'error');
        }
    } catch (error) {
        console.error('删除文件夹时发生错误:', error);
        showNotification('删除文件夹时发生网络错误', 'error', 3000);
        addLog('文件管理', `删除文件夹网络错误: ${decodedPath} - ${error.message}`, 'error');
    }
}

// 更新文件选择UI
function updateFileSelectionUI() {
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadInfo = document.getElementById('uploadInfo');

    if (selectedFiles.length > 0) {
        uploadBtn.disabled = false;
        uploadInfo.style.display = 'block';

        // 创建文件列表HTML
        let fileListHTML = `<div style="margin-bottom: 8px;"><span style="font-weight: bold;">已选择 ${selectedFiles.length} 个文件:</span></div>`;

        selectedFiles.forEach((file, index) => {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            fileListHTML += `
                <div class="selected-file-item">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-size">(${sizeMB}MB)</div>
                    <button 
                        class="delete-btn"
                        onclick="removeSelectedFile(${index})" 
                        title="删除此文件"
                    >
                        ✕
                    </button>
                </div>
            `;
        });

        uploadInfo.innerHTML = fileListHTML;

        // 更新按钮文本，表示可以上传
        uploadBtn.innerHTML = '⬆️ 上传';
    } else {
        uploadBtn.disabled = false; // 按钮不再禁用，而是用于选择文件
        uploadInfo.style.display = 'none';

        // 更新按钮文本，表示可以选择文件
        uploadBtn.innerHTML = '上传文件';
    }
}

// 删除选中的文件
function removeSelectedFile(fileIndex) {
    if (fileIndex >= 0 && fileIndex < selectedFiles.length) {
        const removedFile = selectedFiles[fileIndex];
        selectedFiles.splice(fileIndex, 1);

        // 显示删除成功消息
        const successMsg = `已从上传列表中移除: ${removedFile.name}`;
        addLog('文件管理', successMsg, 'info');
        showNotification(successMsg, 'info', 2000);

        // 更新UI
        updateFileSelectionUI();
    }
} 