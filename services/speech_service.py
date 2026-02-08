from openai import OpenAI


class SpeechService:
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def transcribe(self, file_bytes: bytes, filename: str = "audio.wav") -> str:
        # NOTE: The OpenAI SDK expects a file-like object tuple: (filename, bytes)
        resp = self.client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(filename, file_bytes),
        )
        return resp.text
