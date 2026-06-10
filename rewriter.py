import requests

from main import OPENROUTER_API_KEY


def rewrite_email(template_text: str) -> str:
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

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "openai/gpt-4.1-mini",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        },
        timeout=60
    )

    response.raise_for_status()

    return response.json()["choices"][0]["message"]["content"]