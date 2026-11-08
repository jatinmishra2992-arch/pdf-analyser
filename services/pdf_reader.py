import fitz  # PyMuPDF


def get_pdf_info(path):
    doc = fitz.open(path)
    if doc.needs_pass:
        raise ValueError("this PDF is password protected")
    pages = len(doc)
    text_chars = sum(len(p.get_text().strip()) for p in doc)
    doc.close()
    return {"pages": pages, "is_scanned": text_chars < 20 * pages}