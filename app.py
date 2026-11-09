import threading
import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from services.pdf_reader import get_pdf_info
from services.summarizer import make_detailed_summary

load_dotenv()

BASE = Path(__file__).parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

MAX_PAGES = 100
JOBS = {}  # job_id -> {"status": ..., "summary": ..., "error": ...}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("pdf")
    if not file or file.filename == "":
        return jsonify(error="Please choose a PDF file."), 400
    if not file.filename.lower().endswith(".pdf"):
        return jsonify(error="Only PDF files are allowed."), 400

    file_id = uuid.uuid4().hex
    path = UPLOADS / f"{file_id}.pdf"
    file.save(path)
    try:
        info = get_pdf_info(path)
    except Exception as e:
        path.unlink(missing_ok=True)
        return jsonify(error=f"Could not read this PDF: {e}"), 400

    return jsonify(file_id=file_id, name=file.filename, **info)


def run_job(job_id, file_id, path):
    try:
        text = make_detailed_summary(path)
        (OUTPUTS / f"{file_id}_detailed.txt").write_text(text, encoding="utf-8")
        JOBS[job_id] = {"status": "done", "summary": text}
    except Exception as e:
        JOBS[job_id] = {"status": "error", "error": str(e)}


@app.route("/summarize", methods=["POST"])
def summarize():
    body = request.get_json(silent=True) or {}
    file_id = str(body.get("file_id", ""))
    path = UPLOADS / f"{file_id}.pdf"
    if not file_id.isalnum() or not path.exists():
        return jsonify(error="Please upload your PDF again."), 400

    info = get_pdf_info(path)
    if info["pages"] > MAX_PAGES:
        return jsonify(
            error=f"This PDF has {info['pages']} pages. Right now the limit "
                  f"is {MAX_PAGES} pages."), 400

    job_id = uuid.uuid4().hex
    JOBS[job_id] = {"status": "working"}
    threading.Thread(target=run_job, args=(job_id, file_id, path),
                     daemon=True).start()
    return jsonify(job_id=job_id)


@app.route("/status/<job_id>")
def status(job_id):
    job = JOBS.get(job_id)
    if not job:
        return jsonify(status="error",
                       error="The server restarted. Please upload your PDF "
                             "again and retry."), 404
    return jsonify(job)


@app.errorhandler(Exception)
def handle_any_error(e):
    if isinstance(e, HTTPException):
        return jsonify(error=e.description), e.code
    return jsonify(error=f"Server error: {e}"), 500


if __name__ == "__main__":
    app.run(debug=True)