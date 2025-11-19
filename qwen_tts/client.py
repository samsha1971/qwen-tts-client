import json
import requests
import time
from typing import Generator, Optional, Dict, Any, Tuple
import random
import string
import logging
from sseclient import SSEClient # 假设 sseclient 是一个外部库，保持不变

# --- 配置日志记录系统 (保持不变) ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 常量定义 ---
# 将默认值提取为类属性或常量，增加可维护性
DEFAULT_BASE_URL = "https://qwen-qwen3-tts-demo.hf.space"
SUPPORTS_VOICES = [
					"Cherry / 芊悦",
					"Ethan / 晨煦",
					"Jennifer / 詹妮弗",
					"Ryan / 甜茶",
					"Katerina / 卡捷琳娜",
					"Nofish / 不吃鱼",
					"Elias / 墨讲师",
					"Li / 南京-老李",
					"Marcus / 陕西-秦川",
					"Roy / 闽南-阿杰",
					"Peter / 天津-李彼得",
					"Eric / 四川-程川",
					"Rocky / 粤语-阿强",
					"Kiki / 粤语-阿清",
					"Sunny / 四川-晴儿",
					"Jada / 上海-阿珍",
					"Dylan / 北京-晓东"
				]
DEFAULT_VOICE = "Roy / 闽南-阿杰"

SUPPORTS_LANGUAGES = 	["Auto / 自动",
					"English / 英文",
					"Chinese / 中文",
					"German / 德语",
					"Italian / 意大利语",
					"Portuguese / 葡萄牙语",
					"Spanish / 西班牙语",
					"Japanese / 日语",
					"Korean / 韩语",
					"French / 法语",
					"Russian / 俄语"]
DEFAULT_LANGUAGE = "Auto / 自动"

DEFAULT_FN_INDEX = 1
DEFAULT_TRIGGER_ID = 7
DEFAULT_TIMEOUT_JOIN = 30
DEFAULT_TIMEOUT_TTS = 60 # 增加 TTS 过程的整体超时，避免长时间等待
DEFAULT_USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0")

class QwenTTSClient:
    """
    Qwen TTS 客户端类，用于与 Gradio/HuggingFace Space 上的 Qwen3 TTS 服务进行交互
    封装了队列加入 (_join_queue) 和 SSE 流式轮询 (_poll_data) 的逻辑。
    """

    def __init__(self, base_url: str = DEFAULT_BASE_URL):
        """
        初始化 QwenTTSClient 客户端

        Args:
            base_url (str): TTS 服务的基础 URL 地址
        """
        # 移除基础 URL 末尾的斜杠并保存
        self.base_url = base_url.rstrip('/')
        # 创建一个 requests 会话对象用于 HTTP 请求
        self.session = requests.Session()
        # 更新会话的请求头，设置用户代理信息和默认接受类型
        self.session.headers.update({
            "User-Agent": DEFAULT_USER_AGENT,
            # Gradio API 推荐设置
            "Accept": "*/*"
        })

    @staticmethod
    def _generate_session_hash(length: int = 9) -> str:
        """
        生成指定长度的随机会话哈希字符串
        """
        characters = string.ascii_lowercase + string.digits
        return ''.join(random.choices(characters, k=length))

    def _join_queue(self,
                    text: str,
                    voice: str = DEFAULT_VOICE,
                    mode: str = DEFAULT_LANGUAGE,
                    fn_index: int = DEFAULT_FN_INDEX,
                    trigger_id: int = DEFAULT_TRIGGER_ID) -> Dict[str, Any]:
        """
        通过向 /gradio_api/queue/join 发送 POST 请求加入 TTS 生成队列

        优化说明:
        1. 细化了异常捕获。
        2. 使用 `DEFAULT_TIMEOUT_JOIN` 常量。
        3. 明确返回结果中包含 `session_hash`。
        """
        session_hash = self._generate_session_hash()
        url = f"{self.base_url}/gradio_api/queue/join" # URL 中无需问号

        # 优化：明确定义请求载荷结构
        payload = {
            "data": [text, voice, mode],
            "event_data": None,
            "fn_index": fn_index,
            "trigger_id": trigger_id,
            "session_hash": session_hash
        }

        headers = {"Content-Type": "application/json"}

        logger.info(f"正在加入 TTS 队列，处理文本: {text[:20]}...")

        try:
            response = self.session.post(
                url,
                headers=headers,
                json=payload,
                # 连接超时 5s，读取超时使用常量
                timeout=(5, DEFAULT_TIMEOUT_JOIN)
            )
            response.raise_for_status() # 检查 HTTP 状态码
        except requests.exceptions.Timeout as e:
            logger.error(f"加入队列请求超时: {e}")
            raise requests.exceptions.Timeout("加入队列请求超时") from e
        except requests.exceptions.RequestException as e:
            logger.error(f"加入队列请求失败: {e}")
            raise requests.exceptions.RequestException(f"加入队列请求失败: {response.text}") from e

        result = response.json()
        result["session_hash"] = session_hash # 确保返回结果包含 session_hash

        logger.info(f"成功加入 TTS 队列，Hash: {session_hash}")
        return result

    def _poll_data(self,
                    session_hash: str,
                    timeout: int = DEFAULT_TIMEOUT_TTS) -> Generator[Dict[str, Any], None, None]:
        """
        通过连接到 /gradio_api/queue/data 并使用 SSE 流式传输轮询 TTS 结果

        优化说明:
        1. 移除 `Optional[int]`，明确 `timeout` 为 int 类型。
        2. 统一使用 `timeout` 参数控制读取超时。
        3. 使用 `yield from` 结构，简化 SSEClient 的循环。
        """
        url = f"{self.base_url}/gradio_api/queue/data?session_hash={session_hash}"
        headers = {"Accept": "text/event-stream"}

        logger.info(f"开始轮询数据，会话哈希: {session_hash}")

        try:
            # 使用 `with` 语句确保连接关闭
            with self.session.get(url, headers=headers, stream=True, timeout=(5, timeout)) as response:
                response.raise_for_status()

                client = SSEClient(response)
                # 使用 while True 结构来确保在生成器结束后关闭 client 是困难的
                # 因此保持原有的 try/finally 结构，但简化事件处理
                for event in client.events():
                    try:
                        # 尝试将事件数据解析为 JSON
                        parsed = json.loads(event.data)
                        yield parsed
                    except json.JSONDecodeError as e:
                        # 如果 JSON 解析失败，记录警告日志并产出原始数据
                        logger.warning(f"JSON 解析失败: {e}, 原始数据: {event.data[:50]}...")
                        yield {"raw": event.data, "error": str(e)}
                    except Exception as e:
                         # 其他异常
                         logger.error(f"处理 SSE 事件时发生未知错误: {e}")
                         yield {"raw": event.data, "error": str(e)}

        except requests.exceptions.RequestException as e:
            logger.error(f"轮询数据请求失败: {e}")
            raise requests.exceptions.RequestException(f"轮询数据请求失败") from e

    # get_config 方法保持不变，它很简单且功能清晰。
    def get_config(self) -> Dict[str, Any]:
        """
        通过 GET /config 获取服务配置信息
        """
        url = f"{self.base_url}/config"
        response = self.session.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    # 获取支持的语音列表
    def voices(self) -> Dict[str, Any]:
        return SUPPORTS_VOICES

    # 获取支持的语言列表
    def languages(self) -> Dict[str, Any]:
        return SUPPORTS_LANGUAGES

    def tts(self,
            text: str,
            voice: str = DEFAULT_VOICE,
            mode: str = DEFAULT_LANGUAGE,
            timeout: int = DEFAULT_TIMEOUT_TTS) -> Optional[str]:
        """
        高级方法，合成文本并直接返回音频文件 URL

        优化说明:
        1. 重用 `_poll_data` 方法的逻辑，避免代码重复（原代码中 tts 内部重复了轮询逻辑）。
        2. 增加了对 Gradio 队列状态的日志记录。
        3. 统一处理异常，只返回 URL 或 None。
        """
        start_time = time.time()

        try:
            # 1. 加入队列
            join_response = self._join_queue(text, voice, mode)
            session_hash = join_response.get("session_hash")

            if not session_hash:
                raise ValueError("从加入队列响应中获取会话哈希失败")

            # 2. 轮询结果
            for event in self._poll_data(session_hash, timeout):
                if time.time() - start_time > timeout:
                    logger.warning(f"TTS 合成超时 ({timeout}s)")
                    return None

                msg = event.get("msg")

                # 记录队列状态，方便调试
                if msg in ["send_hash", "queue_full", "estimation"]:
                    logger.info(f"队列状态: {msg} - {event.get('rank', '')}")
                elif msg == "process_completed":
                    # 检查是否完成且成功
                    if event.get("success"):
                        output_data = event.get("output", {}).get("data", [])
                        if output_data and len(output_data) > 0:
                            # 假设音频信息在第一个元素中
                            audio_info = output_data[0]
                            audio_url = audio_info.get("url")
                            if audio_url:
                                logger.info(f"TTS 合成成功，耗时: {time.time() - start_time:.2f}s")
                                return f"{audio_url}" # 补充完整 URL

                        logger.warning("成功消息中未找到有效的音频 URL。")
                        return None
                    else:
                        logger.error(f"TTS 进程执行失败: {event.get('output')}")
                        return None

        except requests.exceptions.RequestException as e:
            # 捕获所有 requests 相关的异常（超时、HTTP 错误等）
            logger.error(f"TTS 请求发生网络错误: {e}")
            return None
        except ValueError as e:
            # 捕获自定义的 ValueError（如获取 hash 失败）
            logger.error(f"TTS 逻辑错误: {e}")
            return None
        except KeyboardInterrupt:
            # 处理用户中断操作 (Ctrl+C)
            print("\n操作已被用户取消。")
            return None
        except Exception as e:
            # 捕获所有其他意外错误
            logger.error(f"文本转语音转换过程中发生未知错误: {e}", exc_info=True)
            return None

        # 正常退出循环（例如，轮询流结束）但未找到结果
        logger.warning("轮询流异常结束或未在事件中找到音频 URL")
        return None

# --- 示例使用 (保持不变，或用于测试) ---
if __name__ == '__main__':
    # 注意：运行此代码需要安装 requests 和 sseclient 库
    # pip install requests sseclient-py

    client = QwenTTSClient()
    text_to_synthesize = "你好，我是阿里云通义千问模型，我正在为您合成闽南语语音。"

    print(f"尝试获取配置信息...(非必要调用)")
    try:
        config = client.get_config()
        print("✅️ 配置获取成功。\n")
    except Exception as e:
        print(f"❌️ 配置获取失败: {e}\n")


    support_vocies = client.voices()
    print(f"✅️ 支持的语音列表:{support_vocies}\n")

    support_languages= client.languages()
    print(f"✅️ 支持的语音列表:{support_languages}\n")

    print("--- 开始 TTS 合成 ---")

    # 默认使用 "Roy / 闽南-阿杰" 语音
    audio_url = client.tts(text_to_synthesize, timeout=90) # 增加超时时间以应对队列等待

    if audio_url:
        print(f"✅ 语音合成成功，音频 URL: {audio_url}")
        try:
          # 发送GET请求获取音频数据
          start_time = time.time()
          response = requests.get(audio_url)
          response.raise_for_status()
          filename = "audio.wav"
          # 保存音频文件
          with open(filename, 'wb') as f:
              f.write(response.content)
          download_time = time.time() - start_time
          print(f"✅️ 音频已保存到: {filename}，耗时: {download_time:.2f}秒")

        except Exception as e:
            print(f"❌️保存音频失败: {e}")

    else:
        print("\n❌ 语音合成失败或未获取到 URL。")
