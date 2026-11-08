import os
from pathlib import Path

from google import genai
from google.genai import errors, types

MAX_BYTES = 18 * 1024 * 1024  # the free upload limit for this method


def ask_ai_about_pdf(pdf_path, instruction):
    """Send the whole PDF plus an instruction to the AI.
    To use another AI provider later, only change this file."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("API key not found. Check your .env file.")
    model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")

    pdf_bytes = Path(pdf_path).read_bytes()
    if len(pdf_bytes) > MAX_BYTES:
        raise RuntimeError("This PDF is bigger than 18 MB. Try a smaller PDF.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=180000),  # 3 minutes
    )

    print(f"[AI] Sending PDF to {model} ...", flush=True)
    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(data=pdf_bytes,
                                      mime_type="application/pdf"),
                instruction,
            ],
        )
    except errors.APIError as e:
        text = str(e)
        print("[AI] Error:", text, flush=True)
        if e.code == 429:
            raise RuntimeError(
                "Free limit reached. Wait a few minutes or try tomorrow.")
        if e.code == 404:
            raise RuntimeError(
                "This AI model name was not found. Change GEMINI_MODEL "
                "in the .env file to another model shown in AI Studio.")
        if "API key" in text or e.code in (401, 403):
            raise RuntimeError(
                "Your API key is not correct. Check the .env file.")
        raise RuntimeError(f"The AI returned an error: {e.message}")
    except Exception as e:
        print("[AI] Error:", e, flush=True)
        raise RuntimeError(f"Could not reach the AI or it took too long: {e}")

    print("[AI] Answer received.", flush=True)
    if not response.text:
        raise RuntimeError("The AI returned no text. Try again.")
    return response.text