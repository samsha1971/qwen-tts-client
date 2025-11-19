# Qwen TTS Client

A Python client library for interacting with the Qwen3 TTS service hosted on HuggingFace Spaces.

[Official Documentation](https://help.aliyun.com/zh/model-studio/qwen-tts?spm=5176.28197632.console-base_help.dexternal.5e032e36yEWx8I)

## Features

- 🎵 High-quality Chinese speech synthesis
- 🔧 Simple and easy-to-use API design
- ⚡ Support for streaming result processing
- 🌐 HTTP-based protocol with customizable service address
- 📦 Lightweight implementation with few dependencies

## Installation

```bash
pip install qwen-tts-client
```

## Quick Start

### Basic Usage

The simplest text-to-speech conversion that directly returns the audio file URL:

```python
from qwen_tts.client import QwenTTSClient

# Create client instance
client = QwenTTSClient()

# Text to speech
audio_url = client.tts("爱拼才会赢")
if audio_url:
    print(f"Audio file URL: {audio_url}")

    # Download and save audio file
    import requests
    response = requests.get(audio_url)
    with open("tts_output.wav", "wb") as f:
        f.write(response.content)
    print("Audio saved as tts_output.wav")
```

### Supported Voices and Languages

```python
from qwen_tts.client import QwenTTSClient

client = QwenTTSClient()

# Get supported voices
voices = client.voices()
print("Supported voices:", voices)

# Get supported languages
languages = client.languages()
print("Supported languages:", languages)

# Use specific voice and language
audio_url = client.tts("你好，世界", voice="Cherry / 芊悦", mode="Chinese / 中文")
```

### Advanced Usage

Stream processing of TTS events to get complete process information:

```python
from qwen_tts.client import QwenTTSClient
import json

client = QwenTTSClient()

# Join queue
join_result = client._join_queue("欢迎使用 Qwen TTS 服务")
session_hash = join_result["session_hash"]

# Stream processing of TTS events
for event in client._poll_data(session_hash):
    print(f"Event: {json.dumps(event, ensure_ascii=False)}")
```

### Custom Configuration

```python
from qwen_tts.client import QwenTTSClient

# Using custom service address
client = QwenTTSClient(base_url="https://your-custom-tts-service.com")

# Get service configuration information
config = client.get_config()
print(f"Service configuration: {config}")
```

## API Reference

### QwenTTSClient Class

#### Constructor

```python
QwenTTSClient(base_url="https://qwen-qwen3-tts-demo.hf.space")
```

Create a QwenTTSClient instance.

**Parameters:**
- [base_url](file://c:\Projects\qwen-tts-client\qwen_tts\client.py#L0-L0) (str): The base URL of the TTS service, defaults to the official demo service address.

#### Public Methods

##### `tts(text, voice="Roy / 闽南-阿杰", mode="Auto / 自动", timeout=60)`

Convert text to speech and return the audio file URL.

**Parameters:**
- `text` (str): The text to synthesize
- `voice` (str): Voice option, defaults to "Roy / 闽南-阿杰"
- `mode` (str): Synthesis mode, defaults to "Auto / 自动"
- `timeout` (int): Polling timeout (seconds), defaults to 60

**Returns:**
- `Optional[str]`: Audio file URL, or None if failed

##### [get_config()](file://c:\Projects\qwen-tts-client\qwen_tts\client.py#L183-L190)

Get service configuration information.

**Returns:**
- `dict`: JSON data of service configuration

##### `voices()`

Get list of supported voices.

**Returns:**
- `list`: List of supported voice options

##### `languages()`

Get list of supported languages.

**Returns:**
- `list`: List of supported language options

#### Private Methods

The following methods are for internal use and are not recommended for direct calling in production environments:

##### `_join_queue(text, voice="Roy / 闽南-阿杰", mode="Auto / 自动", fn_index=1, trigger_id=7)`

Join the TTS generation queue.

##### [_poll_data(session_hash, timeout=60)](file://c:\Projects\qwen-tts-client\qwen_tts\client.py#L140-L179)

Poll TTS results using Server-Sent Events (SSE).

##### [_generate_session_hash(length=9)](file://c:\Projects\qwen-tts-client\qwen_tts\client.py#L73-L78)

Generate a random session hash string of specified length.

## Development Guide

### Environment Requirements

- Python >= 3.7
- pip package manager

### Local Development

```bash
# Clone project
git clone https://github.com/xxx/qwen_tts.git
cd qwen_tts

# Install dependencies
pip install -r requirements.txt

# Install package (development mode)
pip install -e .
```

### Build and Release

```bash
python setup.py sdist bdist_wheel
```

## Dependencies

- `requests`: HTTP library
- `sseclient`: Server-Sent Events client

Install dependencies:
```bash
pip install requests sseclient-py
```

## License

MIT

## Support and Feedback

For issues or suggestions, please submit [GitHub Issues](https://github.com/samsha1971/qwen-tts-client/issues).
