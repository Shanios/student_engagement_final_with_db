import speech_recognition as sr

r = sr.Recognizer()
r.energy_threshold = 200

with sr.Microphone() as source:
    print("Speak something...")
    r.adjust_for_ambient_noise(source)
    audio = r.listen(source)

try:
    text = r.recognize_google(audio)
    print("You said:", text)

except sr.UnknownValueError:
    print("Error: Could not understand audio (UnknownValueError)")

except sr.RequestError as e:
    print(f"Error: Could not reach Google STT service. Details: {e}")

except Exception as e:
    print(f"Unexpected error: {type(e).__name__} -> {e}")

