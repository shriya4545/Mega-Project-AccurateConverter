document.addEventListener('DOMContentLoaded', () => {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const preview = document.getElementById('preview');
    const openDrawerButton = document.getElementById('openDrawer');
    const closeDrawerButton = document.getElementById('closeDrawer');
    const historyDrawer = document.getElementById('historyDrawer');
    const historyList = document.getElementById('historyList');
    const downloadButton = document.getElementById('downloadButton');

    uploadButton.addEventListener('click', (event) => {
        event.preventDefault();
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        handleFile(file);
    });

    function handleFile(file) {
        if (file && file.name.endsWith('.dxf') && file.size < 64 * 1024 * 1024) {
            const formData = new FormData();
            formData.append('file', file);

            preview.innerHTML = '';
            const loadingMessage = document.createElement('p');
            loadingMessage.textContent = 'Uploading...';
            preview.appendChild(loadingMessage);

            fetch('/upload', {
                method: 'POST',
                body: formData
            })
            .then(response => {
                const contentType = response.headers.get('content-type');
                if (contentType && contentType.includes('application/json')) {
                    if (!response.ok) {
                        return response.json().then(err => {
                            throw new Error(err.error || 'Unknown error occurred');
                        });
                    }
                    return response.json();
                }
                throw new Error('Server returned invalid response format');
            })
            .then(data => {
                loadingMessage.remove();
                if (data.svg && data.filename) {
                    preview.innerHTML = data.svg;
                    preview.setAttribute('data-filename', data.filename);
                    // Reset file input to allow re-uploading the same file if needed
                    fileInput.value = '';
                    // Ensure upload button is visible and enabled
                    uploadButton.style.display = 'inline-block';
                    uploadButton.disabled = false;
                } else {
                    alert('Error: ' + data.error);
                    console.error('Error from server:', data.error);
                    // Reset file input and upload button on error
                    fileInput.value = '';
                    uploadButton.style.display = 'inline-block';
                    uploadButton.disabled = false;
                }
            })
            .catch(error => {
                loadingMessage.remove();
                console.error('Error uploading file:', error);
                alert(`Error: ${error.message}`);
                // Reset file input and upload button on error
                fileInput.value = '';
                uploadButton.style.display = 'inline-block';
                uploadButton.disabled = false;
            });
        } else {
            alert('Please upload a valid DXF file (max 64MB).');
        }
    }

    downloadButton.addEventListener('click', () => {
        const svgFilename = preview.getAttribute('data-filename');
        if (svgFilename) {
            window.location.href = `/download/${svgFilename}`;
        } else {
            alert('No file available to download. Please upload a DXF file first.');
        }
    });

    openDrawerButton.addEventListener('click', () => {
        fetch('/history')
            .then(response => response.json())
            .then(data => {
                historyList.innerHTML = '';
                data.forEach(file => {
                    let listItem = document.createElement('li');
                    let link = document.createElement('a');
                    link.href = `/file/${file.filename}`;
                    link.textContent = `${file.filename} - ${file.upload_time}`;
                    link.target = "_blank";
                    listItem.appendChild(link);
                    historyList.appendChild(listItem);
                });
                historyDrawer.classList.add('open');
            })
            .catch(error => console.error('Error fetching history:', error));
    });

    closeDrawerButton.addEventListener('click', () => {
        historyDrawer.classList.remove('open');
    });
});
