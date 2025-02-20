# Gemini Vietnamese-English Speaking Assistant

This is an English speaking practice assistant based on Google Gemini AI that can recognize English pronunciation in real-time and provide instant feedback and correction suggestions, specifically designed for Vietnamese speakers.

Original made by [Box](https://x.com/boxmrchen)

## Features

- 🎤 Real-time speech recognition
- 🤖 AI-powered pronunciation assessment with focus on Vietnamese accent patterns
- 📝 Grammar correction tailored for common Vietnamese-English mistakes
- 🔄 Scenario-based conversation practice with Vietnamese context
- 🎯 Targeted pronunciation guidance for Vietnamese speakers
- 💡 Intelligent scene switching

## System Requirements

- Python 3.11+ (required)
- Microphone device
- Internet connection

## Prerequisites

You need a Gemini API Key, which offers 4 million free requests per day, which is more than sufficient.

Generate one at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

## Installation

1. Clone the repository:
```bash
git clone https://github.com/nishuzumi/gemini-teacher.git
cd gemini-teacher
```

2. Create and activate virtual environment (recommended):
```bash
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# or
.venv\Scripts\activate  # Windows
```

3. Install dependencies:

Before installing Python dependencies, please install the following system dependencies:

- Windows: No additional installation needed
- macOS: `brew install portaudio`
- Ubuntu/Debian: `sudo apt-get install portaudio19-dev python3-pyaudio`

```bash
pip install -r requirements.txt
```

## Usage

1. Set up environment
Create a new `.env` file, copy the contents from `.env.example`, and modify accordingly.

If you need to set up a proxy, fill in `HTTP_PROXY`, e.g., `HTTP_PROXY=http://127.0.0.1:7890`

Fill in `GOOGLE_API_KEY` with your Google Gemini API Key

```bash
python starter.py
```

2. Speak English sentences as prompted
3. Wait for AI assistant's feedback
4. Improve pronunciation based on feedback

## Interaction Guide

- 🎤 : Recording
- ♻️ : Processing
- 🤖 : AI Feedback

Note: This assistant is specifically optimized for Vietnamese speakers learning English, with particular attention to common pronunciation challenges faced by Vietnamese learners.

## License

MIT

## Contributing

Issues and Pull Requests are welcome!
