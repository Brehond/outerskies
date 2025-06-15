import os
import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"

def generate_interpretation(prompt: str, model: str = "openai/gpt-4") -> str:
    print("Sending prompt to OpenRouter:", repr(prompt))  # Debug
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }
    try:
        response = httpx.post(OPENROUTER_ENDPOINT, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content']
        print("Received AI content:", repr(content))  # Debug
        return content
    except Exception as e:
        print("Error during OpenRouter API call:", e)
        return f"Error: {e}"
