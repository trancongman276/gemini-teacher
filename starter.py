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
import io
import os
import sys
import pyaudio
import threading
from rich import color, console
from websockets.asyncio.client import connect
from websockets.asyncio.connection import Connection
from rich.console import Console
from rich.markdown import Markdown
from elevenlabs.client import AsyncElevenLabs
from elevenlabs import ElevenLabs, play
import dotenv

dotenv.load_dotenv()

if sys.version_info < (3, 11, 0):
    raise Exception("Python 3.11 为最低要求.")

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 16000
CHUNK_SIZE = 512

host = "generativelanguage.googleapis.com"
model = "gemini-2.0-flash-exp"

api_key = os.environ["GOOGLE_API_KEY"]
uri = f"wss://{host}/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key={api_key}"

pya = pyaudio.PyAudio()

voice_client = None
voice_api_key = os.environ["ELEVENLABS_API_KEY"]
voice_model = "eleven_flash_v2_5"
voice_voice_id = "nPczCjzI2devNBz1zQrb"

global_console = Console()
if voice_api_key:
    global_console.print("启动语音模式", style="green")
    voice_client = ElevenLabs(api_key=voice_api_key)
else:
    global_console.print("语音模式关闭，找不到 ELEVENLABS_API_KEY", style="red")


class AudioLoop:
    def __init__(self):
        self.ws: WebSocketClientProtocol | Connection
        self.audio_out_queue = asyncio.Queue()
        self.running_step = 0

    async def startup(self):
        setup_msg = {
            "setup": {
                "model": f"models/{model}",
                "generation_config": {"response_modalities": ["TEXT"]},
            }
        }
        await self.ws.send(json.dumps(setup_msg))
        raw_response = await self.ws.recv()
        setup_response = json.loads(raw_response)

        # Send initial prompt after setup
        initial_msg = {
            "client_content": {
                "turns": [
                    {
                        "role": "user",
                        "parts": [
                            {
                                "text": "你是一名专业的英语口语指导老师，你需要帮助用户纠正语法发音，用户将会说一句英文，然后你会给出识别出来的英语是什么，并且告诉他发音中有什么问题，语法有什么错误，并且一步一步的纠正他的发音，当一次发音正确后，根据当前语句提出下一个场景的语句,然后一直循环这个过程，直到用户说OK，我要退出。你的回答永远要保持中文。如果明白了请回答OK两个字"
                            }
                        ],
                    }
                ],
                "turn_complete": True,
            }
        }
        await self.ws.send(json.dumps(initial_msg))
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
            except KeyError:
                pass
            else:
                if turn_complete:
                    if "".join(current_response).startswith("OK"):
                        print("初始化完成 ✅")
                        return

    async def listen_audio(self):
        mic_info = pya.get_default_input_device_info()
        stream = pya.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],  # type: ignore
            frames_per_buffer=CHUNK_SIZE,
        )

        console = global_console
        console.print("🎤 说一句英语吧！比如: What is blockchain?", style="yellow")

        while True:
            data = await asyncio.to_thread(stream.read, CHUNK_SIZE)
            # 计算音量 - 使用简单的字节平均值
            # 每个采样是2字节（16位），所以每次取2个字节转换为整数
            if self.running_step > 1:
                continue
            audio_data = []
            for i in range(0, len(data), 2):
                sample = int.from_bytes(
                    data[i : i + 2], byteorder="little", signed=True
                )
                audio_data.append(abs(sample))
            volume = sum(audio_data) / len(audio_data)
            if volume > 200:  # 阈值可以根据需要调整
                if self.running_step == 0:
                    console.print("🎤 :", style="yellow", end="")
                    self.running_step += 1
                console.print("*", style="green", end="")
            self.audio_out_queue.put_nowait(data)

    async def send_audio(self):
        while True:
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
            msg = json.dumps(msg)
            await self.ws.send(msg)

    async def receive_audio(self):
        console = global_console
        current_response = []
        async for raw_response in self.ws:
            if self.running_step == 1:
                console.print("\n♻️ 处理中：", end="")
                self.running_step += 1
            response = json.loads(raw_response)

            try:
                if "serverContent" in response:
                    parts = (
                        response["serverContent"].get("modelTurn", {}).get("parts", [])
                    )
                    for part in parts:
                        if "text" in part:
                            current_response.append(part["text"])
                            console.print("-", style="blue", end="")
            except Exception:
                pass

            try:
                turn_complete = response["serverContent"]["turnComplete"]
            except KeyError:
                pass
            else:
                if turn_complete:
                    if current_response:
                        text = "".join(current_response)
                        console.print(
                            "\n🤖 =============================================",
                            style="yellow",
                        )
                        console.print(Markdown(text))
                        current_response = []
                        if voice_client:

                            def play_audio():
                                voice_stream = voice_client.text_to_speech.convert_as_stream(  # type: ignore
                                    voice_id=voice_voice_id,
                                    text=text,
                                    model_id=voice_model,
                                    enable_logging=True,
                                )
                                play(voice_stream)

                            console.print("🙎 声音构建中........", style="yellow")
                            await asyncio.to_thread(play_audio)
                            console.print("🙎 播放完毕", style="green")
                        self.running_step = 0

    async def run(self):
        console = global_console
        proxy = (
            Proxy.from_url(os.environ["HTTP_PROXY"])
            if os.environ.get("HTTP_PROXY")
            else None
        )
        if proxy:
            console.print("使用代理", style="yellow")
        else:
            console.print("不使用代理", style="yellow")
        async with (
            proxy_connect(
                uri,
                proxy=proxy,
                # additional_headers={"Content-Type": "application/json"},
            )
            if proxy
            else connect(uri)
        ) as ws:
            self.ws = ws
            console.print("Gemini 英语口语助手", style="green", highlight=True)
            console.print("Make by twitter: @BoxMrChen", style="blue")
            console.print(
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

                    if task.exception() is None:
                        return

                    e = task.exception()
                    print(f"Error: {e}")
                    sys.exit(1)

                for task in tg._tasks:
                    task.add_done_callback(check_error)


if __name__ == "__main__":
    main = AudioLoop()
    asyncio.run(main.run())
