import os
import json
from datetime import datetime
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

from model_utils import predict
from info_utils  import get_disease_info

# Load environment variables from .env
load_dotenv()

# --- Flask setup ---
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key")

# Database in the instance folder
DB_PATH = os.path.join(app.instance_path, "florapatho.db")
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- Load all possible crops for correction dropdown ---
with open("labels.json") as f:
    LABEL_MAP = json.load(f)
ALL_CROPS = sorted({crop for crop, _ in LABEL_MAP.values()})

# --- Models ---
class Analysis(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow)
    image_path    = db.Column(db.String(256), nullable=False)
    crop_label    = db.Column(db.String(64), nullable=False)
    disease_label = db.Column(db.String(64), nullable=False)
    confidence    = db.Column(db.Float, nullable=False)

class Feedback(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analysis.id"), nullable=False)
    correct     = db.Column(db.Boolean, nullable=False)

# --- Routes ---
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    img_file = request.files.get("image")
    if not img_file:
        flash("Please upload an image.", "error")
        return redirect(url_for("index"))

    # Save upload
    filename    = secure_filename(datetime.utcnow().isoformat() + "_" + img_file.filename)
    uploads_dir = os.path.join("static", "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    save_path   = os.path.join(uploads_dir, filename)
    img_file.save(save_path)

    # Model inference
    try:
        crop, disease, conf = predict(save_path)
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("index"))

    # Persist result
    analysis = Analysis(
        image_path=save_path.replace("\\", "/"),
        crop_label=crop,
        disease_label=disease,
        confidence=conf
    )
    db.session.add(analysis)
    db.session.commit()

    return redirect(url_for("results", analysis_id=analysis.id))

@app.route("/results")
def results():
    aid      = request.args.get("analysis_id", type=int)
    analysis = Analysis.query.get_or_404(aid)

    image_url = url_for("static", filename=f"uploads/{os.path.basename(analysis.image_path)}")

    # Fetch disease info, log errors if any
    try:
        desc, causes, prev, treats = get_disease_info(
            analysis.crop_label,
            analysis.disease_label
        )
    except Exception as e:
        app.logger.error(f"Error fetching disease info from OpenAI: {e}")
        desc, causes, prev, treats = (
            "No additional information available.",
            "—", "—", ["—"]
        )

    low_conf = analysis.confidence < 0.5
    note     = "⚠️ Confidence is low—results may be unreliable." if low_conf else ""

    return render_template(
        "results.html",
        crop_name=analysis.crop_label,
        disease_name=analysis.disease_label,
        confidence=round(analysis.confidence * 100, 1),
        image_url=image_url,
        disease_description=desc,
        causes=causes,
        prevention=prev,
        treatment_options=treats,
        session_id=analysis.id,
        low_confidence_note=note,
        all_crops=ALL_CROPS
    )

@app.route("/correct_crop", methods=["POST"])
def correct_crop():
    analysis_id = request.form.get("analysis_id", type=int)
    new_crop    = request.form.get("new_crop")
    analysis    = Analysis.query.get_or_404(analysis_id)
    if new_crop and new_crop != analysis.crop_label:
        analysis.crop_label = new_crop
        db.session.commit()
        flash(f"Crop corrected to {new_crop}.", "message")
    return redirect(url_for("results", analysis_id=analysis_id))

@app.route("/feedback", methods=["POST"])
def feedback():
    aid     = request.form.get("session_id", type=int)
    correct = request.form.get("feedback") == "correct"
    fb      = Feedback(analysis_id=aid, correct=correct)
    db.session.add(fb)
    db.session.commit()
    return redirect(url_for("history"))

@app.route("/history")
def history():
    records = (
        db.session.query(Analysis, Feedback)
        .outerjoin(Feedback, Analysis.id == Feedback.analysis_id)
        .order_by(Analysis.timestamp.desc())
        .all()
    )
    history = []
    for analysis, fb in records:
        history.append({
            "timestamp":  analysis.timestamp.strftime("%Y-%m-%d %H:%M"),
            "crop":       analysis.crop_label,
            "disease":    analysis.disease_label,
            "confidence": f"{analysis.confidence*100:.1f}%",
            "feedback":   "Yes" if fb and fb.correct else ("No" if fb else "—")
        })
    return render_template("history.html", records=history)

if __name__ == "__main__":
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(os.path.join("static", "uploads"), exist_ok=True)
    with app.app_context():
        db.create_all()
    app.run(debug=True)
