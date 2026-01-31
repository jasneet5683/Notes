import speech_recognition as sr
from app.utils import generate_ai_summary
import io

def transcribe_audio_and_summarize(file_bytes):
    recognizer = sr.Recognizer()
    
    # Convert bytes to a file-like object
    audio_file = io.BytesIO(file_bytes)
    
    try:
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            transcribed_text = recognizer.recognize_google(audio_data)
            
        summary = generate_ai_summary(transcribed_text)
        
        return {
            "status": "success",
            "transcription": transcribed_text,
            "summary": summary
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}
