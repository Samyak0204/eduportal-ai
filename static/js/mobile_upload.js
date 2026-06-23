document.addEventListener('DOMContentLoaded', () => {
    const captureContainer = document.getElementById('capture-container');
    const cameraInput = document.getElementById('mobile-camera-input');
    const previewImg = document.getElementById('capture-preview');
    const promptDiv = document.getElementById('capture-prompt');
    
    const btnRetake = document.getElementById('btn-retake');
    const btnSubmit = document.getElementById('btn-submit-upload');
    const uploadForm = document.getElementById('mobile-upload-form');
    const successAlert = document.getElementById('upload-success-alert');

    let base64Image = null;

    // Trigger file dialog
    captureContainer.addEventListener('click', () => {
        cameraInput.click();
    });

    if (btnRetake) {
        btnRetake.addEventListener('click', (e) => {
            e.stopPropagation();
            cameraInput.click();
        });
    }

    cameraInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;

        // Size check: limit to 10MB on mobile
        if (file.size > 10 * 1024 * 1024) {
            alert("File size exceeds 10MB limit. Please capture a lower resolution photo.");
            return;
        }

        const reader = new FileReader();
        reader.onload = (event) => {
            base64Image = event.target.result;
            
            previewImg.src = base64Image;
            previewImg.style.display = 'block';
            promptDiv.style.display = 'none';
            
            btnSubmit.removeAttribute('disabled');
            if (btnRetake) btnRetake.style.display = 'inline-flex';
        };
        reader.readAsDataURL(file);
    });

    uploadForm.addEventListener('submit', (e) => {
        e.preventDefault();
        
        if (!base64Image) {
            alert("Please capture a photo before submitting.");
            return;
        }

        const token = document.getElementById('upload-token').value;

        btnSubmit.setAttribute('disabled', 'true');
        btnSubmit.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting photo...';

        fetch('/mobile_upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                token: token,
                image_data: base64Image
            })
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'ok') {
                // Success state
                uploadForm.style.display = 'none';
                captureContainer.style.display = 'none';
                successAlert.style.display = 'flex';
            } else {
                alert(`Error: ${data.message}`);
                btnSubmit.removeAttribute('disabled');
                btnSubmit.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Upload & Submit Photo';
            }
        })
        .catch(err => {
            console.error("Error submitting mobile photo upload", err);
            btnSubmit.removeAttribute('disabled');
            btnSubmit.innerHTML = '<i class="fa-solid fa-cloud-arrow-up"></i> Upload & Submit Photo';
            alert("Network error. Please make sure your phone is connected to the same network and try again.");
        });
    });
});
