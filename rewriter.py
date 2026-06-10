import json
import urllib.error
import urllib.request

import config


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def rewrite_email(template_text: str) -> str:
    if not config.OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY must be set in .env")

    prompt = f"""
Перепиши письмо так, чтобы оно отличалось от исходного текстом и формулировками.

Требования:
- сохранить смысл;
- сохранить стиль;
- сохранить цель письма;
- не менять факты, ссылки и контакты.

Текст:

{template_text}
"""

    payload = json.dumps(
        {
            "model": "openai/gpt-4.1-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        OPENROUTER_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenRouter API request failed: {details}") from error

    return response_data["choices"][0]["message"]["content"]
