import os
import json
import uuid
import time
from datetime import datetime

from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

from main import match_cv
from cv_reader import extract_cv_text


# APP INIT

app = Flask(__name__)


# CONFIG

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

P5_FILE = os.path.join(BASE_DIR, "p5_job_data.json")
P4_RESULTS_FILE = os.path.join(BASE_DIR, "..", "p4_dashboard", "match_results.json")


# HELPERS
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "status": "error",
        "message": "File too large (max 5MB)"
    }), 413


# ROUTE 1 — HOME
@app.route("/")
def home():
    return render_template("index.html")


# ROUTE 2 — MATCH ENGINE
@app.route("/match", methods=["POST"])
def match():
    start_time = time.time()

    try:
        cv_text = ""
        job_text = request.form.get("job_text", "").strip()

        # -------- CV INPUT --------
        if "cv_file" in request.files and request.files["cv_file"].filename != "":
            cv_file = request.files["cv_file"]

            if not allowed_file(cv_file.filename):
                return jsonify({
                    "status": "error",
                    "message": "Only PDF or DOCX files are allowed"
                }), 400

            # Save file with unique name
            unique_name = f"{uuid.uuid4().hex}_{secure_filename(cv_file.filename)}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_name)
            cv_file.save(filepath)

            # Extract text from saved file
            try:
                with open(filepath, "rb") as f:
                    cv_text = extract_cv_text(f, unique_name)
            finally:
                # Always clean up the file
                try:
                    os.remove(filepath)
                except:
                    pass

        else:
            cv_text = request.form.get("cv_text", "").strip()

        # -------- AUTO LOAD P5 DATA (OPTIONAL) --------
        if not job_text and os.path.exists(P5_FILE):
            try:
                with open(P5_FILE, "r") as f:
                    saved = json.load(f)
                    job_text = saved.get("job_text", "")
            except:
                pass

        # VALIDATION
        if not cv_text:
            return jsonify({
                "status": "error",
                "message": "Provide CV text or upload PDF/DOCX"
            }), 400

        if not job_text:
            return jsonify({
                "status": "error",
                "message": "Provide job description or use scraper"
            }), 400

        # RUN MATCH
        result = match_cv(cv_text, job_text)

        processing_time = round(time.time() - start_time, 2)

        response_data = {
            "status": "success",
            "data": result.get("data", result),
            "processing_time": processing_time
        }

        # AUTO SAVE TO P4
        try:
            os.makedirs(os.path.dirname(P4_RESULTS_FILE), exist_ok=True)

            if os.path.exists(P4_RESULTS_FILE):
                with open(P4_RESULTS_FILE, "r") as f:
                    existing = json.load(f)
            else:
                existing = []

            result["timestamp"] = datetime.now().isoformat()
            existing.append(result)

            with open(P4_RESULTS_FILE, "w") as f:
                json.dump(existing, f, indent=2)

        except:
            pass

        return jsonify(response_data), 200


    except Exception as e:

        import traceback

        print("FULL ERROR:", traceback.format_exc())

        return jsonify({

            "status": "error",

            "message": f"Something went wrong: {str(e)}"

        }), 500



# ROUTE 3 — RECEIVE FROM P5
@app.route("/api/job-data", methods=["POST"])
def receive_from_extension():
    try:
        data = request.get_json() or {}

        if not data.get("title"):
            return jsonify({
                "status": "error",
                "message": "Invalid job data"
            }), 400

        job_title = data.get("title", "")
        skills = data.get("skills", [])
        qualifications = data.get("qualifications", [])

        job_text = f"""Job Title: {job_title}

Required Skills:
{chr(10).join(f'- {s}' for s in skills)}

Qualifications:
{chr(10).join(f'- {q}' for q in qualifications)}"""

        with open(P5_FILE, "w") as f:
            json.dump({
                "job_title": job_title,
                "job_text": job_text.strip(),
                "skills": skills,
                "qualifications": qualifications,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)

        return jsonify({
            "status": "success",
            "message": f"Job data received: {job_title}"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ROUTE 4 — GET P5 DATA
@app.route("/get-job-data", methods=["GET"])
def get_job_data():
    try:
        if os.path.exists(P5_FILE):
            with open(P5_FILE, "r") as f:
                data = json.load(f)

            return jsonify({
                "status": "success",
                "data": data
            }), 200

        return jsonify({
            "status": "empty",
            "message": "No job data yet"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ROUTE 5 — MANUAL SAVE (P4)
@app.route("/save-result", methods=["POST"])
def save_result():
    try:
        data = request.get_json() or {}

        os.makedirs(os.path.dirname(P4_RESULTS_FILE), exist_ok=True)

        if os.path.exists(P4_RESULTS_FILE):
            try:
                with open(P4_RESULTS_FILE, "r") as f:
                    results = json.load(f)
            except:
                results = []
        else:
            results = []

        data["timestamp"] = datetime.now().isoformat()
        results.append(data)

        with open(P4_RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2)

        return jsonify({
            "status": "success",
            "message": "Result saved to P4 dashboard"
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# RUN SERVER
if __name__ == "__main__":
    app.run(debug=True)