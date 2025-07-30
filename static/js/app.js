const video      = document.getElementById('video');
const canvas     = document.getElementById('canvas');
const snapBtn    = document.getElementById('snap-btn');
const uploadForm = document.getElementById('upload-form');
const analyzeBtn = document.getElementById('analyze-btn');
const loader     = document.getElementById('loader');
const message    = document.getElementById('message');

let streaming = false;

uploadForm.addEventListener('submit', () => {
  analyzeBtn.disabled = true;
  loader.hidden      = false;
});

snapBtn.addEventListener('click', () => {
  // First click: start camera
  if (!streaming) {
    if (navigator.mediaDevices?.getUserMedia) {
      navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
          video.srcObject = stream;
          streaming = true;
          video.play();
          snapBtn.textContent = "Capture Photo";
        })
        .catch(() => {
          message.textContent = 'Camera not available.';
        });
    } else {
      message.textContent = 'Camera API not supported.';
    }
    return;
  }

  // Subsequent click: capture image
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
