import math
import tempfile
import time
from pathlib import Path

import fitz  # PyMuPDF

from services.ai_provider import ask_ai_about_pdf, ask_ai_about_text

PAGES_PER_PART = 10
MIN_CHARS_PER_PAGE = 150  # less text than this means a scanned part

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
{diagram_rule}- Do not write an introduction or conclusion for the whole document.
- Do not use bold, tables, or any other markdown.
"""

DIAGRAM_RULE = (
    "- Wherever the PDF has a diagram, image, graph or table, write one line\n"
    "  exactly like this at the matching place: "
    "[Diagram: short description, page N]\n"
    "- Use the real page numbers. The first page of this part is page "
    "{first}.\n")
TEXT_RULE = "- You only see the text, so do not mention diagrams or images.\n"


def _build_prompt(first, last, total, with_diagrams):
    rule = DIAGRAM_RULE.format(first=first) if with_diagrams else TEXT_RULE
    return PART_PROMPT.format(first=first, last=last, total=total,
                              diagram_rule=rule)


def _with_retry(call, tries=2):
    for attempt in range(tries):
        try:
            return call()
        except RuntimeError as e:
            if "API key" in str(e) or attempt == tries - 1:
                raise
            time.sleep(8)


def make_detailed_summary(pdf_path, progress=None):
    src = fitz.open(str(pdf_path))
    total = len(src)
    parts_total = max(1, math.ceil(total / PAGES_PER_PART))
    pieces = []

    with tempfile.TemporaryDirectory() as tmp:
        for idx, start in enumerate(range(0, total, PAGES_PER_PART)):
            end = min(start + PAGES_PER_PART, total) - 1
            if progress:
                progress(f"Reading part {idx + 1} of {parts_total} "
                         f"(pages {start + 1} to {end + 1})")

            text = "\n\n".join(
                f"--- Page {i + 1} ---\n{src[i].get_text()}"
                for i in range(start, end + 1))
            has_text = len(text) >= MIN_CHARS_PER_PAGE * (end - start + 1)

            if has_text:
                prompt = _build_prompt(start + 1, end + 1, total, False)
                call = lambda t=text, p=prompt: ask_ai_about_text(t, p)
            else:
                part = fitz.open()
                part.insert_pdf(src, from_page=start, to_page=end)
                part_path = Path(tmp) / f"part_{start}.pdf"
                part.save(str(part_path))
                part.close()
                prompt = _build_prompt(start + 1, end + 1, total, True)
                call = lambda f=part_path, p=prompt: ask_ai_about_pdf(f, p)

            try:
                pieces.append(_with_retry(call))
            except RuntimeError as e:
                if not pieces:
                    raise  # nothing worked, show the error
                pieces.append(f"[Pages {start + 1} to {total} could not be "
                              f"summarized: {e}]")
                break
            time.sleep(1)

    src.close()
    return "\n\n".join(pieces)