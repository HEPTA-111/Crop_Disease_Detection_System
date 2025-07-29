import json
import tensorflow as tf
import numpy as np
from PIL import Image

# Load label mapping and model once at startup
with open("labels.json") as f:
    LABEL_MAP = json.load(f)  # e.g. {"0": ["Wheat","Leaf Rust"], ...}

# Adjust this path if you save your model elsewhere
MODEL_PATH = "path/to/your/saved_model"

model = tf.keras.models.load_model(MODEL_PATH)

def preprocess_image(image_path, target_size=(224, 224)):
    """Load an image file, resize & scale to [0,1], return as batch."""
    img = Image.open(image_path).convert("RGB")
    img = img.resize(target_size)
    arr = np.array(img, dtype=np.float32) / 255.0
    return np.expand_dims(arr, axis=0)

def predict(image_path):
    """
    Run model on the image, return top result:
      crop_name, disease_name, confidence (float 0–1)
    """
    batch = preprocess_image(image_path)
    preds = model.predict(batch)[0]       # assuming model outputs a 1D softmax
    idx = int(np.argmax(preds))
    conf = float(preds[idx])
    crop, disease = LABEL_MAP[str(idx)]
    return crop, disease, conf
