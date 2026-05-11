import json
import io
import os
import sys
import time
import traceback
import uuid
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

import p4_dashboard.analytics_dashboard as analytics

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
P1_DIR = os.path.join(BASE_DIR, "p1_cv_generator")
P3_DIR = os.path.join(BASE_DIR, "p3_match_engine")
if P1_DIR not in sys.path:
    sys.path.insert(0, P1_DIR)
if P3_DIR not in sys.path:
    sys.path.insert(0, P3_DIR)

from generator import generate_cv
from evaluator import evaluate_cv
from formatter import format_cv
from exporter import export_docx, export_pdf
from main import match_cv
from cv_reader import extract_cv_text
import p3_match_engine.gemini_service as gemini_service

app = Flask(__name__, template_folder='p4_dashboard/templates')

UPLOAD_FOLDER = os.path.join(P3_DIR, "uploads")
ALLOWED_EXTENSIONS = {"pdf", "docx"}
MAX_FILE_SIZE = 5 * 1024 * 1024

P5_FILE = os.path.join(P3_DIR, "p5_job_data.json")
P4_RESULTS_FILE = os.path.join(P3_DIR, "..", "p4_dashboard", "match_results.json")

app.config["MAX_CONTENT_LENGTH"] = MAX_FILE_SIZE
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
analytics.ensure_dashboard_storage()
last_cv_data = {}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.errorhandler(413)
def too_large(e):
    return jsonify({
        "status": "error",
        "message": "File too large (max 5MB)"
    }), 413


@app.route('/')
def index():
    dashboard = analytics.build_dashboard_payload()
    return render_template('dashboard.html', dashboard=dashboard)


@app.route('/match-engine')
def match_engine():
    return send_from_directory(os.path.join(P3_DIR, 'templates'), 'index.html')


@app.route('/cv-generator')
def cv_generator():
    return send_from_directory(os.path.join(P1_DIR, 'templates'), 'index.html')


@app.route('/generate', methods=['POST'])
def generate():
    global last_cv_data

    try:
        user_data = {
            'name': request.form.get('name', '').strip(),
            'email': request.form.get('email', '').strip(),
            'phone': request.form.get('phone', '').strip(),
            'location': request.form.get('location', '').strip(),
            'linkedin': request.form.get('linkedin', '').strip(),
            'dob': request.form.get('dob', '').strip(),
            'job_title': request.form.get('job_title', '').strip(),
            'summary': request.form.get('summary', '').strip(),
            'skills': request.form.get('skills', '').strip(),
            'experience': request.form.get('experience', '').strip(),
            'education': request.form.get('education', '').strip(),
            'certifications': request.form.get('certifications', '').strip(),
            'achievements': request.form.get('achievements', '').strip()
        }

        if not user_data['name']:
            return jsonify({'status': 'error', 'message': 'Enter name'})

        result = generate_cv(user_data)
        if not result or not result.get('cv_text'):
            return jsonify({'status': 'error', 'message': 'CV generation failed'})

        raw_cv = result['cv_text']
        formatted = format_cv(raw_cv, user_data)
        formatted_text = formatted['formatted_text']
        sections = formatted['sections']
        evaluation = evaluate_cv(formatted_text)

        last_cv_data = {
            'sections': sections,
            'formatted_text': formatted_text,
            'user_data': user_data,
            'generated_at': result.get('timestamp', '')
        }

        return jsonify({
            'status': 'success',
            'cv_text': formatted_text,
            'evaluation': evaluation
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/download/docx')
def download_docx():
    global last_cv_data

    try:
        if not last_cv_data:
            return jsonify({
                'status': 'error',
                'message': 'No CV generated yet'
            })

        cv_data = {'sections': last_cv_data['sections']}
        user_data = last_cv_data['user_data']
        docx_bytes = export_docx(cv_data, user_data)
        name = user_data.get('name', 'CV').replace(' ', '_')

        return send_file(
            io.BytesIO(docx_bytes),
            as_attachment=True,
            download_name=f'{name}_CV.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/download/pdf')
def download_pdf():
    global last_cv_data

    try:
        if not last_cv_data:
            return jsonify({
                'status': 'error',
                'message': 'No CV generated yet'
            })

        cv_data = {'sections': last_cv_data['sections']}
        user_data = last_cv_data['user_data']
        pdf_bytes = export_pdf(cv_data, user_data)
        name = user_data.get('name', 'CV').replace(' ', '_')

        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f'{name}_CV.pdf',
            mimetype='application/pdf'
        )

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/evaluate-only', methods=['POST'])
def evaluate_only():
    try:
        data = request.get_json() or {}
        cv_text = data.get('cv_text', '').strip()

        if not cv_text:
            return jsonify({'status': 'error', 'message': 'CV text required'})

        evaluation = evaluate_cv(cv_text)
        return jsonify({'status': 'success', 'evaluation': evaluation})

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)})


@app.route('/api/dashboard')
def api_dashboard():
    return jsonify(analytics.build_dashboard_payload())


@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    data = request.get_json(force=False, silent=True)
    if not data:
        data = request.form.to_dict()
    if not data.get('company') or not data.get('job_title'):
        return jsonify({
            "status": "error",
            "message": "Company and job title are required.",
            "debug": {
                "received_keys": sorted(list(data.keys()))
            }
        }), 400

    result = analytics.append_application_feedback(data)
    return jsonify({
        "status": "success",
        "message": "Feedback saved",
        "action": result["action"],
        "application": result["application"],
        "data": analytics.build_dashboard_payload()
    })


@app.route('/api/applications/<application_id>', methods=['DELETE'])
def api_delete_application(application_id):
    result = analytics.delete_application(application_id)

    if not result.get('deleted'):
        return jsonify({
            "status": "error",
            "message": f"Application {application_id} was not found.",
            "debug": {
                "application_id": application_id
            }
        }), 404

    return jsonify({
        "status": "success",
        "message": f"Application {application_id} deleted.",
        "application_id": application_id,
        "data": analytics.build_dashboard_payload()
    })


@app.route('/api/parse-job', methods=['POST'])
def api_parse_job():
    try:
        payload = request.get_json() or {}
        job_text = payload.get('job_text', '')
        if not job_text:
            return jsonify({ 'status': 'error', 'message': 'job_text is required' }), 400

        parsed = gemini_service.analyze_job_description(job_text)
        if not parsed:
            return jsonify({ 'status': 'error', 'message': 'Could not parse job description' }), 500

        return jsonify({ 'status': 'success', 'data': parsed }), 200
    except Exception as e:
        return jsonify({ 'status': 'error', 'message': str(e) }), 500


@app.route("/match", methods=["POST"])
def match():
    start_time = time.time()

    try:
        cv_text = ""
        job_text = request.form.get("job_text", "").strip()

        if "cv_file" in request.files and request.files["cv_file"].filename != "":
            cv_file = request.files["cv_file"]

            if not allowed_file(cv_file.filename):
                return jsonify({
                    "status": "error",
                    "message": "Only PDF or DOCX files are allowed"
                }), 400

            unique_name = f"{uuid.uuid4().hex}_{secure_filename(cv_file.filename)}"
            filepath = os.path.join(UPLOAD_FOLDER, unique_name)
            cv_file.save(filepath)

            try:
                with open(filepath, "rb") as f:
                    cv_text = extract_cv_text(f, unique_name)
            finally:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
        else:
            cv_text = request.form.get("cv_text", "").strip()

        if not job_text and os.path.exists(P5_FILE):
            try:
                with open(P5_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    job_text = saved.get("job_text", "")
            except Exception:
                pass

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

        result = match_cv(cv_text, job_text)
        processing_time = round(time.time() - start_time, 2)

        response_data = {
            "status": "success",
            "data": result.get("data", result),
            "processing_time": processing_time
        }

        try:
            os.makedirs(os.path.dirname(P4_RESULTS_FILE), exist_ok=True)
            if os.path.exists(P4_RESULTS_FILE):
                with open(P4_RESULTS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            else:
                existing = []

            result["timestamp"] = datetime.now().isoformat()
            existing.append(result)

            with open(P4_RESULTS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
        except Exception:
            pass

        return jsonify(response_data), 200

    except Exception as e:
        import traceback

        print("FULL ERROR:", traceback.format_exc())

        return jsonify({
            "status": "error",
            "message": f"Something went wrong: {str(e)}"
        }), 500


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

        with open(P5_FILE, "w", encoding="utf-8") as f:
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


@app.route("/get-job-data", methods=["GET"])
def get_job_data():
    try:
        if os.path.exists(P5_FILE):
            with open(P5_FILE, "r", encoding="utf-8") as f:
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


@app.route("/save-result", methods=["POST"])
def save_result():
    try:
        data = request.get_json() or {}

        os.makedirs(os.path.dirname(P4_RESULTS_FILE), exist_ok=True)

        if os.path.exists(P4_RESULTS_FILE):
            try:
                with open(P4_RESULTS_FILE, "r", encoding="utf-8") as f:
                    results = json.load(f)
            except Exception:
                results = []
        else:
            results = []

        data["timestamp"] = datetime.now().isoformat()
        results.append(data)

        with open(P4_RESULTS_FILE, "w", encoding="utf-8") as f:
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


if __name__ == '__main__':
    app.run(debug=True, port=5000)
