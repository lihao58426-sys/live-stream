"""
数据模型 — dataclass 定义
=========================
职责：直播系统中用到的结构化数据，替代 tuple 和 dict。

原来传数据的方式：
  generate_script() 返回 (script_text, topic)  ← 两个元素的 tuple
  queue.put({"script": ..., "topic": ..., "voice": ..., "file": ...})  ← 裸 dict

现在：
  generate_script() 返回 LiveScript 对象
  queue.put(PlaylistItem(...))  ← 类型安全
"""

from dataclasses import dataclass


@dataclass
class LiveScript:
    """一段 AI 生成的直播话术"""
    text: str                      # 话术文本
    topic: str                     # 话题名（如 "套餐"、"位置"）


@dataclass
class AudioClip:
    """一个音频片段"""
    file_path: str                 # mp3/wav 文件路径
    voice_name: str = ""           # 使用的音色名


@dataclass
class PlaylistItem:
    """播放队列中的一条——话术 + 音频 + 元信息

    这是生产者-消费者队列的数据单元。
    producer 线程生成 LiveScript + AudioClip → 封装成 PlaylistItem → 放入 Queue
    consumer 主线程从 Queue 取出 → 播放
    """
    script: str                    # 话术全文
    topic: str                     # 话题名
    voice: str                     # 音色名
    file: str                      # 音频文件路径

    @classmethod
    def from_dict(cls, data: dict) -> "PlaylistItem":
        """从 producer 生成的 dict 构造（兼容过渡期）"""
        return cls(
            script=data.get("script", ""),
            topic=data.get("topic", ""),
            voice=data.get("voice", ""),
            file=data.get("file", ""),
        )
