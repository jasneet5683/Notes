import openai
from app.config import Config

def generate_ai_summary(text):
    if not Config.OPENAI_API_KEY:
        return "OpenAI API Key missing. Returning raw text."
    
    try:
        client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Summarize the following text concisely."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Summary failed: {str(e)}"
