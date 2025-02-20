# -*- coding: utf-8 -*-

# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from websockets.legacy.client import WebSocketClientProtocol
from websockets_proxy import Proxy, proxy_connect
import asyncio
import base64
import json
import os
import sys
import pyaudio
from rich.console import Console
from rich.markdown import Markdown
from websockets.asyncio.client import connect
from websockets.asyncio.connection import Connection
import numpy as np
import dotenv

dotenv.load_dotenv()

# Basic configuration
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 16000
CHUNK_SIZE = 512

host = "generativelanguage.googleapis.com"
model = "gemini-2.0-flash-exp"
api_key = os.environ["GOOGLE_API_KEY"]
uri = f"wss://{host}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={api_key}"

# Audio settings
pya = pyaudio.PyAudio()

# Themes and scenarios definition
THEMES = {
    "business": ["job interview", "business meeting", "presentation", "networking"],
    "travel": ["airport", "hotel", "restaurant", "sightseeing"],
    "daily life": ["shopping", "weather", "hobbies", "family"],
    "social": ["meeting friends", "party", "social media", "dating"],
}


class AudioLoop:
    def __init__(self):
        self.ws: WebSocketClientProtocol | Connection
        self.audio_out_queue = asyncio.Queue()
        self.running_step = 0
        self.paused = False
        self.current_theme = None
        self.current_scenario = None
        self.console = Console()

    def calculate_pronunciation_score(self, audio_data):
        """Calculate pronunciation score"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)

            # Calculate audio features
            energy = np.mean(np.abs(audio_array))
            zero_crossings = np.sum(np.abs(np.diff(np.signbit(audio_array))))

            # Normalize and calculate score
            energy_score = min(100, energy / 1000)
            rhythm_score = min(100, zero_crossings / 100)

            # Final score
            final_score = int(0.6 * energy_score + 0.4 * rhythm_score)
            return min(100, max(0, final_score))
        except Exception as e:
            self.console.print(f"Error in scoring: {e}", style="red")
            return 70  # Return default score if error

    async def startup(self):
        """Initialize conversation"""
        # Set initial configuration
        setup_msg = {
            "setup": {
                "model": f"models/{model}",
                "generation_config": {
                    "response_modalities": ["TEXT"],
                },
            }
        }
        await self.ws.send(json.dumps(setup_msg))
        await self.ws.recv()

        # Send initial prompt
        initial_msg = {
            "client_content": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": """You are a professional English-speaking instructor. Please respond in both English and Vietnamese, with English first and Vietnamese following, separated by ---.  

Your Responsibilities:
1. Correct users' grammar and pronunciation.  
2. Provide pronunciation scores and detailed feedback.  
3. Recognize and respond to user control commands:  
   - Pause when the user says, "Can I have a break?"
   - Resume when the user says, "OK, let's continue."
4. Offer practice sentences based on selected themes (business, travel, daily life, social).  

Interaction Flow:
- First, ask the user which theme they want to practice.  
- After each user response:  
  1. Identify what the user said in English.  
  2. Assign a pronunciation score (0-100).  
  3. Highlight pronunciation and grammar issues (with English-Vietnamese comparisons).  
  4. Provide improvement suggestions (with English-Vietnamese comparisons).  
  5. Present the next practice sentence relevant to the scenario (with English-Vietnamese comparisons).  

Response Format:  
```
[English response]  
---  
[Vietnamese response]  
```  

If you understand, reply "OK" in both English and Vietnamese."""
                            }
                        ],
                    }
                ],
                "turn_complete": True,
            }
        }
        await self.ws.send(json.dumps(initial_msg))

        # Wait for AI to reply OK
        current_response = []
        async for raw_response in self.ws:
            response = json.loads(raw_response)
            try:
                if "serverContent" in response:
                    parts = (
                        response["serverContent"].get("modelTurn", {}).get("parts", [])
                    )
                    for part in parts:
                        if "text" in part:
                            current_response.append(part["text"])
            except Exception:
                pass

            try:
                turn_complete = response["serverContent"]["turnComplete"]
                if turn_complete:
                    if "".join(current_response).startswith("OK"):
                        self.console.print("Initialization completed ✅", style="green")
                        return
            except KeyError:
                self.console.print("Initialization failed ❌", style="red")

    async def listen_audio(self):
        """Listen for audio input"""
        mic_info = pya.get_default_input_device_info()
        stream = pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        self.console.print("🎤 Please speak English", style="yellow")

        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            data = await asyncio.to_thread(stream.read, CHUNK_SIZE)
            if self.running_step > 1:
                continue

            # Volume detection
            audio_data = []
            for i in range(0, len(data), 2):
                sample = int.from_bytes(
                    data[i : i + 2], byteorder="little", signed=True
                )
                audio_data.append(abs(sample))
            volume = sum(audio_data) / len(audio_data)

            if volume > 200:
                if self.running_step == 0:
                    self.console.print("🎤 :", style="yellow", end="")
                    self.running_step += 1
                self.console.print("*", style="green", end="")
            await self.audio_out_queue.put(data)

    async def send_audio(self):
        """Send audio data"""
        while True:
            if self.paused:
                await asyncio.sleep(0.1)
                continue

            chunk = await self.audio_out_queue.get()
            msg = {
                "realtime_input": {
                    "media_chunks": [
                        {
                            "data": base64.b64encode(chunk).decode(),
                            "mime_type": "audio/pcm",
                        }
                    ]
                }
            }
            await self.ws.send(json.dumps(msg))

    async def play_audio(self, audio_data):
        """Play audio data received from Gemini"""
        stream = pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE,
        )

        try:
            decoded_audio = base64.b64decode(audio_data)
            stream.write(decoded_audio)
        finally:
            stream.stop_stream()
            stream.close()

    async def receive_audio(self):
        """Receive and process responses"""
        current_response = []

        async for raw_response in self.ws:
            if self.running_step == 1:
                self.console.print("\n♻️ Processing: ", end="")
                self.running_step += 2

            response = json.loads(raw_response)
            try:
                if "serverContent" in response:
                    parts = (
                        response["serverContent"].get("modelTurn", {}).get("parts", [])
                    )
                    for part in parts:
                        if "text" in part:
                            current_response.append(part["text"])
                            self.console.print("-", style="blue", end="")
            except Exception:
                pass

            try:
                turn_complete = response["serverContent"]["turnComplete"]
                if turn_complete and current_response:
                    text = "".join(current_response)

                    # Handle control commands
                    if "can i have a break" in text.lower():
                        self.paused = True
                        self.console.print(
                            "\n⏸️ Session paused. Say 'OK let's continue' to resume",
                            style="yellow",
                        )
                    elif "ok let's continue" in text.lower() and self.paused:
                        self.paused = False
                        self.console.print("\n▶️ Session resumed", style="green")

                    # Display response
                    self.console.print(
                        "\n🤖 =============================================",
                        style="yellow",
                    )
                    self.console.print(Markdown(text))

                    current_response = []
                    self.running_step = 0 if not self.paused else 2
            except KeyError:
                pass

    async def run(self):
        """Main run function"""
        proxy = (
            Proxy.from_url(os.environ["HTTP_PROXY"])
            if os.environ.get("HTTP_PROXY")
            else None
        )
        if proxy:
            self.console.print("Using proxy", style="yellow")
        else:
            self.console.print("No proxy used", style="yellow")

        async with proxy_connect(uri, proxy=proxy) if proxy else connect(uri) as ws:
            self.ws = ws
            self.console.print(
                "Gemini English Speaking Assistant", style="green", highlight=True
            )
            self.console.print("Make by twitter: @BoxMrChen", style="blue")
            self.console.print(
                "============================================", style="yellow"
            )

            await self.startup()

            async with asyncio.TaskGroup() as tg:
                tg.create_task(self.listen_audio())
                tg.create_task(self.send_audio())
                tg.create_task(self.receive_audio())

                def check_error(task):
                    if task.cancelled():
                        return
                    if task.exception():
                        print(f"Error: {task.exception()}")
                        sys.exit(1)

                for task in tg._tasks:
                    task.add_done_callback(check_error)


if __name__ == "__main__":
    main = AudioLoop()
    asyncio.run(main.run())
