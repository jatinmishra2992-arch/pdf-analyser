import os
import time
from pathlib import Path

from google import genai
from google.genai import errors, types

MAX_BYTES = 18 * 1024 * 1024  # upload limit for PDF files
TRY_TIMEOUT_MS = 60000        # give each model 60 seconds
BAD_WORDS = ("image", "tts", "live", "audio", "embedding", "robotics",
             "computer", "native", "thinking")
_working_model = None


def _make_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("API key not found. Add GEMINI_API_KEY in your "
                           ".env file or in Render's Environment settings.")
    return genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=TRY_TIMEOUT_MS))


def _candidates(client):
    """Fast models first. The model from GEMINI_MODEL is tried last."""
    seen = set()
    if _working_model:
        seen.add(_working_model)
        yield _working_model

    found = []
    try:
        for m in client.models.list():
            name = (m.name or "").replace("models/", "")
            low = name.lower()
            if "flash" not in low or any(w in low for w in BAD_WORDS):
                continue
            actions = getattr(m, "supported_actions", None) or []
            if actions and "generateContent" not in actions:
                continue
            found.append(name)
    except errors.APIError as e:
        if e.code in (400, 401, 403):
            raise RuntimeError("Your API key is not correct. Create a new "
                               "key in AI Studio and update it.")
        print("[AI] Could not list models:", e, flush=True)
    except Exception as e:
        print("[AI] Could not list models:", e, flush=True)

    found.sort(reverse=True)                                   # newest first
    found.sort(key=lambda n: 0 if "lite" in n.lower() else 1)  # lite first
    for name in found[:3]:
        if name not in seen:
            seen.add(name)
            yield name

    forced = os.getenv("GEMINI_MODEL")
    if forced and forced not in seen:
        yield forced


def _fast_config():
    try:
        return types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"))
    except Exception:
        return None


def _try_model(client, model, contents):
    config = _fast_config()
    try:
        return client.models.generate_content(
            model=model, contents=contents, config=config)
    except errors.APIError as e:
        if config is not None and e.code == 400:
            return client.models.generate_content(
                model=model, contents=contents)
        raise


def _friendly(err):
    if isinstance(err, errors.APIError):
        if err.code == 429:
            return "Free limit reached. Wait a few minutes or try tomorrow."
        if err.code in (500, 503, 504):
            return ("Google's AI is busy right now. Wait a few minutes and "
                    "try again.")
        if err.code == 404:
            return "No AI model was available for your key."
        return f"The AI returned an error: {err.message}"
    return "The AI took too long to answer. Try again in a few minutes."


def _run(client, contents):
    global _working_model
    last_error = None
    for model in _candidates(client):
        started = time.time()
        print(f"[AI] Trying {model} ...", flush=True)
        try:
            response = _try_model(client, model, contents)
        except errors.APIError as e:
            print(f"[AI] {model} failed after {time.time() - started:.0f}s "
                  f"(code {e.code})", flush=True)
            if e.code in (401, 403) or "API key" in str(e):
                raise RuntimeError("Your API key is not correct. Create a "
                                   "new key in AI Studio and update it.")
            last_error = e
            continue
        except Exception as e:
            print(f"[AI] {model} failed after {time.time() - started:.0f}s: "
                  f"{e}", flush=True)
            last_error = e
            continue

        if response.text:
            _working_model = model
            print(f"[AI] {model} answered in {time.time() - started:.0f}s",
                  flush=True)
            return response.text
        last_error = RuntimeError("empty answer")

    raise RuntimeError(_friendly(last_error) if last_error
                       else "No AI model could be found for your key.")


def ask_ai_about_pdf(pdf_path, instruction):
    """Send a PDF file plus an instruction to the AI."""
    client = _make_client()
    pdf_bytes = Path(pdf_path).read_bytes()
    if len(pdf_bytes) > MAX_BYTES:
        raise RuntimeError("This PDF is bigger than 18 MB. Try a smaller PDF.")
    return _run(client, [
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        instruction,
    ])


def ask_ai_about_text(text, instruction):
    """Send plain text plus an instruction. This is faster than a PDF.
    To use another AI provider later, only change this file."""
    client = _make_client()
    return _run(client, [instruction + "\n\nHere is the text:\n\n" + text])