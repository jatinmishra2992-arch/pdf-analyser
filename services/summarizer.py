from services.ai_provider import ask_ai_about_pdf

DETAILED_PROMPT = """You are making study notes from an educational PDF.
Write a detailed summary that covers EVERY important topic, in the same
order as the PDF. Use simple, easy language and keep the original meaning.

Keep all important definitions, formulas, examples, code outputs and
key points. Do not add facts that are not in the PDF.

Formatting rules (follow exactly):
- Start each main topic with '# ' and each sub-topic with '## '.
- Start each bullet point with '- '.
- Write other text as normal short paragraphs.
- Wherever the PDF has a diagram, image, graph or table, write one line
  exactly like this at the matching place: [Diagram: short description, page N]
- Do not use bold, tables, or any other markdown.
"""


def make_detailed_summary(pdf_path):
    return ask_ai_about_pdf(pdf_path, DETAILED_PROMPT)