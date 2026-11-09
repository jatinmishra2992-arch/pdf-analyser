import tempfile
import time
from pathlib import Path

import fitz  # PyMuPDF

from services.ai_provider import ask_ai_about_pdf

PAGES_PER_PART = 10  # small parts finish fast and avoid time-outs

PART_PROMPT = """You are making study notes from part of an educational PDF.
This part contains pages {first} to {last} of a {total}-page PDF.
Write a detailed summary of ONLY this part, in the same order as the pages.
Use simple, easy language and keep the original meaning.

Keep all important definitions, formulas, examples, code outputs and
key points. Do not add facts that are not in the PDF.

Formatting rules (follow exactly):
- Start each main topic with '# ' and each sub-topic with '## '.
- Start each bullet point with '- '.
- Write other text as normal short paragraphs.
- Wherever the PDF has a diagram, image, graph or table, write one line
  exactly like this at the matching place: [Diagram: short description, page N]
- Use the real page numbers. The first page of this part is page {first}.
- Do not write an introduction or conclusion for the whole document.
- Do not use bold, tables, or any other markdown.
"""


def _ask_with_retry(path, prompt, tries=3):
    for attempt in range(tries):
        try:
            return ask_ai_about_pdf(path, prompt)
        except RuntimeError as e:
            msg = str(e)
            fatal = "API key" in msg or "model name" in msg
            if fatal or attempt == tries - 1:
                raise
            time.sleep(10 * (attempt + 1))  # wait, then try again


def make_detailed_summary(pdf_path):
    src = fitz.open(str(pdf_path))
    total = len(src)
    pieces = []

    with tempfile.TemporaryDirectory() as tmp:
        for start in range(0, total, PAGES_PER_PART):
            end = min(start + PAGES_PER_PART, total) - 1
            part = fitz.open()
            part.insert_pdf(src, from_page=start, to_page=end)
            part_path = Path(tmp) / f"part_{start}.pdf"
            part.save(str(part_path))
            part.close()

            prompt = PART_PROMPT.format(first=start + 1, last=end + 1,
                                        total=total)
            try:
                pieces.append(_ask_with_retry(part_path, prompt))
            except RuntimeError as e:
                if not pieces:
                    raise  # nothing worked, show the error
                pieces.append(f"[Pages {start + 1} to {total} could not be "
                              f"summarized: {e}]")
                break
            time.sleep(2)

    src.close()
    return "\n\n".join(pieces)