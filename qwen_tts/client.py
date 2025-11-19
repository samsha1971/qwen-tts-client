import json
import requests
import time
from typing import Generator, Optional, Dict, Any
import random
import string
import logging
from sseclient import SSEClient

# 配置日志记录系统
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenTTSClient:
    """
    Qwen TTS 客户端类，用于与 HuggingFace Space 上的 Qwen3 TTS 服务进行交互
    官方云服务地址：https://help.aliyun.com/zh/model-studio/qwen-tts?spm=5176.28197632.console-base_help.dexternal.5e032e36yEWx8I
    """

    def __init__(self, base_url: str = "https://qwen-qwen3-tts-demo.hf.space"):
        """
        初始化 QwenTTSClient 客户端

        Args:
            base_url (str): TTS 服务的基础 URL 地址
        """
        # 移除基础 URL 末尾的斜杠并保存
        self.base_url = base_url.rstrip('/')
        # 创建一个 requests 会话对象用于 HTTP 请求
        self.session = requests.Session()
        # 更新会话的请求头，设置用户代理信息
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36 Edg/142.0.0.0"
        })

    @staticmethod
    def _generate_session_hash(length: int = 9) -> str:
        """
        生成指定长度的随机会话哈希字符串

        Args:
            length (int): 会话哈希字符串的长度，默认为 9 位

        Returns:
            str: 由小写字母和数字组成的随机会话哈希字符串
        """
        # 定义字符集，包含小写字母和数字
        characters = string.ascii_lowercase + string.digits
        # 从字符集中随机选择指定数量的字符并组合成字符串
        return ''.join(random.choices(characters, k=length))

    def _join_queue(self,
                   text: str,
                   voice: str = "Roy / 闽南-阿杰",
                   mode: str = "Auto / 自动",
                   fn_index: int = 1,
                   trigger_id: int = 7) -> Dict[str, Any]:
        """
        通过向 /gradio_api/queue/join 发送 POST 请求加入 TTS 生成队列

        Args:
            text (str): 需要合成语音的文本内容
            voice (str): 语音选项，默认为 "Roy / 闽南-阿杰"
            mode (str): 合成模式，默认为 "Auto / 自动"
            fn_index (int): 函数索引，默认为 1
            trigger_id (int): 触发器 ID，默认为 7

        Returns:
            dict: 来自 TTS 服务的 JSON 响应数据

        Raises:
            requests.RequestException: 当网络请求失败时抛出异常
        """
        # 总是生成一个新的会话哈希值
        session_hash = self._generate_session_hash()

        # 构建请求 URL
        url = f"{self.base_url}/gradio_api/queue/join?"
        # 构建请求载荷数据
        payload = {
            "data": [text, voice, mode],      # 包含文本、语音和模式的数据
            "event_data": None,               # 事件数据，此处为空
            "fn_index": fn_index,             # 函数索引
            "trigger_id": trigger_id,         # 触发器 ID
            "session_hash": session_hash      # 会话哈希值
        }
        # 设置请求头，指定内容类型为 JSON
        headers = {"Content-Type": "application/json"}

        # 记录日志，显示正在处理的文本前 20 个字符
        logger.info(f"正在加入 TTS 队列，处理文本: {text[:20]}...")
        # 发送 POST 请求到服务端
        response = self.session.post(url, headers=headers, json=payload, timeout=30)
        # 如果响应状态码表示错误，则抛出异常
        response.raise_for_status()

        # 解析响应的 JSON 数据
        result = response.json()
        # 确保响应结果中包含会话哈希值
        result["session_hash"] = session_hash
        # 记录成功加入队列的日志
        logger.info("成功加入 TTS 队列")
        # 返回解析后的结果
        return result

    def _poll_data(self,
                  session_hash: str,
                  timeout: Optional[int] = None) -> Generator[Dict[str, Any], None, None]:
        """
        通过连接到 /gradio_api/queue/data 并使用 SSE 流式传输轮询 TTS 结果

        Args:
            session_hash (str): 从 _join_queue() 方法获取的会话哈希值
            timeout (Optional[int]): 轮询超时时间（秒），如果为 None 则不设置超时

        Yields:
            dict: 解析后的 JSON 事件数据或解析失败时的原始数据

        Raises:
            requests.RequestException: 当网络请求失败时抛出异常
        """
        # 构建轮询数据的 URL，包含会话哈希参数
        url = f"{self.base_url}/gradio_api/queue/data?session_hash={session_hash}"
        # 设置请求头，表明接受 SSE 流式数据
        headers = {"Accept": "text/event-stream"}

        # 记录开始轮询数据的日志
        logger.info(f"开始轮询数据，会话哈希: {session_hash}")

        # 发起 GET 请求并启用流式传输
        with self.session.get(url, headers=headers, stream=True, timeout=(5, timeout)) as response:
            # 如果响应状态码表示错误，则抛出异常
            response.raise_for_status()

            # 使用 sseclient-py 库来处理 SSE 流
            client = SSEClient(response)
            try:
                # 遍历所有 SSE 事件
                for event in client.events():
                    try:
                        # 尝试将事件数据解析为 JSON
                        parsed = json.loads(event.data)
                        # 产出解析后的数据
                        yield parsed
                    except Exception as e:
                        # 如果 JSON 解析失败，记录警告日志并产出原始数据
                        logger.warning(f"JSON 解析失败: {e}")
                        yield {"raw": event.data}
            finally:
                # 确保关闭 SSE 客户端连接
                client.close()

    def get_config(self) -> Dict[str, Any]:
        """
        通过 GET /config 获取服务配置信息

        Returns:
            dict: 来自服务端的配置 JSON 数据

        Raises:
            requests.RequestException: 当网络请求失败时抛出异常
        """
        # 构建获取配置的 URL
        url = f"{self.base_url}/config"
        # 发送 GET 请求获取配置信息
        response = self.session.get(url, timeout=10)
        # 如果响应状态码表示错误，则抛出异常
        response.raise_for_status()
        # 返回解析后的配置 JSON 数据
        return response.json()

    def tts(self,
          text: str,
          voice: str = "Roy / 闽南-阿杰",
          mode: str = "Auto / 自动",
          timeout: int = 30) -> Optional[str]:
      """
      高级方法，合成文本并直接返回音频文件 URL

      Args:
          text (str): 要合成的文本
          voice (str): 声音选项，默认为 "Roy / 闽南-阿杰"
          mode (str): 合成模式，默认为 "Auto / 自动"
          timeout (int): 轮询超时时间（秒），默认为 30

      Returns:
          Optional[str]: 成功时返回音频文件 URL，否则返回 None
      """
      try:
          # 加入队列并获取会话哈希
          join_response = self._join_queue(text, voice, mode)
          session_hash = join_response.get("session_hash")

          # 检查是否成功获取会话哈希
          if not session_hash:
              raise ValueError("从加入队列响应中获取会话哈希失败")

          # 轮询结果直到获得音频 URL 或超时
          with self.session.get(
              f"{self.base_url}/gradio_api/queue/data?session_hash={session_hash}",
              headers={"Accept": "text/event-stream"},
              stream=True,
              timeout=(5, timeout)
          ) as response:
              # 如果响应状态码表示错误，则抛出异常
              response.raise_for_status()

              # 使用 sseclient-py 库来处理 SSE 流
              client = SSEClient(response)
              try:
                  # 遍历所有 SSE 事件
                  for event in client.events():
                      try:
                          # 尝试解析事件数据为 JSON
                          parsed_event = json.loads(event.data)
                          # 检查是否有 process_completed 消息，其中包含音频文件 URL
                          if parsed_event.get("msg") == "process_completed" and parsed_event.get("success"):
                              # 获取输出数据
                              output_data = parsed_event.get("output", {}).get("data", [])
                              # 检查输出数据是否存在且不为空
                              if output_data and len(output_data) > 0:
                                  # 获取音频信息
                                  audio_info = output_data[0]
                                  # 返回音频文件的 URL
                                  return audio_info.get("url")
                      except Exception as e:
                          # 如果单个事件解析失败，记录警告并继续处理下一个事件
                          logger.warning(f"JSON 解析失败: {e}")
                          continue

              finally:
                  # 确保关闭 SSE 客户端连接
                  client.close()

          # 如果没有找到音频 URL，记录警告日志
          logger.warning("在响应事件中未找到音频 URL")
          # 返回 None 表示未找到音频 URL
          return None

      except KeyboardInterrupt:
          # 处理用户中断操作 (Ctrl+C)
          print("\n操作已被用户取消。")
          # 返回 None 表示操作被取消
          return None
      except Exception as e:
          # 处理其他异常并记录错误日志
          logger.error(f"文本转语音转换过程中发生错误: {e}")
          # 返回 None 表示发生错误
          return None
