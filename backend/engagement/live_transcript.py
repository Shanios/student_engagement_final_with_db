import speech_recognition as sr

recognizer = sr.Recognizer()
mic = sr.Microphone()

print("Real-time transcript started...")
with mic as source:
    recognizer.adjust_for_ambient_noise(source)

while True:
    try:
        with mic as source:
            audio = recognizer.listen(source, phrase_time_limit=4)

        text = recognizer.recognize_google(audio)
        print(">>", text)

    except sr.UnknownValueError:
        pass  # ignore silence
    except KeyboardInterrupt:
        print("Stopped.")
        break
    except Exception as e:
        print("Error:", e)

