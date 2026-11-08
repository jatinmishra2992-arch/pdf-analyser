import uuid
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from services.pdf_reader import get_pdf_info
from services.summarizer import make_detailed_summary

load_dotenv()

BASE = Path(__file__).parent
UPLOADS = BASE / "uploads"
OUTPUTS = BASE / "outputs"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)

MAX_PAGES = 100  # limit of the AI for one PDF

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

    try:
        text = make_detailed_summary(path)
    except Exception as e:
        return jsonify(error=str(e)), 500

    (OUTPUTS / f"{file_id}_detailed.txt").write_text(text, encoding="utf-8")
    return jsonify(summary=text)


@app.errorhandler(413)
def too_big(e):
    return jsonify(error="File is too large (max 32 MB)."), 413


if __name__ == "__main__":
    app.run(debug=True)