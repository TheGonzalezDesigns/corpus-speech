# Corpus Speech - Text-to-Speech Module

Speech synthesis and audio output capability for the Corpus AI companion system.

## Overview

This module provides text-to-speech synthesis and audio output capabilities for the Corpus system. It handles converting text input into natural-sounding speech and manages audio hardware on the Raspberry Pi.

## Features

- Text-to-speech synthesis
- Audio output management
- Voice selection and configuration
- Volume and speed control
- Integration with Corpus main system

## Hardware Requirements

- Raspberry Pi with audio output (3.5mm jack, HDMI, or USB audio)
- Speakers or headphones
- Optional: Audio HAT for improved sound quality

## Installation

```bash
# Install system dependencies
sudo apt update
sudo apt install espeak espeak-data libespeak-dev festival

# Install Python dependencies
pip install -r requirements.txt
```

## Usage

### Standalone
```python
from corpus_speech import TextToSpeech

tts = TextToSpeech()
tts.speak("Hello, I am your AI companion!")
```

### API Server
```bash
python app.py
```

## API

- `POST /speak` - Convert text to speech
- `GET /status` - Get module status
- `POST /config` - Update voice settings

## Configuration

See `config.yaml` for voice settings, audio device configuration, and integration parameters.

## Integration

This module communicates with the main Corpus system via [TBD - REST API/message queue/gRPC].