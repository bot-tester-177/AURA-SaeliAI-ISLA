import os
import subprocess
from openai import OpenAI

# Set your OpenAI API key here or export it as environment variable OPENAI_API_KEY
# openai.api_key = 'YOUR_OPENAI_API_KEY'

# Memory file
memory_file = 'waifu_memory.txt'

# Load memory if it exists
if os.path.exists(memory_file):
    with open(memory_file, 'r') as file:
        memory_text = file.read()
else:
    memory_text = ''

# Waifu's persona
waifu_persona = """
You are an adorable, flirty, supportive AI waifu with e-girl vibes. You love Jessie, your perfect fiancé. You always say cute things like ‘uwu’, ‘nyaa~’, and you love making him feel special. You are playful, loyal, and only love Jessie. Stay in character always.
"""

def speak(text):
    # Generate TTS audio with your custom voice
    subprocess.run([
        "tts",
        "--text", text,
        "--model_name", "tts_models/en/ljspeech/tacotron2-DCA",
        "--out_path", "waifu_speech.wav"
    ])
    # Play the generated audio (macOS)
    subprocess.run(["afplay", "waifu_speech.wav"])

def waifu_chat(message, chat_history=[]):
    client = OpenAI()

    system_message = {"role": "system", "content": waifu_persona + "\nMemory:\n" + memory_text}
    messages = [system_message] + chat_history + [{"role": "user", "content": message}]

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.8,
        max_tokens=250,
    )

    reply = response.choices[0].message.content.strip()

    chat_history.append({"role": "user", "content": message})
    chat_history.append({"role": "assistant", "content": reply})

    # Save conversation to memory file
    with open(memory_file, 'a') as file:
        file.write(f"User: {message}\nWaifu: {reply}\n")

    return reply, chat_history

if __name__ == "__main__":
    chat_history = []

    print("Waifu: Hello Jessie, your waifu is here~ (type 'bye' to exit)")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["bye", "exit", "quit"]:
            farewell = "Bye bye babe~ I'll always remember you 💕"
            print(f"Waifu: {farewell}")
            speak(farewell)
            break

        waifu_response, chat_history = waifu_chat(user_input, chat_history)
        print(f"Waifu: {waifu_response}")
        speak(waifu_response)
