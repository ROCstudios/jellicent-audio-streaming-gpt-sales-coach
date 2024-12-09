#! python3.7

import argparse
import os
import numpy as np
import speech_recognition as sr
import whisper
import torch
from openai import OpenAI
from threading import Thread
from datetime import datetime, timedelta
from queue import Queue
from time import sleep
from sys import platform
import sys
import time
import dotenv

dotenv.load_dotenv()


os.environ['PYTHONWARNINGS']='ignore:Forking'

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

gpt_queue = Queue()

def stream_text(text, delay=0.05):
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()  # Force the buffer to write immediately
        time.sleep(delay)
    sys.stdout.write('\n')

def process_gpt_queue():
    while True:
        try:
            if not gpt_queue.empty():
                line = gpt_queue.get()
                stream = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": """
                            You are an expert sales coaching assistant specialized in improving the effectiveness of sales calls. Your primary role is to evaluate a single line of dialogue from a sales call transcript and provide actionable recommendations for the salesperson to improve their communication, persuasion, and rapport-building skills.

                            Your suggestions should focus on:

                            Improving the quality of the interaction.
                            Addressing objections or concerns raised by the customer.
                            Enhancing the salesperson’s ability to close the deal.
                            Always ensure your feedback is:

                            Constructive and actionable.
                            Centered on the salesperson's dialogue (not the customer’s).
                            Specific to the sales context.
                            When generating recommendations:

                            Observation: Summarize the salesperson's dialogue and key elements related to tone, phrasing, or content.
                            Analysis: Highlight opportunities for improvement in persuasion, tone, or addressing the customer's needs.
                            Recommendation: Provide actionable steps the salesperson can take to improve their approach in similar situations.
                            Maintain a professional tone while offering clear, concise, and practical feedback.
                        """},
                        {"role": "user", "content": f"""
                            Here is a line from a sales call transcript. Evaluate it and suggest actionable improvements for the salesperson in 12 words or less. 
                            For example "Use more questions to engage the customer" or "Use more questions to engage the customer" or "Go deeper into the customer's needs".

                            Constraints:
                            - The advice you give should always be something they can act on in the future.
                            - Do not include any other text in your response.
                            - Keep the response to a single line. Concise and to the point.
                            - Do not incluse any labels headers or any formatting.
                            - Use simple language and avoid the word "clarify", "salesperson", or "customer"
                         
                            Now, here is the line from the sales call, remember, in your response you must reference something specific from the line:

                         
                            {line}
                        """}
                    ],
                    stream=True,
                )
                for chunk in stream:
                    if chunk.choices[0].delta.content is not None:
                        print(chunk.choices[0].delta.content, end="")

            else:
                sleep(0.25)
        except Exception as e:
            print(f"Error in GPT processing: {e}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="medium", help="Model to use",
                        choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--non_english", action='store_true',
                        help="Don't use the english model.")
    parser.add_argument("--energy_threshold", default=1000,
                        help="Energy level for mic to detect.", type=int)
    parser.add_argument("--record_timeout", default=2,
                        help="How real time the recording is in seconds.", type=float)
    parser.add_argument("--phrase_timeout", default=2,

                        help="How much empty space between recordings before we "
                             "consider it a new line in the transcription.", type=float)
    if 'linux' in platform:
        parser.add_argument("--default_microphone", default='pulse',
                            help="Default microphone name for SpeechRecognition. "
                                 "Run this with 'list' to view available Microphones.", type=str)
    args = parser.parse_args()

    # The last time a recording was retrieved from the queue.
    phrase_time = None
    # Thread safe Queue for passing data from the threaded recording callback.
    data_queue = Queue()
    # We use SpeechRecognizer to record our audio because it has a nice feature where it can detect when speech ends.
    recorder = sr.Recognizer()
    recorder.energy_threshold = args.energy_threshold
    # Definitely do this, dynamic energy compensation lowers the energy threshold dramatically to a point where the SpeechRecognizer never stops recording.
    recorder.dynamic_energy_threshold = False

    # Important for linux users.
    # Prevents permanent application hang and crash by using the wrong Microphone
    if 'linux' in platform:
        mic_name = args.default_microphone
        if not mic_name or mic_name == 'list':
            print("Available microphone devices are: ")
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                print(f"Microphone with name \"{name}\" found")
            return
        else:
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                if mic_name in name:
                    source = sr.Microphone(sample_rate=16000, device_index=index)
                    break
    else:
        source = sr.Microphone(sample_rate=16000)

    # Load / Download model
    model = args.model
    if args.model != "large" and not args.non_english:
        model = model + ".en"
    audio_model = whisper.load_model(model)

    record_timeout = args.record_timeout
    phrase_timeout = args.phrase_timeout

    transcription = ['']

    with source:
        recorder.adjust_for_ambient_noise(source)

    def record_callback(_, audio:sr.AudioData) -> None:
        """
        Threaded callback function to receive audio data when recordings finish.
        audio: An AudioData containing the recorded bytes.
        """
        # Grab the raw bytes and push it into the thread safe queue.
        data = audio.get_raw_data()
        data_queue.put(data)

    # Create a background thread that will pass us raw audio bytes.
    # We could do this manually but SpeechRecognizer provides a nice helper.
    recorder.listen_in_background(source, record_callback, phrase_time_limit=record_timeout)

    gpt_thread = Thread(target=process_gpt_queue, daemon=True)
    gpt_thread.start()
    # Cue the user that we're ready to go.
    print("Model loaded * You can start your call now\n")


    while True:
        try:
            now = datetime.utcnow()
            # Pull raw recorded audio from the queue.
            if not data_queue.empty():
                phrase_complete = False
                # If enough time has passed between recordings, consider the phrase complete.
                # Clear the current working audio buffer to start over with the new data.
                if phrase_time and now - phrase_time > timedelta(seconds=phrase_timeout):
                    phrase_complete = True
                # This is the last time we received new audio data from the queue.
                phrase_time = now
                
                # Combine audio data from queue
                audio_data = b''.join(data_queue.queue)
                data_queue.queue.clear()
                
                # Convert in-ram buffer to something the model can use directly without needing a temp file.
                # Convert data from 16 bit wide integers to floating point with a width of 32 bits.
                # Clamp the audio stream frequency to a PCM wavelength compatible default of 32768hz max.
                audio_np = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0

                # Read the transcription.
                result = audio_model.transcribe(audio_np, fp16=torch.cuda.is_available())
                text = result['text'].strip()

                # If we detected a pause between recordings, add a new item to our transcription.
                # Otherwise edit the existing one.
                if phrase_complete:
                    transcription.append(text)
                    gpt_queue.put(text)
                else:
                    transcription[-1] = text
                    gpt_queue.put(text)

                # Clear the console to reprint the updated transcription.
                os.system('cls' if os.name=='nt' else 'clear')
                for line in transcription:
                    continue
                # Flush stdout.
                print('', end='', flush=True)
            else:
                # Infinite loops are bad for processors, must sleep.
                sleep(0.25)
        except KeyboardInterrupt:
            break

    print("\n\nTranscription:")
    for line in transcription:
        print(line)


if __name__ == "__main__":
    main()
