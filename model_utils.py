import os
import json
import numpy as np
from PIL import Image, UnidentifiedImageError
import tensorflow as tf

# Load label mapping
with open("labels.json") as f:
    LABEL_MAP = json.load(f)

# Path to your Keras model saved in .h5 format
MODEL_PATH = "model.h5"
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at {MODEL_PATH}. Make sure you place 'model.h5' in the root directory.")

# Load the model once
model = tf.keras.models.load_model(MODEL_PATH)

# Inspect the model's input shape
# model.input_shape is something like (None, height, width, channels)
_, IMG_H, IMG_W, IMG_C = model.input_shape

def preprocess_image(image_path):
    """
    Load image, resize & convert channels to match the model,
    normalize to [0,1], and return a batch of shape (1, H, W, C).
    """
    try:
        img = Image.open(image_path)
    except UnidentifiedImageError:
        raise ValueError("Uploaded file is not a valid image.")

    # Convert channels
    if IMG_C == 1:
        img = img.convert("L")   # grayscale
    else:
        img = img.convert("RGB")

    # Resize to model’s expected dimensions
    img = img.resize((IMG_W, IMG_H))
    arr = np.array(img, dtype=np.float32) / 255.0

    # If grayscale, ensure shape is (H, W, 1)
    if IMG_C == 1:
        arr = np.expand_dims(arr, axis=-1)

    # Return batch dimension
    return np.expand_dims(arr, axis=0)

def predict(image_path):
    """
    Runs the model on the preprocessed image.
    Returns:
      crop_name (str), disease_name (str), confidence (float 0–1)
    """
    batch = preprocess_image(image_path)
    preds = model.predict(batch)[0]
    idx   = int(np.argmax(preds))
    conf  = float(preds[idx])
    crop, disease = LABEL_MAP.get(str(idx), ("Unknown", "Unknown"))
    return crop, disease, conf
