// 文件管理模块 - 文件上传和路径选择功能

// 处理合并后的上传文件按钮
function handleFileUpload() {
    // 如果没有选择文件，先触发文件选择
    if (selectedFiles.length === 0) {
        document.getElementById('fileInput').click();
        return;
    }

    // 如果已经有文件选择，直接上传
    uploadFiles();
}

// 处理文件选择
function handleFileSelection(event) {
    const files = Array.from(event.target.files);
    const oversizedFiles = [];

    selectedFiles = files.filter(file => {
        // 检查文件大小 (100MB限制)
        if (file.size > 100 * 1024 * 1024) {
            oversizedFiles.push(file.name);
            return false;
        }
        return true;
    });

    // 显示超大文件的警告
    if (oversizedFiles.length > 0) {
        const warningMsg = `文件 ${oversizedFiles.join(', ')} 超过100MB限制，已跳过`;
        addLog('上传文件', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 4000);
    }

    updateFileSelectionUI();
}

// 处理路径选择按钮点击 - 现在显示下拉框
// 打开路径选择模态框
function openPathModal() {
    const modal = document.getElementById('pathModal');

    if (!modal) {
        console.error('Modal element not found!');
        return;
    }

    modal.style.display = 'flex';

    // 重新显示目标路径元素
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'block';
    }

    // 重置路径导航历史
    pathHistory = [];

    // 保存打开模态框时的原始状态
    modalOriginalPath = selectedPath;
    modalOriginalPathName = selectedPathName;
    modalOriginalCurrentPath = currentModalPath;

    // 设置当前模态框路径为已选择的路径
    currentModalPath = selectedPath || '';

    // 立即更新路径显示，确保显示正确的路径
    updateModalPathDisplay(selectedPath);

    // 重新设置路径输入框的事件监听器
    // 使用setTimeout确保DOM完全准备好
    setTimeout(() => {
        setupPathInputEventListeners();
    }, 100);

    // 检查是否是系统路径（包括所有盘符）
    // 注意：只有明确的系统路径才被视为系统路径，空字符串默认是Downloads
    const isSystemPath = selectedPath && selectedPath !== '' && (
        selectedPath.startsWith('/') ||
        /^[A-Z]:\\/.test(selectedPath) // 使用正则表达式匹配任意盘符
    );

    if (isSystemPath) {
        // 如果是系统路径，调用系统目录加载函数
        loadSystemDirectories(selectedPath);
    } else {
        // 如果是Downloads路径或空路径，调用Downloads目录加载函数
        loadModalPathList(selectedPath || '');
    }
}

// 关闭路径选择模态框
function closePathModal() {
    const modal = document.getElementById('pathModal');
    modal.style.display = 'none';

    // 恢复打开模态框时的原始状态
    // 注意：即使原始状态是null，也要恢复
    selectedPath = modalOriginalPath;
    selectedPathName = modalOriginalPathName;
    currentModalPath = modalOriginalCurrentPath;

    // 恢复模态框中的当前路径显示
    if (modalOriginalCurrentPath !== null) {
        updateModalPathDisplay(modalOriginalCurrentPath);
    }

    // 更新文件管理卡片上的路径显示
    updatePathSelectionUI();

    // 刷新文件列表到原始路径
    loadFileList();

    // 清除保存的状态
    modalOriginalPath = null;
    modalOriginalPathName = null;
    modalOriginalCurrentPath = null;
}

// 加载系统目录列表
async function loadSystemDirectories(path = '', restoreSelection = true) {

    const pathList = document.getElementById('modalPathList');
    const upButton = document.getElementById('upButton');

    // 保存当前选中的路径信息，用于在加载后恢复选中状态
    const currentSelectedPath = restoreSelection ? selectedPath : null;

    // 显示加载状态
    pathList.innerHTML = '<div class="loading-placeholder">正在加载系统目录列表...</div>';

    // 构建请求URL
    const url = path ? `${getServerBaseUrl()}/system-directories?path=${encodeURIComponent(path)}` : `${getServerBaseUrl()}/system-directories`;

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

        // 更新当前路径显示 - 优先使用服务器返回的路径，如果为空则使用传入的路径
        currentModalPath = data.current_path || path;

        // 如果服务器返回的路径为空，但我们有已选择的路径，则使用已选择的路径
        // 但是当导航到根目录时（path为空），始终显示系统根目录
        const displayPath = data.current_path ? data.current_path :
            (path === '' ? '我的电脑' :
                (selectedPath ? selectedPath : '我的电脑'));

        // 更新路径显示 - 使用当前模态框路径
        updateModalPathDisplay(displayPath);

        // 更新上级目录按钮

        // 始终显示上级目录按钮
        upButton.style.display = 'inline-block';

        if (data.can_go_up) {
            upButton.title = '返回上级目录';
            upButton.innerText = '⬆️ 上级目录';
            upButton.onclick = function () {
                // 使用服务器返回的父路径，如果为空则使用当前路径的父路径
                const parentPath = data.parent_path || '';

                // 立即更新当前路径显示
                updateModalPathDisplay(parentPath);

                // 更新当前模态框路径
                currentModalPath = parentPath;

                // 清除选中的路径，避免默认选中文件夹
                selectedPath = null;
                selectedPathName = null;

                // 更新创建文件夹位置显示
                updateCreateFolderLocation();

                loadSystemDirectories(parentPath, false);
            };
        } else {
            // 在根目录时显示禁用状态的上级目录按钮
            upButton.title = '已在根目录';
            upButton.innerText = '⬆️ 上级目录';
            upButton.onclick = function () {
                showNotification('已在根目录，无法继续向上导航' + data.can_go_up + "-" + data.detail?.can_go_up, 'warning', 3000);
                addLog('路径选择', '已在根目录，无法继续向上导航', 'warning');
            };
        }

        // 填充路径列表
        populateSystemPathList(data.items, currentSelectedPath);

        // 隐藏loading
        hideModalLoading();

    } catch (error) {
        // 清除超时定时器
        clearTimeout(timeoutId);

        console.error('加载系统目录列表失败:', error);

        let userFriendlyMessage = '';

        // 根据错误类型提供用户友好的提示
        if (error.name === 'AbortError') {
            userFriendlyMessage = '请求超时，请检查网络连接或稍后重试';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            userFriendlyMessage = '无法连接到服务器，请确保服务器正在运行';
        } else if (error.message.includes('status: 403')) {
            userFriendlyMessage = '没有权限访问此目录';

            // 对于403错误，更新当前路径为尝试访问的路径，以便正确导航
            currentModalPath = path;

            // 更新路径显示
            updateModalPathDisplay(currentModalPath);
        } else if (error.message.includes('status: 404')) {
            userFriendlyMessage = '目录不存在或已被删除';

            // 对于404错误，更新当前路径为尝试访问的路径，以便正确导航
            currentModalPath = path;

            // 更新路径显示
            updateModalPathDisplay(currentModalPath);
        } else if (error.message.includes('status: 408')) {
            userFriendlyMessage = '请求超时，请稍后重试';
        } else if (error.message.includes('status: 500')) {
            userFriendlyMessage = '服务器内部错误，请稍后重试';
        } else {
            userFriendlyMessage = '加载目录列表失败，请重试';
        }

        pathList.innerHTML = `
            <div class="error-placeholder">
                ${userFriendlyMessage}
            </div>
        `;

        // 配置上级目录按钮 - 在错误情况下也要确保按钮可用
        const upButton = document.getElementById('upButton');
        upButton.style.display = 'inline-block';
        upButton.title = '返回上级目录';
        upButton.innerText = '⬆️ 上级目录';
        upButton.onclick = navigateUp;

        showNotification(userFriendlyMessage, 'error', 3000);
        addLog('路径选择', userFriendlyMessage, 'error');

        // 隐藏loading
        hideModalLoading();
    }
}

// 填充系统路径列表
function populateSystemPathList(items, currentSelectedPath) {
    const pathList = document.getElementById('modalPathList');

    if (!items || items.length === 0) {
        pathList.innerHTML = '<div class="empty-placeholder">当前目录下无文件夹</div>';
        return;
    }

    let html = '';

    items.forEach(item => {
        // 根据类型选择不同的图标
        let icon = '📁'; // 默认文件夹图标
        if (item.type === 'drive') {
            icon = '💾'; // 盘符图标
        }

        const itemPath = item.path;

        // 转义路径中的特殊字符，防止JavaScript语法错误
        const escapedPath = itemPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const escapedName = item.name.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

        // 处理文件夹数量显示：-1表示超时或错误，显示为"-"
        const folderCountDisplay = item.file_count === -1 ? '-' : (item.file_count || 0);

        html += `
            <div class="path-item" 
                 onclick="event.stopPropagation(); selectSystemPathItem(this, '${escapedPath}', '${escapedName}')" 
                 title="单击选择: ${escapedName}">
                <div class="path-name">
                    ${item.name}
                </div>
                <div class="file-count">${folderCountDisplay}</div>
                <div class="path-item-actions">
                    <button class="btn btn-primary" 
                            style="padding: 2px 6px; font-size: 10px; height: 20px; line-height: 1.2; border-radius: 3px; margin-right: 4px;"
                            onclick="event.stopPropagation(); navigateToSystemPath('${escapedPath}')" 
                            title="进入文件夹: ${escapedName}">
                        进入
                    </button>
                </div>
            </div>
        `;
    });

    pathList.innerHTML = html;

    // 恢复选中状态，确保与图片中的选中效果一致
    if (currentSelectedPath && currentSelectedPath.trim() !== '') {
        const pathItems = pathList.querySelectorAll('.path-item');
        pathItems.forEach(item => {
            try {
                const itemPath = item.getAttribute('onclick').match(/'([^']+)'/)[1];
                // 解码转义的路径进行比较
                const decodedPath = itemPath.replace(/\\\\/g, '\\').replace(/\\'/g, "'");
                if (decodedPath === currentSelectedPath) {
                    item.classList.add('selected');
                }
            } catch (e) {
                console.warn('Error parsing item path:', e);
            }
        });
    }
}

// 选中系统路径项
function selectSystemPathItem(element, path, name) {

    // 检查当前项是否已经被选中
    const isCurrentlySelected = element.classList.contains('selected');

    // 移除所有其他项的选中状态
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });

    if (!isCurrentlySelected) {
        // 如果当前项未被选中，则选中它
        element.classList.add('selected');

        // 存储选中的路径信息
        selectedPath = path || '';
        selectedPathName = name || '';

        // 更新模态框中的当前路径显示
        updateModalPathDisplay(path || '');

        // 显示选择成功通知
        const selectMsg = `已选文件夹: ${name || path}`;
        addLog('路径选择', selectMsg, 'info');
        showNotification(selectMsg, 'success', 2000);
    } else {
        // 如果当前项已经被选中，则取消选择
        selectedPath = null;
        selectedPathName = null;

        // 更新模态框中的当前路径显示
        updateModalPathDisplay('/');

        // 更新创建文件夹位置显示
        updateCreateFolderLocation();

        // 显示取消选择通知
        const cancelMsg = '取消选择文件夹';
        addLog('路径选择', cancelMsg, 'info');
        showNotification(cancelMsg, 'info', 2000);

        // 自动刷新文件列表
        loadFileList();
    }

    // 更新路径选择UI
    updatePathSelectionUI();
}

// 导航到系统路径
function navigateToSystemPath(path) {

    // 立即更新当前路径显示
    updateModalPathDisplay(path);

    // 更新当前模态框路径
    currentModalPath = path;

    // 更新创建文件夹位置显示
    updateCreateFolderLocation();

    // 显示加载状态
    showModalLoading();

    // 然后加载目录内容
    loadSystemDirectories(path);
}

// 删除系统路径
async function deleteSystemPath(path) {
    const decodedPath = decodeURIComponent(path);

    // 检查是否为关键系统路径
    const criticalPaths = ['C:\\', 'D:\\', 'E:\\', 'F:\\', '/', '/home', '/root', '我的电脑'];
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