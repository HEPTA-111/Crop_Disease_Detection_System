import os
from datetime import datetime
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

from model_utils import predict

# --- Flask & DB setup ---
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev‑key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///instance/florapatho.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- Models ---
class Analysis(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)
    image_path  = db.Column(db.String(256), nullable=False)
    crop_label  = db.Column(db.String(64), nullable=False)
    disease_label = db.Column(db.String(64), nullable=False)
    confidence  = db.Column(db.Float, nullable=False)

class Feedback(db.Model):
    id          = db.Column(db.Integer, primary_key=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey("analysis.id"), nullable=False)
    correct     = db.Column(db.Boolean, nullable=False)

# Create the database tables
@app.before_first_request
def create_tables():
    os.makedirs("uploads", exist_ok=True)
    db.create_all()

# --- Routes ---
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/analyze", methods=["POST"])
def analyze():
    img_file = request.files.get("image")
    if not img_file:
        flash("No image uploaded.", "error")
        return redirect(url_for("index"))

    # Save upload
    filename = secure_filename(datetime.utcnow().isoformat() + "_" + img_file.filename)
    save_path = os.path.join("uploads", filename)
    img_file.save(save_path)

    # Model inference
    crop, disease, conf = predict(save_path)

    # Record in DB
    analysis = Analysis(
        image_path=save_path,
        crop_label=crop,
        disease_label=disease,
        confidence=conf
    )
    db.session.add(analysis)
    db.session.commit()

    # Redirect to results with analysis ID
    return redirect(url_for("results", analysis_id=analysis.id))

@app.route("/results")
def results():
    aid = request.args.get("analysis_id", type=int)
    analysis = Analysis.query.get_or_404(aid)

    # Example images: lookup static/images/<disease>_1.jpg, etc.
    examples = []
    for i in range(1, 4):
        path = f"{analysis.disease_label.lower().replace(' ', '_')}_{i}.jpg"
        if os.path.exists(os.path.join("static/images", path)):
            examples.append(url_for("static", filename=f"images/{path}"))

    return render_template(
        "results.html",
        crop_name=analysis.crop_label,
        disease_name=analysis.disease_label,
        confidence=round(analysis.confidence * 100, 1),
        disease_description="…fetch from your disease DB…",
        causes="…",
        prevention="…",
        treatment_options=["…"],
        example_images=examples,
        session_id=analysis.id
    )

@app.route("/feedback", methods=["POST"])
def feedback():
    aid = request.form.get("session_id", type=int)
    correct = request.form.get("feedback") == "correct"

    fb = Feedback(analysis_id=aid, correct=correct)
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
    # Flatten for template
    history = []
    for analysis, fb in records:
        history.append({
            "timestamp": analysis.timestamp.strftime("%Y-%m-%d %H:%M"),
            "crop": analysis.crop_label,
            "disease": analysis.disease_label,
            "confidence": f"{analysis.confidence*100:.1f}%",
            "feedback": "Yes" if fb and fb.correct else ("No" if fb else "—")
        })
    return render_template("history.html", records=history)

if __name__ == "__main__":
    app.run(debug=True)
