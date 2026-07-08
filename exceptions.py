"""
自定义异常类
===========
职责：无人直播系统各环节的失败类型。

为什么需要？
  - AI 话术生成失败 → 降级到知识库原文（直播不能停）
  - TTS 合成失败 → 跳过这一段，下一段继续（直播不能停）
  - 音频播放失败 → 记录日志，尝试下一段
"""


class AIGenerationError(Exception):
    """AI 话术生成失败

    场景：DeepSeek API 不可用、返回格式异常
    处理：降级到知识库原文拼接，直播继续
    """
    pass


class TTSError(Exception):
    """语音合成失败

    场景：edge-tts 网络异常、音色不支持
    处理：跳过当前段，producer 立即生成下一段
    """
    pass


class PlaybackError(Exception):
    """音频播放失败

    场景：pygame 混音器异常、音频文件损坏
    处理：跳过当前段，记录日志，继续播放下一段
    """
    pass
