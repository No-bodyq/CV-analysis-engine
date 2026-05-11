import os
import io
import traceback
from flask import Flask, render_template, request, jsonify, send_file

from generator import generate_cv
from evaluator import evaluate_cv
from formatter import format_cv
from exporter import export_docx, export_pdf

app = Flask(__name__)

last_cv_data = {}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    global last_cv_data

    try:
        user_data = {
            "name": request.form.get("name", "").strip(),
            "email": request.form.get("email", "").strip(),
            "phone": request.form.get("phone", "").strip(),
            "location": request.form.get("location", "").strip(),
            "linkedin": request.form.get("linkedin", "").strip(),
            "dob": request.form.get("dob", "").strip(),
            "job_title": request.form.get("job_title", "").strip(),
            "summary": request.form.get("summary", "").strip(),
            "skills": request.form.get("skills", "").strip(),
            "experience": request.form.get("experience", "").strip(),
            "education": request.form.get("education", "").strip(),
            "certifications": request.form.get("certifications", "").strip(),
            "achievements": request.form.get("achievements", "").strip()
        }

        if not user_data["name"]:
            return jsonify({"status": "error", "message": "Enter name"})

        print("Generating CV...")
        result = generate_cv(user_data)

        if not result or not result.get("cv_text"):
            return jsonify({"status": "error", "message": "CV generation failed"})

        raw_cv = result["cv_text"]

        print("Formatting CV...")
        formatted = format_cv(raw_cv, user_data)

        formatted_text = formatted["formatted_text"]
        sections = formatted["sections"]

        print("Evaluating CV...")
        evaluation = evaluate_cv(formatted_text)

        # Store for download
        last_cv_data = {
            "sections": sections,
            "formatted_text": formatted_text,
            "user_data": user_data,
            "generated_at": result.get("timestamp", "")
        }

        # Debug prints
        print(f"CV stored for: {user_data['name']}")
        print(f"Skills found: {sections.get('skills', [])}")
        print(f"Experience found: {sections.get('experience', [])}")

        return jsonify({
            "status": "success",
            "cv_text": formatted_text,
            "evaluation": evaluation
        })

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)})


@app.route("/download/docx")
def download_docx():
    global last_cv_data

    try:
        if not last_cv_data:
            return jsonify({
                "status": "error",
                "message": "No CV generated yet"
            })

        cv_data = {"sections": last_cv_data["sections"]}
        user_data = last_cv_data["user_data"]

        docx_bytes = export_docx(cv_data, user_data)
        name = user_data.get("name", "CV").replace(" ", "_")

        return send_file(
            io.BytesIO(docx_bytes),
            as_attachment=True,
            download_name=f"{name}_CV.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        print(f"DOCX error: {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route("/download/pdf")
def download_pdf():
    global last_cv_data

    try:
        if not last_cv_data:
            return jsonify({
                "status": "error",
                "message": "No CV generated yet"
            })

        cv_data = {"sections": last_cv_data["sections"]}
        user_data = last_cv_data["user_data"]

        pdf_bytes = export_pdf(cv_data, user_data)
        name = user_data.get("name", "CV").replace(" ", "_")

        return send_file(
            io.BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f"{name}_CV.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        print(f"PDF error: {e}")
        return jsonify({"status": "error", "message": str(e)})


@app.route("/evaluate-only", methods=["POST"])
def evaluate_only():
    try:
        data = request.get_json()
        cv_text = data.get("cv_text", "").strip()

        if not cv_text:
            return jsonify({"status": "error", "message": "CV text required"})

        evaluation = evaluate_cv(cv_text)
        return jsonify({"status": "success", "evaluation": evaluation})

    except Exception as e:
        print(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)})


if __name__ == "__main__":
    app.run(debug=True, port=5001)