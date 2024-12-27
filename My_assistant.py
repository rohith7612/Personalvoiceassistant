import speech_recognition as sr
import openai
import pyttsx3
from dotenv import load_dotenv
import os
import sys
import pvporcupine
import pyaudio
import struct
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import pyautogui
from ttkthemes import ThemedTk
from PIL import Image, ImageTk
import pytesseract
import pyperclip
import pytesseract

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

porcupine = None
pa = None
audio_stream = None

running = True

conversation_history = []

engine = pyttsx3.init()

def check_dependencies():
    try:
        import pyaudio
        import pvporcupine
        import pyautogui
        from ttkthemes import ThemedTk
        import PIL
        import pytesseract
        import pyperclip
    except ImportError as e:
        print(f"Missing dependency: {str(e)}")
        print("Please install the required libraries:")
        print("pip install pyaudio pvporcupine SpeechRecognition openai pyttsx3 python-dotenv pyautogui ttkthemes pillow pytesseract pyperclip")
        sys.exit(1)

def check_microphone_permission():
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
        return True
    except OSError as e:
        if "Could not open audio device" in str(e):
            messagebox.showerror("Microphone Error", "Could not access the microphone. Please check your microphone permissions and try again.")
        else:
            messagebox.showerror("Error", f"An error occurred while accessing the microphone: {str(e)}")
        return False
    except Exception as e:
        messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")
        return False

def wake_word_callback():
    print("Wake word detected!")
    update_status("Listening...")
    text_to_speech("I'm listening.")

def wake_word_detection():
    global porcupine, pa, audio_stream, running

    try:
        porcupine = pvporcupine.create(access_key="21yOYguX+Tglxu6+6hvGaL3lqmJDdiqRGVpQ/tP/+2bpON8hz2e9eg==",keywords=["jarvis"])
        pa = pyaudio.PyAudio()
        audio_stream = pa.open(
            rate=porcupine.sample_rate,
            channels=1,
            format=pyaudio.paInt16,
            input=True,
            frames_per_buffer=porcupine.frame_length
        )

        while running:
            pcm = audio_stream.read(porcupine.frame_length)
            pcm = struct.unpack_from("h" * porcupine.frame_length, pcm)

            keyword_index = porcupine.process(pcm)
            if keyword_index >= 0:
                wake_word_callback()
                process_voice_command()

    except Exception as e:
        print(f"Error in wake word detection: {str(e)}")
        messagebox.showerror("Error", f"Wake word detection error: {str(e)}")
    finally:
        if porcupine is not None:
            porcupine.delete()
        if audio_stream is not None:
            audio_stream.close()
        if pa is not None:
            pa.terminate()

def speech_to_text():
    recognizer = sr.Recognizer()
    try:
        with sr.Microphone() as source:
            print("Listening for command...")
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
        
        text = recognizer.recognize_google(audio)
        print(f"You said: {text}")
        return text
    except sr.UnknownValueError:
        print("Sorry, I couldn't understand that.")
        text_to_speech("I'm sorry, I couldn't understand that. Could you please repeat?")
    except sr.RequestError:
        print("Sorry, there was an error with the speech recognition service.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    return None

def get_openai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Provide concise responses."},
                *[{"role": "user" if i % 2 == 0 else "assistant", "content": msg} for i, msg in enumerate(conversation_history[-4:])],
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return None

def text_to_speech(text):
    try:
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Error in text-to-speech conversion: {str(e)}")

def write_at_mouse_location(text):
    try:
        current_x, current_y = pyautogui.position()
        pyautogui.click(current_x, current_y)
        pyautogui.write(text)
    except Exception as e:
        print(f"Error writing at mouse location: {str(e)}")

def process_command(input_text, is_voice=False):
    global running
    update_status("Processing...")
    text_to_speech("Processing your request.")

    if input_text.lower() in ["exit", "stop", "quit", "goodbye"]:
        running = False
        farewell = "Goodbye! The assistant is shutting down."
        display_message("Assistant", farewell)
        text_to_speech(farewell)
        print("Shutting down the assistant...")
        root.after(2000, root.quit) 
        return

    if input_text.lower().startswith("write at mouse:"):
        text_to_write = input_text[15:].strip()
        write_at_mouse_location(text_to_write)
        display_message("Assistant", "Text written at mouse location.")
        text_to_speech("Text has been written at the mouse location.")
        return

    conversation_history.append(input_text)
    ai_response = get_openai_response(input_text)
    if not ai_response:
        update_status("Waiting for input...")
        text_to_speech("I'm sorry, I couldn't process that request. Please try again.")
        return

    conversation_history.append(ai_response)

    print(f"AI response: {ai_response}")

    display_message("Assistant", ai_response)
    if is_voice:
        text_to_speech(ai_response)
    else:
        text_to_speech("I've provided a response. Let me know if you need anything else.")
    update_status("Waiting for input...")

def process_voice_command():
    input_text = speech_to_text()
    if input_text:
        display_message("You", input_text)
        process_command(input_text, is_voice=True)

def process_text_command():
    input_text = input_entry.get()
    input_entry.delete(0, tk.END)
    if input_text:
        display_message("You", input_text)
        threading.Thread(target=process_command, args=(input_text,)).start()

def startup_greeting():
    greeting = "Jarvis is now running!"
    print(greeting)
    display_message("System", greeting)
    text_to_speech(greeting)

def create_gui():
    global root, status_label, chat_display, input_entry, send_button

    root = ThemedTk(theme="arc")
    root.title("AI Assistant")
    root.geometry("800x600")
    root.attributes('-topmost', True)
    root.resizable(True, True)

    style = ttk.Style()
    style.configure("TButton", padding=6, relief="flat", background="#4CAF50")

    main_frame = ttk.Frame(root, padding="10")
    main_frame.pack(expand=True, fill=tk.BOTH)

    # Chat display
    chat_frame = ttk.Frame(main_frame)
    chat_frame.pack(expand=True, fill=tk.BOTH, pady=(0, 10))

    chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, width=80, height=20)
    chat_display.pack(expand=True, fill=tk.BOTH)
    chat_display.config(state=tk.DISABLED)

    # Input area
    input_frame = ttk.Frame(main_frame)
    input_frame.pack(fill=tk.X, pady=(0, 10))

    input_entry = ttk.Entry(input_frame, font=("Arial", 12))
    input_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)

    send_button = ttk.Button(input_frame, text="Send", command=process_text_command, style="TButton")
    send_button.pack(side=tk.RIGHT, padx=(5, 0))

    # Options frame
    options_frame = ttk.Frame(main_frame)
    options_frame.pack(fill=tk.X)

    upload_button = ttk.Button(options_frame, text="Upload Photo", command=upload_photo)
    upload_button.pack(side=tk.LEFT, padx=(0, 5))

    screenshot_button = ttk.Button(options_frame, text="Scan Screenshot", command=scan_screenshot)
    screenshot_button.pack(side=tk.LEFT, padx=(0, 5))

    copy_button = ttk.Button(options_frame, text="Copy", command=copy_text)
    copy_button.pack(side=tk.LEFT, padx=(0, 5))

    paste_button = ttk.Button(options_frame, text="Paste", command=paste_text)
    paste_button.pack(side=tk.LEFT)

    status_label = ttk.Label(main_frame, text="Ready", anchor=tk.W)
    status_label.pack(fill=tk.X, pady=(10, 0))

def update_status(message):
    status_label.config(text=message)
    root.update_idletasks()

def display_message(sender, message):
    chat_display.config(state=tk.NORMAL)
    chat_display.insert(tk.END, f"{sender}: {message}\n\n")
    chat_display.config(state=tk.DISABLED)
    chat_display.see(tk.END)

def stop_assistant():
    global running
    running = False
    farewell = "Goodbye! The assistant is shutting down."
    display_message("System", farewell)
    text_to_speech(farewell)
    print("Shutting down the assistant...")
    root.after(2000, root.quit)

def run_assistant():
    if check_microphone_permission():
        startup_greeting()
        wake_word_detection()
    else:
        messagebox.showerror("Microphone Error", "Unable to access the microphone. The assistant will now exit.")
        root.quit()

def run_background():
    assistant_thread = threading.Thread(target=run_assistant)
    assistant_thread.start()
    root.mainloop()
    assistant_thread.join()
    print("Assistant has been stopped.")

def upload_photo():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png *.jpg *.jpeg *.gif *.bmp")])
    if file_path:
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            display_message("System", f"Extracted text from image:\n{text}")
        except Exception as e:
            display_message("System", f"Error processing image: {str(e)}")

def scan_screenshot():
    try:
        screenshot = pyautogui.screenshot()
        text = pytesseract.image_to_string(screenshot)
        display_message("System", f"Extracted text from screenshot:\n{text}")
    except Exception as e:
        display_message("System", f"Error processing screenshot: {str(e)}")

def copy_text():
    try:
        selected_text = chat_display.selection_get()
        pyperclip.copy(selected_text)
        update_status("Text copied to clipboard")
    except tk.TclError:
        update_status("No text selected")

def paste_text():
    pasted_text = pyperclip.paste()
    input_entry.insert(tk.END, pasted_text)
    update_status("Text pasted from clipboard")

if __name__ == "__main__":
    check_dependencies()
    create_gui()
    run_background()