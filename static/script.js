// document.addEventListener('DOMContentLoaded', () => {
//     const uploadArea = document.getElementById('uploadArea');
//     const fileInput = document.getElementById('fileInput');
//     const uploadButton = document.getElementById('uploadButton');
//     const preview = document.getElementById('preview');

//     uploadButton.addEventListener('click', (event) => {
//         event.preventDefault(); // Prevent default action
//         fileInput.click(); // Trigger file input click
//     });

//     fileInput.addEventListener('change', (e) => {
//         const file = e.target.files[0];
//         handleFile(file);
//     });

//     function handleFile(file) {
//         if (file && file.name.endsWith('.dxf') && file.size < 10 * 1024 * 1024) { // Example size limit: 5MB
//             const formData = new FormData();
//             formData.append('file', file);

//             // Clear previous SVG preview
//             preview.innerHTML = '';

//             // Show loading message
//             const loadingMessage = document.createElement('p');
//             loadingMessage.textContent = 'Uploading...';
//             preview.appendChild(loadingMessage);

//             // Make AJAX request to upload the DXF file
//             fetch('/upload', {
//                 method: 'POST',
//                 body: formData
//             })
//             .then(response => {
//                 // Check content type first
//                 const contentType = response.headers.get('content-type');
//                 if (contentType && contentType.includes('application/json')) {
//                     if (!response.ok) {
//                         return response.json().then(err => {
//                             throw new Error(err.error || 'Unknown error occurred');
//                         });
//                     }
//                     return response.json();
//                 }
//                 throw new Error('Server returned invalid response format');
//             })
//             .then(data => {
//                 // Remove loading message
//                 loadingMessage.remove();

//                 if (data.svg) {
//                     preview.innerHTML = data.svg; // Display SVG in preview area
//                 } else {
//                     alert('Error: ' + data.error);
//                     console.error('Error from server:', data.error);
//                 }
//             })
//             .catch(error => {
//                 // Remove loading message
//                 loadingMessage.remove();

//                 console.error('Error uploading file:', error); // Log detailed error
//                 if (error instanceof TypeError && error.message === 'Failed to fetch') {
//                     alert('Network error: Could not reach the server.');
//                 } else {
//                     alert(`Error: ${error.message}`);
//                 }
//             });
//         } else {
//             alert('Please upload a valid DXF file (max 10MB).');
//         }
//     }
// });



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
        if (file && file.name.endsWith('.dxf') && file.size < 10 * 1024 * 1024) {
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
                } else {
                    alert('Error: ' + data.error);
                    console.error('Error from server:', data.error);
                }
            })
            .catch(error => {
                loadingMessage.remove();
                console.error('Error uploading file:', error);
                alert(`Error: ${error.message}`);
            });
        } else {
            alert('Please upload a valid DXF file (max 10MB).');
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
