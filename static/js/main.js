// 主入口文件 - 初始化逻辑和事件监听器

// 初始化
document.addEventListener('DOMContentLoaded', function () {
    addLog('系统', '页面加载完成', 'success');

    // 设置全屏状态监听器
    setupFullscreenListener();

    // 重置被收起的显示器状态
    resetCollapsedMonitors();

    // 初始化趋势图
    drawMemoryTrendChart();
    drawCpuTrendChart(); // 初始化CPU趋势图
    drawNetworkLatencyTrendChart(); // 初始化网络延迟趋势图
    updateTrendChartTooltip();

    // 初始化远程控制功能
    if (typeof initRemoteControl === 'function') {
        initRemoteControl();
    }

    // 检测环境并显示信息
    const environment = detectEnvironment();
    const serverUrl = getServerBaseUrl();
    addLog('系统', `服务器地址: ${serverUrl}`, 'info');

    // 检查服务器状态
    checkServerStatus().then(serverAvailable => {
        if (serverAvailable) {
            connectWebSocket();
            refreshAllMonitors(); // 默认加载多显示器模式
            
            // 启动自动刷新（默认行为）
            startAutoRefresh();
            
            // 更新按钮状态
            const autoRefreshBtn = document.getElementById('autoRefreshBtn');
            if (autoRefreshBtn) {
                autoRefreshBtn.textContent = '⏸️ 停止刷新';
                autoRefreshBtn.className = 'btn btn-danger';
            }
        } else {
            addLog('系统', '请先启动服务器: python server.py', 'warning');
        }
    });

    // 文件选择事件监听
    const fileInput = document.getElementById('fileInput');
    const pathInput = document.getElementById('pathInput');

    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelection);
    }

    if (pathInput) {
        pathInput.addEventListener('change', handlePathSelectionEvent);
    }

    // 初始化上传按钮状态
    updateFileSelectionUI();

    // 初始化路径选择按钮状态
    updatePathSelectionUI();

    // 直接为路径按钮添加点击事件监听器
    const pathBtn = document.getElementById('pathBtn');
    if (pathBtn) {
        pathBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            // 总是打开模态框，无论是否已有选择的路径
            openPathModal();
        });
    } else {
        console.error('pathBtn element not found!');
    }

    // 自动加载文件列表，无需点击刷新按钮
    loadFileList();

    // 添加点击外部关闭模态框的事件监听
    document.addEventListener('click', function (event) {
        const modal = document.getElementById('pathModal');
        const createFolderModal = document.getElementById('createFolderModal');
        if (createFolderModal && createFolderModal.style.display === 'flex') {
            return;
        }

        if (modal && modal.style.display === 'flex') {
            const modalContent = modal.querySelector('.modal-content');
            if (modalContent && !modalContent.contains(event.target)) {
                closePathModal();
            }
        }
    });

    // 添加ESC键关闭模态框的事件监听
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            const modal = document.getElementById('pathModal');
            if (modal && modal.style.display === 'flex') {
                closePathModal();
            }
        }
    });
});

// 处理路径选择事件 (保留用于文件选择的情况)
function handlePathSelectionEvent(event) {
    const file = event.target.files[0];

    if (!file) {
        return;
    }

    // 获取文件名作为路径提示
    const fileName = file.name;

    // 使用prompt让用户确认或修改路径
    const customPath = prompt(`检测到文件: ${fileName}\n请输入目标路径 (例如: Documents/MyFiles 或留空使用默认Downloads目录):`);

    if (customPath !== null) { // 用户点击了确定
        if (customPath.trim() === '') {
            // 用户输入了空路径，清除选择
            clearSelectedPath();
        } else {
            // 设置选中的路径
            selectedPath = customPath.trim();

            // 更新UI显示
            updatePathSelectionUI();

            // 显示成功消息
            const successMsg = `已设置目标路径: ${selectedPath}`;
            addLog('路径选择', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);

            // 自动刷新文件列表
            loadFileList();
        }
    }

    // 清除文件选择，避免影响后续操作
    event.target.value = '';
}

// 更新路径选择UI
function updatePathSelectionUI() {
    const pathInfo = document.getElementById('pathInfo');
    const currentPath = document.getElementById('currentPath');
    const pathBtn = document.getElementById('pathBtn');

    if (selectedPath !== null && selectedPath !== undefined) {
        pathInfo.style.display = 'block';

        // 显示路径信息
        let displayPath;
        // 检查是否是系统路径（包括所有盘符）
        const isSystemPath = selectedPath && selectedPath !== '' && (
            selectedPath.startsWith('/') ||
            /^[A-Z]:\\/.test(selectedPath) // 使用正则表达式匹配任意盘符
        );

        if (selectedPath === '我的电脑') {
            // 我的电脑路径
            displayPath = '我的电脑';
            pathBtn.innerHTML = '已选路径';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        } else if (isSystemPath) {
            // 系统路径
            displayPath = selectedPath;
            pathBtn.innerHTML = '已选路径';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        } else if (selectedPath === '') {
            // 默认Downloads路径（空字符串）
            displayPath = 'Downloads';
            pathBtn.innerHTML = '已选路径';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        } else {
            // Downloads子目录路径
            displayPath = `Downloads/${selectedPath}`;
            pathBtn.innerHTML = '已选路径';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        }

        currentPath.textContent = displayPath;
    } else {
        pathInfo.style.display = 'none';
        pathBtn.innerHTML = '设置路径';
        pathBtn.style.background = '';
    }
}

// 清除选中的路径
function clearSelectedPath() {
    selectedPath = null;
    selectedPathName = null;

    // 清除所有路径项的选中状态
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });

    updatePathSelectionUI();

    // 更新创建文件夹位置显示
    updateCreateFolderLocation();

    // 隐藏目标路径元素
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'none';
    }

    const successMsg = '已清除路径设置，返回默认Downloads目录';
    addLog('路径选择', successMsg, 'info');
    showNotification(successMsg, 'info', 3000);

    // 自动刷新文件列表
    loadFileList();
}

// 更新创建文件夹位置显示
function updateCreateFolderLocation() {
    const createFolderLocation = document.getElementById('createFolderLocation');
    if (!createFolderLocation) return;

    let locationText = '';
    if (selectedPath !== null && selectedPath !== undefined) {
        // 检查是否是系统路径（包括所有盘符）
        const isSystemPath = selectedPath && selectedPath !== '' && (
            selectedPath.startsWith('/') ||
            /^[A-Z]:\\/.test(selectedPath) // 使用正则表达式匹配任意盘符
        );

        if (selectedPath === '我的电脑') {
            // 我的电脑路径
            locationText = '我的电脑';
        } else if (isSystemPath) {
            // 系统路径
            locationText = selectedPath;
        } else if (selectedPath === '') {
            // 默认Downloads路径（空字符串）
            locationText = 'Downloads';
        } else {
            // Downloads子目录路径
            locationText = `Downloads/${selectedPath}`;
        }
    } else {
        // 没有选择路径时，默认显示Downloads
        locationText = 'Downloads';
    }

    createFolderLocation.textContent = locationText;
}

// 显示创建文件夹对话框
function showCreateFolderDialog() {
    const modal = document.getElementById('createFolderModal');
    modal.style.display = 'flex';

    // 更新创建文件夹位置显示
    updateCreateFolderLocation();

    // 聚焦到输入框
    const folderNameInput = document.getElementById('folderNameInput');
    if (folderNameInput) {
        folderNameInput.focus();
    }
}

// 关闭创建文件夹对话框
function closeCreateFolderDialog() {
    const modal = document.getElementById('createFolderModal');
    modal.style.display = 'none';

    // 清空输入框
    const folderNameInput = document.getElementById('folderNameInput');
    if (folderNameInput) {
        folderNameInput.value = '';
    }
}

// 创建文件夹
async function createFolder() {
    const folderNameInput = document.getElementById('folderNameInput');
    const folderName = folderNameInput.value.trim();

    if (!folderName) {
        showNotification('请输入文件夹名称', 'warning', 3000);
        return;
    }

    // 检查文件夹名称是否包含非法字符
    const invalidChars = /[<>:"/\\|?*]/;
    if (invalidChars.test(folderName)) {
        showNotification('文件夹名称包含非法字符', 'error', 3000);
        return;
    }

    try {
        const response = await fetch(`${getServerBaseUrl()}/create_folder`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                folder_name: folderName,
                parent_path: selectedPath || ''
            })
        });

        if (response.ok) {
            const result = await response.json();
            showNotification(`文件夹 "${folderName}" 创建成功`, 'success', 3000);
            addLog('文件管理', `创建文件夹成功: ${folderName}`, 'info');

            // 关闭对话框
            closeCreateFolderDialog();

            // 刷新路径列表
            refreshPathList();
        } else {
            const errorData = await response.json();
            showNotification(`创建文件夹失败: ${errorData.detail || '未知错误'}`, 'error', 3000);
            addLog('文件管理', `创建文件夹失败: ${folderName} - ${errorData.detail}`, 'error');
        }
    } catch (error) {
        console.error('创建文件夹时发生错误:', error);
        showNotification('创建文件夹时发生网络错误', 'error', 3000);
        addLog('文件管理', `创建文件夹网络错误: ${folderName} - ${error.message}`, 'error');
    }
}

// 设置路径输入框事件监听器
function setupPathInputEventListeners() {
    const pathInput = document.getElementById('modalCurrentPathInput');
    if (!pathInput) return;

    // 移除现有的事件监听器
    pathInput.removeEventListener('click', pathInputClickHandler);
    pathInput.removeEventListener('dblclick', pathInputDblClickHandler);
    pathInput.removeEventListener('keydown', pathInputKeydownHandler);
    pathInput.removeEventListener('contextmenu', pathInputContextMenuHandler);

    // 添加新的事件监听器
    pathInput.addEventListener('click', pathInputClickHandler);
    pathInput.addEventListener('dblclick', pathInputDblClickHandler);
    pathInput.addEventListener('keydown', pathInputKeydownHandler);
    pathInput.addEventListener('contextmenu', pathInputContextMenuHandler);
}

// 路径输入框点击处理
function pathInputClickHandler(event) {
    event.preventDefault();
    event.stopPropagation();
    // 可以在这里添加点击处理逻辑
}

// 路径输入框双击处理
function pathInputDblClickHandler(event) {
    event.preventDefault();
    event.stopPropagation();
    // 可以在这里添加双击处理逻辑
}

// 路径输入框键盘处理
function pathInputKeydownHandler(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        // 可以在这里添加回车处理逻辑
    }
}

// 路径输入框右键菜单处理
function pathInputContextMenuHandler(event) {
    event.preventDefault();
    event.stopPropagation();
    // 可以在这里添加右键菜单处理逻辑
}

// 刷新路径列表
function refreshPathList() {
    showModalLoading();

    // 检查是否是系统路径（包括所有盘符）
    // 注意：只有明确的系统路径才被视为系统路径，空字符串默认是Downloads
    const isSystemPath = currentModalPath && currentModalPath !== '' && (
        currentModalPath.startsWith('/') ||
        /^[A-Z]:\\/.test(currentModalPath) ||
        currentModalPath === '我的电脑'
    );
    console.log('DEBUG: refreshPathList - currentModalPath:', currentModalPath);
    console.log('DEBUG: refreshPathList - isSystemPath:', isSystemPath);

    if (isSystemPath) {
        // 如果是系统路径，调用系统目录加载函数
        if (currentModalPath === '我的电脑') {
            loadSystemDirectories('');
        } else {
            loadSystemDirectories(currentModalPath);
        }
    } else {
        // 如果是Downloads路径或空路径，调用Downloads目录加载函数
        loadModalPathList(currentModalPath);
    }
}

// 选择当前路径并关闭模态框
function selectCurrentPath() {
    // 在弹窗中未选择文件夹的情况下，使用与 currentModalPath 相同的值
    let finalSelectedPath;
    if (selectedPath !== null && selectedPath !== undefined && selectedPath !== '') {
        // 用户已经选中了路径，使用选中的路径
        finalSelectedPath = selectedPath;
    } else {
        // 用户没有选中路径，使用当前浏览的路径
        finalSelectedPath = currentModalPath || '';
    }
    // 设置选中的路径
    selectedPath = finalSelectedPath;

    // 更新UI
    updatePathSelectionUI();

    // 隐藏目标路径元素
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'none';
    }

    // 直接关闭模态框，不调用 closePathModal() 避免恢复原始状态
    const modal = document.getElementById('pathModal');
    modal.style.display = 'none';

    // 显示成功消息
    let pathDisplay;
    // 检查是否是系统路径（包括所有盘符）
    const isSystemPath = selectedPath && selectedPath !== '' && (
        selectedPath.startsWith('/') ||
        /^[A-Z]:\\/.test(selectedPath) // 使用正则表达式匹配任意盘符
    );

    if (isSystemPath) {
        // 系统路径
        pathDisplay = selectedPath;
    } else {
        // Downloads路径（包括空字符串表示Downloads根目录）
        pathDisplay = selectedPath === '' ? 'Downloads' : `Downloads/${selectedPath}`;
    }
    const successMsg = `已选文件夹: ${pathDisplay}`;
    addLog('路径选择', successMsg, 'info');
    showNotification(successMsg, 'info', 3000);

    // 自动刷新文件列表到选中的路径
    loadFileList();

    // 清除保存的模态框状态
    modalOriginalPath = null;
    modalOriginalPathName = null;
    modalOriginalCurrentPath = null;
} 