from qwen_tts import QwenTTSClient
import requests

def main():
    # Create client
    client = QwenTTSClient()

    # Get service config
    config = client.get_config()
    print("Service config:", config)

    # Convert text to speech
    text = "爱拼才会赢"
    print(f"Converting text to speech: {text}")

    audio_url = client.tts(text, timeout=30)
    print("Audio URL:", audio_url)

    if audio_url:
      # 下载音频文件
      response = requests.get(audio_url)
      with open("output.wav", "wb") as f:
          f.write(response.content)
      print("音频文件已保存为 output.wav")

if __name__ == "__main__":
    main()
