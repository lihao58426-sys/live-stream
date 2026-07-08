"""
音频播放模块
============
职责：用 pygame 播放人声 + 可选背景音乐循环。

为什么单独拆出来？
  - 播放引擎可能换（pygame → 其他）
  - 主循环不需要知道 pygame 怎么初始化、怎么加载 BGM
  - 改音量、换 BGM 文件只动这里
"""

import logging
import os

import pygame

logger = logging.getLogger(__name__)


def init_audio(bgm_file: str = "", bgm_volume: float = 0.15) -> None:
    """初始化音频系统 + 可选循环播放背景音乐

    Args:
        bgm_file: 背景音乐文件路径，空字符串表示不启用 BGM
        bgm_volume: BGM 音量 （0.0 ~ 1.0）
    """
    pygame.mixer.init()

    if bgm_file and os.path.exists(bgm_file):
        try:
            bgm_sound = pygame.mixer.Sound(bgm_file)
            bgm_sound.set_volume(bgm_volume)
            bgm_channel = pygame.mixer.Channel(0)
            bgm_channel.play(bgm_sound, loops=-1)
            logger.info("背景音乐已启动")
        except Exception as e:
            logger.warning(f"BGM加载失败: {e}")


def play_audio(file_path: str, volume: float = 1.0) -> None:
    """播放一段人声音频，阻塞直到播放完成

    Args:
        file_path: mp3/wav 文件路径
        volume: 音量（0.0 ~ 1.0）
    """
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.set_volume(volume)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()


def shutdown_audio() -> None:
    """关闭音频系统"""
    pygame.mixer.quit()
