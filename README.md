# Smart PDF Analyzer – AI Notes Generator

A web app that turns long educational PDFs into a detailed, easy-to-read summary using AI.

**Live demo:** https://pdf-analyser-cmzw.onrender.com

(The free server sleeps when unused, so the first load can take about a minute.)

## Features
- Upload a PDF and see its name and page count
- Preview the PDF in the browser
- AI detailed summary with headings and bullet points
- Works with scanned PDFs too

## Built with
Python, Flask, PyMuPDF, HTML, CSS, JavaScript, Google Gemini API

## Coming next
- "Make It Concise" button
- Keeping the original diagrams and images
- Download the summary as a PDF

## Run it on your laptop
1. Install the tools: `pip install -r requirements.txt`
2. Make a file named `.env` and add:
   GEMINI_API_KEY=your-key
   GEMINI_MODEL=gemini-3.8-flash
3. Run: `python app.py`
4. Open http://127.0.0.1:5000
