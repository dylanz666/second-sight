// File Management Tool Module - File List, Upload, Download, and Other Functions

// Upload files
async function uploadFiles() {
    if (selectedFiles.length === 0) {
        const warningMsg = 'No files selected';
        addLog('Upload File', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 3000);
        return;
    }

    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    try {
        uploadBtn.disabled = true;
        uploadBtn.innerHTML = '⏳ Uploading...';
        uploadProgress.style.display = 'block';

        const formData = new FormData();
        selectedFiles.forEach(file => {
            formData.append('files', file);
        });

        // If a folder is selected, add it to the request
        if (selectedPath !== null && selectedPath !== undefined) {
            formData.append('folder_path', selectedPath);
        }

        const xhr = new XMLHttpRequest();

        // Listen for upload progress
        xhr.upload.addEventListener('progress', function (event) {
            if (event.lengthComputable) {
                const percentComplete = (event.loaded / event.total) * 100;
                progressFill.style.width = percentComplete + '%';
                progressText.textContent = Math.round(percentComplete) + '%';
            }
        });

        // Listen for upload completion
        xhr.addEventListener('load', function () {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    addLog('Upload File', response.message, 'success');
                    showNotification(response.message, 'success', 5000);

                    // Clear selection
                    selectedFiles = [];
                    document.getElementById('fileInput').value = '';
                    updateFileSelectionUI();

                    // Refresh file list
                    loadFileList();

                } catch (error) {
                    const errorMsg = 'Failed to parse response: ' + error.message;
                    addLog('Upload File', errorMsg, 'error');
                    showNotification(errorMsg, 'error', 5000);
                }
            } else {
                const errorMsg = 'Upload failed: HTTP ' + xhr.status;
                addLog('Upload File', errorMsg, 'error');
                showNotification(errorMsg, 'error', 5000);
            }

            // Reset UI
            uploadProgress.style.display = 'none';
            progressFill.style.width = '0%';
            progressText.textContent = '0%';
            updateFileSelectionUI();
        });

        // Listen for upload errors
        xhr.addEventListener('error', function () {
            const errorMsg = 'Network error, upload failed';
            addLog('Upload File', errorMsg, 'error');
            showNotification(errorMsg, 'error', 5000);
            uploadProgress.style.display = 'none';
            updateFileSelectionUI();
        });

        // Send request
        xhr.open('POST', getServerBaseUrl() + '/upload/multiple');
        xhr.send(formData);

    } catch (error) {
        const errorMsg = 'Upload failed: ' + error.message;
        addLog('Upload File', errorMsg, 'error');
        showNotification(errorMsg, 'error', 5000);
        uploadProgress.style.display = 'none';
        updateFileSelectionUI();
    }
}

async function dropToUploadFiles(droppedFiles) {
    if (droppedFiles.length === 0) {
        const warningMsg = 'No files selected';
        addLog('Upload File', warningMsg, 'warning');
        showNotification(warningMsg, 'warning', 3000);
        return;
    }
    if (selectedPath == "My Computer") {
        showNotification("Please set path in file manager area!", 'warning', 3000);
        return;
    }
    const targetFolder = selectedPath ? selectedPath : 'Downloads';
    if (!confirm(droppedFiles.length + ` files will be uploaded to the remote server.\n\nTarget folder: ${targetFolder}\n\nDo you want to continue?`)) {
        return;
    }

    // Upload files
    try {
        const formData = new FormData();
        for (let i = 0; i < droppedFiles.length; i++) {
            formData.append('files', droppedFiles[i]);
        }
        // If a folder is selected, add it to the request
        if (selectedPath !== null && selectedPath !== undefined) {
            formData.append('folder_path', selectedPath);
        }

        const xhr = new XMLHttpRequest();
        // Listen for upload completion
        xhr.addEventListener('load', async function () {
            if (xhr.status === 200) {
                try {
                    const response = JSON.parse(xhr.responseText);
                    addLog('Upload File', response.message, 'success');
                    showNotification(response.message, 'success', 5000);

                    // Refresh file list
                    loadFileList();

                    // Open folder in remote server
                    const openFolderResponse = await fetch(`${getServerBaseUrl()}/folder/open`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            folder_path: selectedPath
                        })
                    })
                    if (openFolderResponse.ok) {
                        addLog('Upload File', 'Open folder in remote server', 'success');
                        showNotification('Open folder in remote server successfully', 'success', 3000);
                    } else {
                        const errorData = await openFolderResponse.json();
                        addLog('Upload File', 'Failed to open folder in remote server: ' + (errorData.detail || 'Unknown error'), 'error');
                        showNotification('Failed to open folder in remote server', 'error', 3000);
                    }
                } catch (error) {
                    const errorMsg = 'Failed to parse response: ' + error.message;
                    addLog('Upload File', errorMsg, 'error');
                    showNotification(errorMsg, 'error', 5000);
                }
            } else {
                const errorMsg = 'Upload failed: HTTP ' + xhr.status;
                addLog('Upload File', errorMsg, 'error');
                showNotification(errorMsg, 'error', 5000);
            }
        });
        // Listen for upload errors
        xhr.addEventListener('error', function () {
            const errorMsg = 'Network error, upload failed';
            addLog('Upload File', errorMsg, 'error');
            showNotification(errorMsg, 'error', 5000);
        });
        // Send request
        xhr.open('POST', getServerBaseUrl() + '/upload/multiple');
        xhr.send(formData);        
    } catch (error) {
        const errorMsg = 'Upload failed: ' + error.message;
        addLog('Upload File', errorMsg, 'error');
        showNotification(errorMsg, 'error', 5000);
    }
}


// Load file list
async function loadFileList() {
    const fileList = document.getElementById('fileList');

    fileList.innerHTML = '<div class="file-list-placeholder">Loading...</div>';

    // Build request URL, including folder path parameter
    let url = getServerBaseUrl() + '/files';
    if (selectedPath !== null && selectedPath !== undefined) {
        url += `?folder=${encodeURIComponent(selectedPath)}`;
    }

    // Create AbortController for timeout control
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000); // 15 seconds timeout

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

        if (data.files && data.files.length > 0) {
            fileList.innerHTML = '';

            // Display current folder information
            const folderHeader = document.createElement('div');
            folderHeader.style.cssText = 'padding: 8px; background: #e9ecef; border-radius: 4px; margin-bottom: 8px; font-size: 12px; color: #495057;';

            // Build complete folder path display
            let folderDisplay;
            // Check if it is a system path (including all drives)
            const isSystemFolder = data.current_folder && (
                data.current_folder.startsWith('/') ||
                /^[A-Z]:\\/.test(data.current_folder) // Use regex to match any drive letter
            );

            if (isSystemFolder) {
                // System path
                folderDisplay = data.current_folder;
            } else if (data.current_folder && data.current_folder !== 'Downloads') {
                // Downloads subdirectory
                folderDisplay = `Downloads\\${data.current_folder}`;
            } else {
                // Downloads root directory
                folderDisplay = 'Downloads';
            }

            folderHeader.innerHTML = `<span>📁 Current Folder: ${folderDisplay} (${data.files.length} files)</span>`;
            fileList.appendChild(folderHeader);

            data.files.forEach(file => {
                const fileItem = createFileItem(file);
                fileList.appendChild(fileItem);
            });

            addLog('File Management', `Loaded ${data.files.length} files`, 'info');
        } else {
            // Build complete folder path display
            let folderDisplay;
            // Check if it is a system path (including all drives)
            const isSystemFolder = data.current_folder && (
                data.current_folder.startsWith('/') ||
                /^[A-Z]:\\/.test(data.current_folder) || data.current_folder === 'My Computer'
            );

            if (isSystemFolder) {
                // System path
                folderDisplay = data.current_folder;
                fileList.innerHTML = `<div class="file-list-placeholder">🏠 No files in ${folderDisplay}</div>`;
                return;
            }
            if (data.current_folder && data.current_folder !== 'Downloads') {
                // Downloads subdirectory
                folderDisplay = `Downloads\\${data.current_folder}`;
            } else {
                // Downloads root directory
                folderDisplay = 'Downloads';
            }
            fileList.innerHTML = `<div class="file-list-placeholder">📁 No files in ${folderDisplay}</div>`;
        }

    } catch (error) {
        // Clear timeout timer
        clearTimeout(timeoutId);

        let userFriendlyMessage = '';

        // Provide user-friendly prompts based on error type
        if (error.name === 'AbortError') {
            userFriendlyMessage = 'Request timed out, please check your network connection or try again later';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            userFriendlyMessage = 'Unable to connect to the server, please ensure the server is running';
        } else if (error.message.includes('status: 403')) {
            userFriendlyMessage = 'No permission to access files in this directory, please choose another path';
        } else if (error.message.includes('status: 404')) {
            userFriendlyMessage = 'Directory does not exist or has been deleted';
        } else if (error.message.includes('status: 408')) {
            userFriendlyMessage = 'Request timed out, please try again later';
        } else if (error.message.includes('status: 500')) {
            userFriendlyMessage = 'Internal server error, please try again later';
        } else {
            userFriendlyMessage = 'Failed to load file list, please try again';
        }

        fileList.innerHTML = `<div class="error-placeholder">${userFriendlyMessage}</div>`;
        addLog('File Management', userFriendlyMessage, 'error');
        showNotification(userFriendlyMessage, 'error', 3000);
    }
}

// Create file item
function createFileItem(file) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';

    const uploadTime = new Date(file.upload_time).toLocaleString('zh-CN', { hour12: false });

    // Escape special characters in filename to prevent JavaScript syntax errors
    const escapedFilename = file.filename.replace(/\\/g, '\\\\').replace(/'/g, "\\'");

    fileItem.innerHTML = `
        <div class="file-info">
            <div class="file-name">${file.filename}</div>
            <div class="file-details">
                <span>Size: ${file.size_mb}MB</span>
                <span>Date: ${uploadTime}</span>
            </div>
        </div>
        <div class="file-actions">
            <button class="file-btn file-btn-download" onclick="downloadFile('${escapedFilename}')" title="Download">📥</button>
            <button class="file-btn file-btn-delete" onclick="deleteFile('${escapedFilename}')" title="Delete">🗑️</button>
        </div>
    `;

    return fileItem;
}

// Download file
async function downloadFile(filename) {
    try {
        // Build request URL, including folder path parameter
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

            const successMsg = `File ${filename} downloaded successfully`;
            addLog('File Management', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);
        } else {
            const errorMsg = `Failed to download file ${filename}: HTTP ${response.status}`;
            addLog('File Management', errorMsg, 'error');
            showNotification(errorMsg, 'error', 3000);
        }
    } catch (error) {
        const errorMsg = `Failed to download file ${filename}: ${error.message}`;
        addLog('File Management', errorMsg, 'error');
        showNotification(errorMsg, 'error', 3000);
    }
}

// Delete file
async function deleteFile(filename) {
    if (!confirm(`Are you sure you want to delete the file "${filename}"?\n\nThis action cannot be undone!`)) {
        return;
    }

    try {
        // Build request URL, including folder path parameter
        let url = getServerBaseUrl() + `/files/${filename}`;
        if (selectedPath !== null && selectedPath !== undefined) {
            url += `?folder=${encodeURIComponent(selectedPath)}`;
        }

        const response = await fetch(url, {
            method: 'DELETE'
        });

        if (response.ok) {
            const successMsg = `File ${filename} deleted successfully`;
            addLog('File Management', successMsg, 'success');
            showNotification(successMsg, 'success', 3000);

            // Refresh file list
            loadFileList();
        } else {
            const errorData = await response.json();
            const errorMsg = `Failed to delete file ${filename}: ${errorData.detail || 'Unknown error'}`;
            addLog('File Management', errorMsg, 'error');
            showNotification(errorMsg, 'error', 3000);
        }
    } catch (error) {
        const errorMsg = `Failed to delete file ${filename}: ${error.message}`;
        addLog('File Management', errorMsg, 'error');
        showNotification(errorMsg, 'error', 3000);
    }
}

// Delete folder
async function deleteFolder(folderPath) {
    const decodedPath = decodeURIComponent(folderPath);

    // Check if it is a critical system path
    const criticalPaths = ['C:\\', 'D:\\', 'E:\\', 'F:\\', '/', '/home', '/root', 'Downloads'];
    if (criticalPaths.some(criticalPath => decodedPath === criticalPath || decodedPath.startsWith(criticalPath + '/'))) {
        showNotification('Cannot delete critical system directories', 'error', 3000);
        addLog('File Management', `Attempt to delete critical directory blocked: ${decodedPath}`, 'warning');
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
            addLog('File Management', `Folder deletion successful: ${decodedPath}`, 'info');

            // If the deleted folder is the currently selected path, clear selection
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
            addLog('File Management', `Failed to delete folder: ${decodedPath} - ${errorData.detail}`, 'error');
        }
    } catch (error) {
        console.error('Error occurred while deleting folder:', error);
        showNotification('Network error occurred while deleting folder', 'error', 3000);
        addLog('File Management', `Network error while deleting folder: ${decodedPath} - ${error.message}`, 'error');
    }
}

// Update file selection UI
function updateFileSelectionUI() {
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadInfo = document.getElementById('uploadInfo');

    if (selectedFiles.length > 0) {
        uploadBtn.disabled = false;
        uploadInfo.style.display = 'block';

        // Create file list HTML
        let fileListHTML = `<div style="margin-bottom: 8px;"><span style="font-weight: bold;">Selected ${selectedFiles.length} files:</span></div>`;

        selectedFiles.forEach((file, index) => {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            fileListHTML += `
                <div class="selected-file-item">
                    <div class="file-name" title="${file.name}">${file.name}</div>
                    <div class="file-size">(${sizeMB}MB)</div>
                    <button 
                        class="delete-btn"
                        onclick="removeSelectedFile(${index})" 
                        title="Remove this file"
                    >
                        ✕
                    </button>
                </div>
            `;
        });

        uploadInfo.innerHTML = fileListHTML;

        // Update button text to indicate upload is possible
        uploadBtn.innerHTML = '⬆️ Upload';
    } else {
        uploadBtn.disabled = false; // Button is no longer disabled, but used for file selection
        uploadInfo.style.display = 'none';

        // Update button text to indicate file selection is possible
        uploadBtn.innerHTML = 'Upload File';
    }
}

// Remove selected file
function removeSelectedFile(fileIndex) {
    if (fileIndex >= 0 && fileIndex < selectedFiles.length) {
        const removedFile = selectedFiles[fileIndex];
        selectedFiles.splice(fileIndex, 1);

        // Show success message for removal
        const successMsg = `Removed from upload list: ${removedFile.name}`;
        addLog('File Management', successMsg, 'info');
        showNotification(successMsg, 'info', 2000);

        // Update UI
        updateFileSelectionUI();
    }
}