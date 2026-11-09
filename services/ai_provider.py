import os
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

MAX_BYTES = 18 * 1024 * 1024  # the free upload limit for this method


def _generate(client, model, contents, fast):
    config = None
    if fast:  # ask the AI to think less, so it answers faster
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"))
    return client.models.generate_content(
        model=model, contents=contents, config=config)


def ask_ai_about_pdf(pdf_path, instruction):
    """Send the PDF plus an instruction to the AI.
    To use another AI provider later, only change this file."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("API key not found. Check your .env file.")
    model = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    pdf_bytes = Path(pdf_path).read_bytes()
    if len(pdf_bytes) > MAX_BYTES:
        raise RuntimeError("This PDF is bigger than 18 MB. Try a smaller PDF.")

    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=90000),  # 90 seconds
    )
    contents = [
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        instruction,
    ]

    started = time.time()
    print(f"[AI] Sending {len(pdf_bytes) // 1024} KB to {model} ...",
          flush=True)
    try:
        try:
            response = _generate(client, model, contents, fast=True)
        except errors.APIError as e:
            if e.code == 400 and "thinking" in str(e).lower():
                response = _generate(client, model, contents, fast=False)
            else:
                raise
    except errors.APIError as e:
        text = str(e)
        print(f"[AI] Error after {time.time() - started:.0f}s:", text,
              flush=True)
        if e.code == 429:
            raise RuntimeError(
                "Free limit reached. Wait a few minutes or try tomorrow.")
        if e.code in (503, 504):
            raise RuntimeError(
                "Google's AI is busy or slow right now. Try again in a few "
                "minutes.")
        if e.code == 404:
            raise RuntimeError(
                "This AI model name was not found. Change GEMINI_MODEL "
                "to another model shown in AI Studio.")
        if "API key" in text or e.code in (401, 403):
            raise RuntimeError(
                "Your API key is not correct. Check the .env file.")
        raise RuntimeError(f"The AI returned an error: {e.message}")
    except Exception as e:
        print("[AI] Error:", e, flush=True)
        raise RuntimeError(f"Could not reach the AI or it took too long: {e}")

    print(f"[AI] Answer received in {time.time() - started:.0f}s", flush=True)
    if not response.text:
        raise RuntimeError("The AI returned no text. Try again.")
    return response.text