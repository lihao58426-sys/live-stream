"""
TTS 语音合成模块
================
职责：把话术文字 → edge-tts → mp3 音频文件。

为什么单独拆出来？
  - TTS 引擎可能换（edge-tts → 其他）
  - 主循环不需要知道"怎么把字变成声音"，只需要拿到音频文件路径
"""

import asyncio

import edge_tts


async def _tts(text: str, voice: str, output_file: str) -> None:
    """异步：调用 edge-tts 生成语音"""
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output_file)


def generate_audio(text: str, voice: str, output_file: str) -> None:
    """同步包装：把文字转成 mp3 语音文件

    这是给 producer 线程调用的——线程里不能直接用 asyncio，
    所以包一层 asyncio.run()。

    Args:
        text: 要朗读的文字
        voice: edge-tts 音色名（如 zh-CN-XiaoxiaoNeural）
        output_file: 输出 mp3 文件路径
    """
    asyncio.run(_tts(text, voice, output_file))
