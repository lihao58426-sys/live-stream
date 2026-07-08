"""
抖音无人直播系统 — 主入口
=========================
职责：配置 + 后台预生成线程 + 主播放循环。

调用链（4 个模块的分工）：
  1. script_gen.py → 知识库 + DeepSeek 生成口播话术
  2. tts.py        → edge-tts 文字转语音
  3. player.py     → pygame 播放音频 + BGM
  4. main.py       → 你就是它 ← 生产者-消费者调度

架构：生产者-消费者模式
  - 后台线程（producer）：不断生成 (话术 + 音频) 放入队列
  - 主线程（consumer）：从队列取出 → 播放 → 随机停顿 → 取下一条
  - 好处：播放当前段时，下一段已经在后台生成好了，无缝衔接

用法：
  python main.py      启动直播（Ctrl+C 停止）
"""

import logging
import os
import random
import time
import threading
from queue import Queue

from script_gen import generate_script, KNOWLEDGE
from tts import generate_audio
from player import init_audio, play_audio, shutdown_audio

# ── 日志配置（入口文件负责，所有模块自动继承）──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("live_stream.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ======================== 配置区 ========================
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")

# 多音色轮换，避免一直一个声音被识别为 AI
VOICES = [
    "zh-CN-XiaoxiaoNeural",   # 晓晓 - 温柔女声
    "zh-CN-XiaoyiNeural",     # 晓伊 - 活泼女声
    "zh-CN-YunxiNeural",      # 云希 - 阳光男声
    "zh-CN-YunyangNeural",    # 云扬 - 专业男声
]

# 背景音乐（可选，空字符串表示不启用）
BGM_FILE = ""
BGM_VOLUME = 0.15
VOICE_VOLUME = 1.0

# 预生成缓冲区大小（提前准备几段，播放时下一段已就绪）
PREFETCH_SIZE = 2


# ======================== 后台预生成线程（生产者） ========================
def producer(queue: Queue, stop_event: threading.Event) -> None:
    """后台线程：不断生成话术 + 音频，放入队列

    这是生产者-消费者模式的生产端。
    主线程在播放时，这个线程已经悄悄生成了下一段。
    """
    idx = 0
    os.makedirs("temp", exist_ok=True)

    while not stop_event.is_set():
        if queue.full():
            time.sleep(0.3)
            continue

        try:
            # 步骤 1：AI 生成话术 ── script_gen.py
            script, topic = generate_script()

            # 步骤 2：TTS 生成语音 ── tts.py
            voice = random.choice(VOICES)
            audio_file = f"temp/audio_{idx % (PREFETCH_SIZE + 2)}.mp3"
            generate_audio(script, voice, audio_file)

            queue.put({
                "script": script,
                "topic": topic,
                "voice": voice,
                "file": audio_file,
            })
            idx += 1
        except Exception as e:
            logger.error(f"预生成失败: {e}")
            time.sleep(3)


# ======================== 主循环（消费者） ========================
def main() -> None:
    """无人直播主循环

    启动后台预生成 → 循环播放 → 随机停顿 → 直到 Ctrl+C
    """
    logger.info("抖音无人直播系统 V1（预生成无缝版）启动")
    logger.info("按 Ctrl+C 停止")

    if not DEEPSEEK_API_KEY:
        logger.warning("未检测到环境变量 DEEPSEEK_API_KEY，AI将无法调用，仅使用降级话术。")

    # 初始化音频（BGM）
    init_audio(bgm_file=BGM_FILE, bgm_volume=BGM_VOLUME)

    # 启动生产者-消费者
    queue: Queue = Queue(maxsize=PREFETCH_SIZE)
    stop_event = threading.Event()
    worker = threading.Thread(target=producer, args=(queue, stop_event), daemon=True)
    worker.start()

    logger.info("正在预生成首段内容，请稍候...")
    count = 1

    try:
        while True:
            # 从队列取一段（阻塞等待）
            item: dict = queue.get()

            logger.info(f"第 {count} 段 [话题: {item['topic']}] [音色: {item['voice']}]")
            logger.debug(f"话术: {item['script']}")
            logger.info(f"播放中... (后台已缓冲 {queue.qsize()} 段)")

            # 播放 ── player.py
            play_audio(item["file"], volume=VOICE_VOLUME)
            logger.info("播放完成")

            # 随机停顿，更像真人节奏
            pause = random.uniform(1.5, 3.5)
            logger.info(f"停顿 {pause:.1f} 秒...")
            time.sleep(pause)

            count += 1

    except KeyboardInterrupt:
        logger.info("正在关闭...")
        stop_event.set()
        shutdown_audio()
        logger.info("程序已退出")


if __name__ == "__main__":
    main()
