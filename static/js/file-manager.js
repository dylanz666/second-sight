// File management module - File upload and path selection functions

// Handle merged upload file button
function handleFileUpload() {
    // If no files are selected, trigger file selection first
    if (selectedFiles.length === 0) {
        document.getElementById('fileInput').click();
        return;
    }

    // If files are already selected, upload directly
    uploadFiles();
}

// Handle file selection
function handleFileSelection(event) {
    const files = Array.from(event.target.files);
    const oversizedFiles = [];

    selectedFiles = files.filter(file => {
        // Check file size (100MB limit)
        if (file.size > 100 * 1024 * 1024) {
            oversizedFiles.push(file.name);
            return false;
        }
        return true;
    });

    // Display warning for oversized files
    if (oversizedFiles.length > 0) {
        const warningMsg = `Files ${oversizedFiles.join(', ')} exceed the 100MB limit and have been skipped`;
        addLog('File upload', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 4000);
    }

    updateFileSelectionUI();
}

// Handle path selection button click - now show dropdown
// Open path selection modal
function openPathModal() {
    const modal = document.getElementById('pathModal');

    if (!modal) {
        console.error('Modal element not found!');
        return;
    }

    modal.style.display = 'flex';

    // Redisplay target path element
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'block';
    }

    // Reset path navigation history
    pathHistory = [];

    // Save original state when opening modal
    modalOriginalPath = selectedPath;
    modalOriginalPathName = selectedPathName;
    modalOriginalCurrentPath = currentModalPath;

    // Set current modal path to selected path
    currentModalPath = selectedPath || '';

    // Update path display immediately to ensure correct path is shown
    updateModalPathDisplay(selectedPath);

    // Reset event listeners for path input
    // Use setTimeout to ensure DOM is fully ready
    setTimeout(() => {
        setupPathInputEventListeners();
    }, 100);

    // Check if it's a system path (including all drives)
    // Note: Only explicit system paths are considered system paths, empty string defaults to Downloads
    const isSystemPath = selectedPath && selectedPath !== '' && (
        selectedPath.startsWith('/') ||
        /^[A-Z]:\\/.test(selectedPath) // Use regex to match any drive letter
    );

    if (isSystemPath) {
        // If it's a system path, call system directory loading function
        loadSystemDirectories(selectedPath);
    } else {
        // If it's Downloads path or empty path, call Downloads directory loading function
        loadModalPathList(selectedPath || '');
    }
}

// Close path selection modal
function closePathModal() {
    const modal = document.getElementById('pathModal');
    modal.style.display = 'none';

    // Restore original state when modal was opened
    // Note: Restore even if original state was null
    selectedPath = modalOriginalPath;
    selectedPathName = modalOriginalPathName;
    currentModalPath = modalOriginalCurrentPath;

    // Restore current path display in modal
    if (modalOriginalCurrentPath !== null) {
        updateModalPathDisplay(modalOriginalCurrentPath);
    }

    // Update path display on file management card
    updatePathSelectionUI();

    // Refresh file list to original path
    loadFileList();

    // Clear saved state
    modalOriginalPath = null;
    modalOriginalPathName = null;
    modalOriginalCurrentPath = null;
}

// Load system directory list
async function loadSystemDirectories(path = '', restoreSelection = true) {
    const pathList = document.getElementById('modalPathList');
    const upButton = document.getElementById('upButton');

    // Save currently selected path info to restore selection after loading
    const currentSelectedPath = restoreSelection ? selectedPath : null;

    // Show loading state
    pathList.innerHTML = '<div class="loading-placeholder">Loading system directory list...</div>';

    // Construct request URL
    const url = path ? `${getServerBaseUrl()}/system-directories?path=${encodeURIComponent(path)}` : `${getServerBaseUrl()}/system-directories`;

    // Create AbortController for timeout control
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15-second timeout

    try {
        const response = await fetch(url, {
            signal: controller.signal
        });

        // Clear timeout timer
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update current path display - prefer server-returned path, use incoming path if empty
        currentModalPath = data.current_path || path;

        // If server-returned path is empty but we have a selected path, use the selected path
        // But when navigating to root directory (empty path), always show system root
        const displayPath = data.current_path ? data.current_path :
            (path === '' ? 'My Computer' :
                (selectedPath ? selectedPath : 'My Computer'));

        // Update path display - use current modal path
        updateModalPathDisplay(displayPath);

        // Update parent directory button

        // Always show parent directory button
        upButton.style.display = 'inline-block';

        if (data.can_go_up) {
            upButton.title = 'Return to parent directory';
            upButton.innerText = '⬆️ Parent Directory';
            upButton.onclick = function () {
                // Use server-returned parent path, use current path's parent if empty
                const parentPath = data.parent_path || '';

                // Update current path display immediately
                updateModalPathDisplay(parentPath);

                // Update current modal path
                currentModalPath = parentPath;

                // Clear selected path to avoid default folder selection
                selectedPath = null;
                selectedPathName = null;

                // Update create folder location display
                updateCreateFolderLocation();

                loadSystemDirectories(parentPath, false);
            };
        } else {
            // Show disabled parent directory button when in root directory
            upButton.title = 'Already in root directory';
            upButton.innerText = '⬆️ Parent Directory';
            upButton.onclick = function () {
                showNotification('Already in root directory, cannot navigate further up' + data.can_go_up + "-" + data.detail?.can_go_up, 'warning', 3000);
                addLog('Path selection', 'Already in root directory, cannot navigate further up', 'warning');
            };
        }

        // Populate path list
        populateSystemPathList(data.items, currentSelectedPath);

        // Hide loading
        hideModalLoading();

    } catch (error) {
        // Clear timeout timer
        clearTimeout(timeoutId);

        console.error('Failed to load system directory list:', error);

        let userFriendlyMessage = '';

        // Provide user-friendly message based on error type
        if (error.name === 'AbortError') {
            userFriendlyMessage = 'Request timed out, please check network connection or try again later';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            userFriendlyMessage = 'Cannot connect to server, please ensure server is running';
        } else if (error.message.includes('status: 403')) {
            userFriendlyMessage = 'No permission to access this directory';

            // For 403 errors, update current path to attempted path for proper navigation
            currentModalPath = path;

            // Update path display
            updateModalPathDisplay(currentModalPath);
        } else if (error.message.includes('status: 404')) {
            userFriendlyMessage = 'Directory does not exist or has been deleted';

            // For 404 errors, update current path to attempted path for proper navigation
            currentModalPath = path;

            // Update path display
            updateModalPathDisplay(currentModalPath);
        } else if (error.message.includes('status: 408')) {
            userFriendlyMessage = 'Request timed out, please try again later';
        } else if (error.message.includes('status: 500')) {
            userFriendlyMessage = 'Server internal error, please try again later';
        } else {
            userFriendlyMessage = 'Failed to load directory list, please try again';
        }

        pathList.innerHTML = `
            <div class="error-placeholder">
                ${userFriendlyMessage}
            </div>
        `;

        // Configure parent directory button - ensure button is usable even in error cases
        const upButton = document.getElementById('upButton');
        upButton.style.display = 'inline-block';
        upButton.title = 'Return to parent directory';
        upButton.innerText = '⬆️ Parent Directory';
        upButton.onclick = navigateUp;

        showNotification(userFriendlyMessage, 'error', 3000);
        addLog('Path selection', userFriendlyMessage, 'error');

        // Hide loading
        hideModalLoading();
    }
}

// Populate system path list
function populateSystemPathList(items, currentSelectedPath) {
    const pathList = document.getElementById('modalPathList');

    if (!items || items.length === 0) {
        pathList.innerHTML = '<div class="empty-placeholder">No folders in current directory</div>';
        return;
    }

    let html = '';

    items.forEach(item => {
        // Select different icons based on type
        let icon = '📁'; // Default folder icon
        if (item.type === 'drive') {
            icon = '💾'; // Drive icon
        }

        const itemPath = item.path;

        // Escape special characters in path to prevent JavaScript syntax errors
        const escapedPath = itemPath.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
        const escapedName = item.name.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

        // Handle folder count display: -1 indicates timeout or error, display as "-"
        const folderCountDisplay = item.file_count === -1 ? '-' : (item.file_count || 0);

        html += `
            <div class="path-item" 
                 onclick="event.stopPropagation(); selectSystemPathItem(this, '${escapedPath}', '${escapedName}')" 
                 title="Click to select: ${escapedName}">
                <div class="path-name">
                    ${item.name}
                </div>
                <div class="file-count">${folderCountDisplay}</div>
                <div class="path-item-actions">
                    <button class="btn btn-primary" 
                            style="padding: 2px 6px; font-size: 10px; height: 20px; line-height: 1.2; border-radius: 3px; margin-right: 4px;"
                            onclick="event.stopPropagation(); navigateToSystemPath('${escapedPath}')" 
                            title="Enter folder: ${escapedName}">
                        Enter
                    </button>
                </div>
            </div>
        `;
    });

    pathList.innerHTML = html;

    // Restore selection state to match selected effect in image
    if (currentSelectedPath && currentSelectedPath.trim() !== '') {
        const pathItems = pathList.querySelectorAll('.path-item');
        pathItems.forEach(item => {
            try {
                const itemPath = item.getAttribute('onclick').match(/'([^']+)'/)[1];
                // Decode escaped path for comparison
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

// Select system path item
function selectSystemPathItem(element, path, name) {
    // Check if current item is already selected
    const isCurrentlySelected = element.classList.contains('selected');

    // Remove selection state from all other items
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });

    if (!isCurrentlySelected) {
        // If current item is not selected, select it
        element.classList.add('selected');

        // Store selected path information
        selectedPath = path || '';
        selectedPathName = name || '';

        // Update current path display in modal
        updateModalPathDisplay(path || '');

        // Show selection success notification
        const selectMsg = `Selected folder: ${name || path}`;
        addLog('Path selection', selectMsg, 'info');
        showNotification(selectMsg, 'success', 2000);
    } else {
        // If current item is already selected, deselect it
        selectedPath = null;
        selectedPathName = null;

        // Update current path display in modal
        updateModalPathDisplay('/');

        // Update create folder location display
        updateCreateFolderLocation();

        // Show deselection notification
        const cancelMsg = 'Folder selection canceled';
        addLog('Path selection', cancelMsg, 'info');
        showNotification(cancelMsg, 'info', 2000);

        // Automatically refresh file list
        loadFileList();
    }

    // Update path selection UI
    updatePathSelectionUI();
}

// Navigate to system path
function navigateToSystemPath(path) {
    // Update current path display immediately
    updateModalPathDisplay(path);

    // Update current modal path
    currentModalPath = path;

    // Update create folder location display
    updateCreateFolderLocation();

    // Show loading state
    showModalLoading();

    // Then load directory contents
    loadSystemDirectories(path);

    selectedPath = path;
    selectedPathName = path;
}

// Delete system path
async function deleteSystemPath(path) {
    const decodedPath = decodeURIComponent(path);

    // Check if it's a critical system path
    const criticalPaths = ['C:\\', 'D:\\', 'E:\\', 'F:\\', '/', '/home', '/root', 'My Computer'];
    if (criticalPaths.some(criticalPath => decodedPath === criticalPath || decodedPath.startsWith(criticalPath + '/'))) {
        showNotification('Cannot delete critical system directories', 'error', 3000);
        addLog('File management', `Attempted to delete critical directory was blocked: ${decodedPath}`, 'warning');
        return;
    }

    // Confirm deletion
    if (!confirm(`Are you sure you want to delete the folder "${decodedPath}"?\n\nThis action cannot be undone!`)) {
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
            showNotification(`Folder "${decodedPath}" deleted successfully`, 'success', 3000);
            addLog('File management', `Successfully deleted folder: ${decodedPath}`, 'info');

            // Clear selection if deleted path is currently selected
            if (selectedPath === decodedPath) {
                selectedPath = null;
                selectedPathName = null;
                updateCreateFolderLocation();
            }

            // Refresh path list
            refreshPathList();
        } else {
            const errorData = await response.json();
            showNotification(`Deletion failed: ${errorData.detail || 'Unknown error'}`, 'error', 3000);
            addLog('File management', `Failed to delete folder: ${decodedPath} - ${errorData.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error occurred while deleting folder:', error);
        showNotification('Network error occurred while deleting folder', 'error', 3000);
        addLog('File management', `Network error deleting folder: ${decodedPath} - ${error.message}`, 'error');
    }
}

// Load Downloads directory list
async function loadModalPathList(path = '', restoreSelection = true) {
    const pathList = document.getElementById('modalPathList');
    const currentPathElement = document.getElementById('modalCurrentPath');
    const upButton = document.getElementById('upButton');

    // Save currently selected path info to restore selection after loading
    const currentSelectedPath = restoreSelection ? selectedPath : null;
    const currentSelectedPathName = restoreSelection ? selectedPathName : null;

    // Show loading state
    pathList.innerHTML = '<div class="loading-placeholder">Loading directory list...</div>';

    // Construct request URL
    const url = path ? `${getServerBaseUrl()}/directories?path=${path}` : `${getServerBaseUrl()}/directories`;

    // Create AbortController for timeout control
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15-second timeout

    try {
        const response = await fetch(url, {
            signal: controller.signal
        });

        // Clear timeout timer
        clearTimeout(timeoutId);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update current path display - always use server-returned current path for consistency
        currentModalPath = data.current_path || '';

        // Show currently browsed path
        let displayPath;
        if (data.current_path && data.current_path !== '') {
            // Show server-returned current path
            displayPath = `📂 Downloads\\${data.current_path}`;
        } else {
            // Default to show Downloads root directory
            displayPath = '📂 Downloads';
        }

        // Update path display
        updateModalPathDisplay(data.current_path || '');

        // Update parent directory button - improved display logic

        // Always show parent directory button
        upButton.style.display = 'inline-block';

        // Set parent directory button functionality based on current path state
        if (data.current_path && data.current_path !== '') {
            upButton.title = 'Return to parent directory';
            upButton.innerText = '⬆️ Parent Directory';
            upButton.onclick = navigateUp;
        } else {
            upButton.title = 'Already in root directory';
            upButton.innerText = '⬆️ Parent Directory';
            upButton.onclick = function () {
                showNotification('Already in root directory, cannot navigate further up', 'warning', 3000);
                addLog('Path selection', 'Already in root directory, cannot navigate further up', 'warning');
            };
        }

        // Populate path list
        populateModalPathList(data.items, currentSelectedPath);

        // Hide loading
        hideModalLoading();

    } catch (error) {
        // Clear timeout timer
        clearTimeout(timeoutId);

        console.error('Failed to load path list:', error);

        let userFriendlyMessage = '';

        // Provide user-friendly message based on error type
        if (error.name === 'AbortError') {
            userFriendlyMessage = 'Request timed out, please check network connection or try again later';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            userFriendlyMessage = 'Cannot connect to server, please ensure server is running';
        } else if (error.message.includes('status: 403')) {
            userFriendlyMessage = 'No permission to access this directory';

            // For 403 errors, update current path to attempted path for proper navigation
            currentModalPath = path;

            // Update path display
            updateModalPathDisplay(currentModalPath);
        } else if (error.message.includes('status: 404')) {
            userFriendlyMessage = 'Directory does not exist or has been deleted';

            // For 404 errors, update current path to attempted path for proper navigation
            currentModalPath = path;

            // Update path display
            updateModalPathDisplay(currentModalPath);
        } else if (error.message.includes('status: 408')) {
            userFriendlyMessage = 'Request timed out, please try again later';
        } else if (error.message.includes('status: 500')) {
            userFriendlyMessage = 'Server internal error, please try again later';
        } else {
            userFriendlyMessage = 'Failed to load directory list, please try again';
        }

        pathList.innerHTML = `
            <div class="error-placeholder">
                ${userFriendlyMessage}
            </div>
        `;

        // Configure parent directory button - ensure button is usable even in error cases
        const upButton = document.getElementById('upButton');
        upButton.style.display = 'inline-block';
        upButton.title = 'Return to parent directory';
        upButton.innerText = '⬆️ Parent Directory';
        upButton.onclick = navigateUp;

        showNotification(userFriendlyMessage, 'error', 3000);
        addLog('Path selection', userFriendlyMessage, 'error');

        // Hide loading
        hideModalLoading();
    }
}

// Populate modal path list
function populateModalPathList(items, currentSelectedPath) {
    const pathList = document.getElementById('modalPathList');

    if (!items || items.length === 0) {
        pathList.innerHTML = '<div class="empty-placeholder">No folders in current directory</div>';
        return;
    }

    let html = '';

    items.forEach(item => {
        // Calculate correct path
        let itemPath;
        if (item.path && item.path !== '') {
            // Use server-returned path if available
            itemPath = item.path;
        } else if (currentModalPath && currentModalPath !== '') {
            // If in a directory, path is current directory + folder name
            itemPath = `${currentModalPath}\\${item.name}`;
        } else {
            // If in root directory, path is just folder name
            itemPath = item.name;
        }
        // Ensure itemPath is not null or undefined
        if (!itemPath) {
            itemPath = item.name || '';
        }

        // Escape special characters in path to prevent JavaScript syntax errors
        const escapedPath = itemPath.replace(/\//g, '\\\\').replace(/'/g, "\\'");
        const escapedName = itemPath.replace(/\//g, '\\\\').replace(/'/g, "\\'");

        // Handle folder count display: -1 indicates timeout or error, display as "-"
        const folderCountDisplay = item.file_count === -1 ? '-' : (item.file_count || 0);

        html += `
            <div class="path-item" 
                 onclick="event.stopPropagation(); selectModalPathItem(this, '${escapedPath}', '${escapedName}')" 
                 title="Click to select: ${escapedName}">
                <div class="path-name">
                    ${item.name}
                </div>
                <div class="file-count">${folderCountDisplay}</div>
                <div class="path-item-actions">
                    <button class="btn btn-primary" 
                            style="padding: 2px 6px; font-size: 10px; height: 20px; line-height: 1.2; border-radius: 3px; margin-right: 4px;"
                            onclick="event.stopPropagation(); navigateToPath('${escapedPath}')" 
                            title="Enter folder: ${escapedName}">
                        Enter
                    </button>
                    <button class="btn btn-danger" 
                            style="padding: 2px 6px; font-size: 10px; height: 20px; line-height: 1.2; border-radius: 3px;"
                            onclick="event.stopPropagation(); deleteFolder('${encodeURIComponent(itemPath)}')" 
                            title="Delete folder: ${escapedName}">
                        Delete
                    </button>
                </div>
            </div>
        `;
    });

    pathList.innerHTML = html;

    // Restore selection state to match selected effect in image
    if (currentSelectedPath && currentSelectedPath.trim() !== '') {
        const pathItems = pathList.querySelectorAll('.path-item');
        pathItems.forEach(item => {
            try {
                const itemPath = item.getAttribute('onclick').match(/'([^']+)'/)[1];
                // Decode escaped path for comparison
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

// Select modal path item
function selectModalPathItem(element, path, name) {
    // Check if current item is already selected
    const isCurrentlySelected = element.classList.contains('selected');

    // Remove selection state from all other items
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });

    if (!isCurrentlySelected) {
        // If current item is not selected, select it
        element.classList.add('selected');

        // Store selected path information
        selectedPath = path || '';
        selectedPathName = name || '';
        lastSelectedPath = path || ''; // Backup selected path

        // Update current path display in modal
        updateModalPathDisplay(path);

        // Update create folder location display
        updateCreateFolderLocation();

        // Show selection success notification
        const selectMsg = `Selected folder: ${name || path}`;
        addLog('Path selection', selectMsg, 'info');
        showNotification(selectMsg, 'success', 2000);
    } else {
        // If current item is already selected, deselect it
        selectedPath = null;
        selectedPathName = null;

        // Update current path display in modal
        updateModalPathDisplay(currentModalPath);

        // Update create folder location display
        updateCreateFolderLocation();

        // Show deselection notification
        const cancelMsg = 'Folder selection canceled';
        addLog('Path selection', cancelMsg, 'info');
        showNotification(cancelMsg, 'info', 2000);

        // Automatically refresh file list
        loadFileList();
    }

    // Update path selection UI
    updatePathSelectionUI();
}

// Navigate to specified path
function navigateToPath(path) {
    // Save current path to history (reserved for possible back functionality)
    if (currentModalPath !== '') {
        pathHistory.push(currentModalPath);
    }

    // Update current path display immediately
    updateModalPathDisplay(path);

    // Update current modal path
    currentModalPath = path;

    // Update create folder location display
    updateCreateFolderLocation();

    // Show loading state
    showModalLoading();

    // Then load directory contents
    loadModalPathList(path);
}

// Navigate to parent directory
function navigateUp() {
    // Cannot go up if in root directory
    if (!currentModalPath || currentModalPath === '') {
        showNotification('Already in root directory, cannot navigate further up', 'warning', 3000);
        addLog('Path selection', 'Already in root directory, cannot navigate further up', 'warning');
        return;
    }

    // Calculate parent directory path
    const pathParts = currentModalPath.split('\\');
    pathParts.pop(); // Remove last part
    const parentPath = pathParts.join('\\');

    // Update current path display immediately
    updateModalPathDisplay(parentPath);

    // Update current modal path
    currentModalPath = parentPath;

    // Update create folder location display
    updateCreateFolderLocation();

    // Show loading state
    showModalLoading();

    // Then load directory contents
    loadModalPathList(parentPath);
}

// Set default path (Downloads)
function setDefaultPath() {
    // Update current path display immediately
    updateModalPathDisplay('');

    // Set current modal path to empty string (indicates Downloads root directory)
    currentModalPath = '';
    // Set selected path to empty string, indicating default Downloads directory
    selectedPath = '';
    selectedPathName = 'Downloads';

    // Update path display under file management card
    updatePathSelectionUI();

    // Update create folder location display
    updateCreateFolderLocation();

    // Show user feedback
    addLog('Path selection', 'Switched to default Downloads directory', 'info');
    showNotification('Switched to default Downloads directory', 'success', 2000);

    showModalLoading();
    loadModalPathList('');
}

// Navigate to root directory (My Computer)
async function navigateToRoot() {
    // Update current path display immediately
    updateModalPathDisplay('/');

    // Clear current modal path to ensure system root is displayed
    currentModalPath = '';
    // Set selected path to "My Computer"
    selectedPath = 'My Computer';
    selectedPathName = 'My Computer';

    // Update path display under file management card
    updatePathSelectionUI();

    // Update create folder location display
    updateCreateFolderLocation();

    // Show user feedback
    addLog('Path selection', 'Selected "My Computer" as target path', 'info');
    showNotification('Selected "My Computer" as target path', 'success', 2000);

    showModalLoading();

    // Wait for system directory loading to complete
    await loadSystemDirectories('');

    // Set currentModalPath after async operation completes
    currentModalPath = "My Computer";
}

// Handle async call to navigate to root directory
async function handleNavigateToRoot() {
    try {
        await navigateToRoot();
    } catch (error) {
        console.error('Failed to navigate to root directory:', error);
        showNotification('Failed to navigate to root directory, please try again', 'error', 3000);
        addLog('Path selection', 'Failed to navigate to root directory: ' + error.message, 'error');
    }
}