// Elements
const video       = document.getElementById('video');
const canvas      = document.getElementById('canvas');
const snapBtn     = document.getElementById('snap-btn');
const uploadForm  = document.getElementById('upload-form');
const analyzeBtn  = document.getElementById('analyze-btn');
const loader      = document.getElementById('loader');
const message     = document.getElementById('message');

// Camera setup
if (navigator.mediaDevices?.getUserMedia) {
  navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => video.srcObject = stream)
    .catch(() => message.textContent = 'Camera not available.');
}

// Show loader on form submit
uploadForm.addEventListener('submit', () => {
  analyzeBtn.disabled = true;
  loader.hidden      = false;
});

// Capture from camera
snapBtn.addEventListener('click', () => {
  canvas.width  = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  canvas.toBlob(blob => {
    analyzeBtn.disabled = true;
    loader.hidden      = false;
    const form = new FormData();
    form.append('image', blob, 'capture.png');
    fetch('/analyze', { method: 'POST', body: form })
      .then(res => {
        if (res.redirected) window.location = res.url;
        else return res.text().then(txt => message.textContent = txt);
      })
      .catch(() => message.textContent = 'Upload failed.');
  }, 'image/png');
});
