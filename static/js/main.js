// Main entry file - Initialization logic and event listeners

// Initialization
document.addEventListener('DOMContentLoaded', function () {
    addLog('System', 'Page loaded completely', 'success');

    // Set up fullscreen state listener
    setupFullscreenListener();

    // Reset collapsed monitor states
    resetCollapsedMonitors();

    // Initialize trend charts
    drawMemoryTrendChart();
    drawCpuTrendChart(); // Initialize CPU trend chart
    drawNetworkLatencyTrendChart(); // Initialize network latency trend chart
    updateTrendChartTooltip();

    // Initialize remote control functionality
    if (typeof initRemoteControl === 'function') {
        initRemoteControl();
    }

    // Detect environment and display information
    const environment = detectEnvironment();
    const serverUrl = getServerBaseUrl();
    addLog('System', `Server address: ${serverUrl}`, 'info');

    // Check server status
    checkServerStatus().then(serverAvailable => {
        if (serverAvailable) {
            connectWebSocket();
            refreshAllMonitors(); // Load multi-monitor mode by default

            // Start auto-refresh (default behavior)
            startAutoRefresh();

            // Update button status
            const autoRefreshBtn = document.getElementById('autoRefreshBtn');
            if (autoRefreshBtn) {
                autoRefreshBtn.textContent = '⏸️ Stop Refresh';
                autoRefreshBtn.className = 'btn btn-danger';
            }
        } else {
            addLog('System', 'Please start the server first: python server.py', 'warning');
        }
    });

    // File selection event listener
    const fileInput = document.getElementById('fileInput');
    const pathInput = document.getElementById('pathInput');

    if (fileInput) {
        fileInput.addEventListener('change', handleFileSelection);
    }

    if (pathInput) {
        pathInput.addEventListener('change', handlePathSelectionEvent);
    }

    // Initialize upload button status
    updateFileSelectionUI();

    // Initialize path selection button status
    updatePathSelectionUI();

    // Directly add click event listener to path button
    const pathBtn = document.getElementById('pathBtn');
    if (pathBtn) {
        pathBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();

            // Always open modal regardless of whether a path is already selected
            openPathModal();
        });
    } else {
        console.error('pathBtn element not found!');
    }

    // Automatically load file list without clicking refresh button
    loadFileList();

    // Add event listener to close modal when clicking outside
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

    // Add event listener to close modal with ESC key
    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            const modal = document.getElementById('pathModal');
            if (modal && modal.style.display === 'flex') {
                closePathModal();
            }
        }
    });
});

// Handle path selection event (reserved for file selection cases)
function handlePathSelectionEvent(event) {
    const file = event.target.files[0];

    if (!file) {
        return;
    }

    // Get file name as path hint
    const fileName = file.name;

    // Use prompt to let user confirm or modify path
    const customPath = prompt(`Detected file: ${fileName}\nPlease enter target path (e.g.: Documents/MyFiles or leave empty to use default Downloads directory):`);

    if (customPath !== null) { // User clicked OK
        if (customPath.trim() === '') {
            // User entered empty path, clear selection
            clearSelectedPath();
        } else {
            // Set selected path
            selectedPath = customPath.trim();

            // Update UI display
            updatePathSelectionUI();

            // Show success message
            const successMsg = `Target path set: ${selectedPath}`;
            addLog('Path selection', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);

            // Automatically refresh file list
            loadFileList();
        }
    }

    // Clear file selection to avoid affecting subsequent operations
    event.target.value = '';
}

// Update path selection UI
function updatePathSelectionUI() {
    const pathInfo = document.getElementById('pathInfo');
    const currentPath = document.getElementById('currentPath');
    const pathBtn = document.getElementById('pathBtn');

    if (selectedPath !== null && selectedPath !== undefined) {
        pathInfo.style.display = 'block';

        // Display path information
        let displayPath;
        // Check if it's a system path (including all drives)
        const isSystemPath = selectedPath && selectedPath !== '' && (
            selectedPath.startsWith('/') ||
            /^[A-Z]:\\/.test(selectedPath) // Use regex to match any drive letter
        );

        if (selectedPath === 'My Computer') {
            // My Computer path
            displayPath = 'My Computer';
            pathBtn.innerHTML = 'Selected Path';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        } else if (isSystemPath) {
            // System path
            displayPath = selectedPath;
            pathBtn.innerHTML = 'Selected Path';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        } else if (selectedPath === '') {
            // Default Downloads path (empty string)
            displayPath = 'Downloads';
            pathBtn.innerHTML = 'Selected Path';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        } else {
            // Downloads subdirectory path
            displayPath = `Downloads/${selectedPath}`;
            pathBtn.innerHTML = 'Selected Path';
            pathBtn.style.background = 'linear-gradient(135deg, #28a745 0%, #20c997 100%)';
        }

        currentPath.textContent = displayPath;
    } else {
        pathInfo.style.display = 'none';
        pathBtn.innerHTML = 'Set Path';
        pathBtn.style.background = '';
    }
}

// Clear selected path
function clearSelectedPath() {
    selectedPath = null;
    selectedPathName = null;

    // Clear selection state for all path items
    const allItems = document.querySelectorAll('.path-item');
    allItems.forEach(item => {
        item.classList.remove('selected');
    });

    updatePathSelectionUI();

    // Update create folder location display
    updateCreateFolderLocation();

    // Hide target path element
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'none';
    }

    const successMsg = 'Path settings cleared, returned to default Downloads directory';
    addLog('Path selection', successMsg, 'info');
    showNotification(successMsg, 'info', 3000);

    // Automatically refresh file list
    loadFileList();
}

// Update create folder location display
function updateCreateFolderLocation() {
    const createFolderLocation = document.getElementById('createFolderLocation');
    if (!createFolderLocation) return;

    let locationText = '';
    if (selectedPath !== null && selectedPath !== undefined) {
        // Check if it's a system path (including all drives)
        const isSystemPath = selectedPath && selectedPath !== '' && (
            selectedPath.startsWith('/') ||
            /^[A-Z]:\\/.test(selectedPath) // Use regex to match any drive letter
        );

        if (selectedPath === 'My Computer') {
            // My Computer path
            locationText = 'My Computer';
        } else if (isSystemPath) {
            // System path
            locationText = selectedPath;
        } else if (selectedPath === '') {
            // Default Downloads path (empty string)
            locationText = 'Downloads';
        } else {
            // Downloads subdirectory path
            locationText = `Downloads/${selectedPath}`;
        }
    } else {
        // When no path is selected, default to showing Downloads
        locationText = 'Downloads';
    }

    createFolderLocation.textContent = locationText;
}

// Show create folder dialog
function showCreateFolderDialog() {
    const modal = document.getElementById('createFolderModal');
    modal.style.display = 'flex';

    // Update create folder location display
    updateCreateFolderLocation();

    // Focus on input box
    const folderNameInput = document.getElementById('folderNameInput');
    if (folderNameInput) {
        folderNameInput.focus();
    }
}

// Close create folder dialog
function closeCreateFolderDialog() {
    const modal = document.getElementById('createFolderModal');
    modal.style.display = 'none';

    // Clear input box
    const folderNameInput = document.getElementById('folderNameInput');
    if (folderNameInput) {
        folderNameInput.value = '';
    }
}

// Create folder
async function createFolder() {
    const folderNameInput = document.getElementById('folderNameInput');
    const folderName = folderNameInput.value.trim();

    if (!folderName) {
        showNotification('Please enter a folder name', 'warning', 3000);
        return;
    }

    // Check if folder name contains invalid characters
    const invalidChars = /[<>:"/\\|?*]/;
    if (invalidChars.test(folderName)) {
        showNotification('Folder name contains invalid characters', 'error', 3000);
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
            showNotification(`Folder "${folderName}" created successfully`, 'success', 3000);
            addLog('File management', `Successfully created folder: ${folderName}`, 'info');

            // Close dialog
            closeCreateFolderDialog();

            // Refresh path list
            refreshPathList();
        } else {
            const errorData = await response.json();
            showNotification(`Failed to create folder: ${errorData.detail || 'Unknown error'}`, 'error', 3000);
            addLog('File management', `Failed to create folder: ${folderName} - ${errorData.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error occurred while creating folder:', error);
        showNotification('Network error occurred while creating folder', 'error', 3000);
        addLog('File management', `Network error creating folder: ${folderName} - ${error.message}`, 'error');
    }
}

// Set up path input event listeners
function setupPathInputEventListeners() {
    const pathInput = document.getElementById('modalCurrentPathInput');
    if (!pathInput) return;

    // Remove existing event listeners
    pathInput.removeEventListener('click', pathInputClickHandler);
    pathInput.removeEventListener('dblclick', pathInputDblClickHandler);
    pathInput.removeEventListener('keydown', pathInputKeydownHandler);
    pathInput.removeEventListener('contextmenu', pathInputContextMenuHandler);

    // Add new event listeners
    pathInput.addEventListener('click', pathInputClickHandler);
    pathInput.addEventListener('dblclick', pathInputDblClickHandler);
    pathInput.addEventListener('keydown', pathInputKeydownHandler);
    pathInput.addEventListener('contextmenu', pathInputContextMenuHandler);
}

// Path input click handler
function pathInputClickHandler(event) {
    event.preventDefault();
    event.stopPropagation();
    // Click handling logic can be added here
}

// Path input double click handler
function pathInputDblClickHandler(event) {
    event.preventDefault();
    event.stopPropagation();
    // Double click handling logic can be added here
}

// Path input keyboard handler
function pathInputKeydownHandler(event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        event.stopPropagation();
        // Enter key handling logic can be added here
    }
}

// Path input context menu handler
function pathInputContextMenuHandler(event) {
    event.preventDefault();
    event.stopPropagation();
    // Right-click menu handling logic can be added here
}

// Refresh path list
function refreshPathList() {
    showModalLoading();

    // Check if it's a system path (including all drives)
    // Note: Only explicit system paths are considered system paths, empty string defaults to Downloads
    const isSystemPath = currentModalPath && currentModalPath !== '' && (
        currentModalPath.startsWith('/') ||
        /^[A-Z]:\\/.test(currentModalPath) ||
        currentModalPath === 'My Computer'
    );
    console.log('DEBUG: refreshPathList - currentModalPath:', currentModalPath);
    console.log('DEBUG: refreshPathList - isSystemPath:', isSystemPath);

    if (isSystemPath) {
        // If it's a system path, call system directory loading function
        if (currentModalPath === 'My Computer') {
            loadSystemDirectories('');
        } else {
            loadSystemDirectories(currentModalPath);
        }
    } else {
        // If it's Downloads path or empty path, call Downloads directory loading function
        loadModalPathList(currentModalPath);
    }
}

// Select current path and close modal
function selectCurrentPath() {
    // When no folder is selected in the popup, use the same value as currentModalPath
    let finalSelectedPath;
    if (selectedPath !== null && selectedPath !== undefined && selectedPath !== '') {
        // User has selected a path, use the selected path
        finalSelectedPath = selectedPath;
    } else {
        // User hasn't selected a path, use currently browsed path
        finalSelectedPath = currentModalPath || '';
    }
    // Set selected path
    selectedPath = finalSelectedPath;

    // Update UI
    updatePathSelectionUI();

    // Hide target path element
    const pathInfo = document.getElementById('pathInfo');
    if (pathInfo) {
        pathInfo.style.display = 'none';
    }

    // Close modal directly without calling closePathModal() to avoid restoring original state
    const modal = document.getElementById('pathModal');
    modal.style.display = 'none';

    // Show success message
    let pathDisplay;
    // Check if it's a system path (including all drives)
    const isSystemPath = selectedPath && selectedPath !== '' && (
        selectedPath.startsWith('/') ||
        /^[A-Z]:\\/.test(selectedPath) // Use regex to match any drive letter
    );

    if (isSystemPath) {
        // System path
        pathDisplay = selectedPath;
    } else {
        // Downloads path (including empty string representing Downloads root directory)
        pathDisplay = selectedPath === '' ? 'Downloads' : `Downloads/${selectedPath}`;
    }
    const successMsg = `Selected folder: ${pathDisplay}`;
    addLog('Path selection', successMsg, 'info');
    showNotification(successMsg, 'info', 3000);

    // Automatically refresh file list to selected path
    loadFileList();

    // Clear saved modal state
    modalOriginalPath = null;
    modalOriginalPathName = null;
    modalOriginalCurrentPath = null;
}