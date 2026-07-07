"""
抖音无人直播 V1 - 改进版
功能：循环生成话术 → TTS → 播放（预生成 + 无缝衔接 + 多音色）
"""

import asyncio
import os
import random
import time
import threading
from queue import Queue
from openai import OpenAI
import edge_tts
import pygame

# ==================== 配置区 ====================
# 优先从环境变量读取，避免明文泄露。设置方法：
#   Windows: set DEEPSEEK_API_KEY=你的key
#   Mac/Linux: export DEEPSEEK_API_KEY=你的key
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 多音色轮换，避免一直一个声音被识别为AI
VOICES = [
    "zh-CN-XiaoxiaoNeural",   # 晓晓 - 温柔女声
    "zh-CN-XiaoyiNeural",     # 晓伊 - 活泼女声
    "zh-CN-YunxiNeural",      # 云希 - 阳光男声
    "zh-CN-YunyangNeural",    # 云扬 - 专业男声
]

# 背景音乐文件（可选，没有就留空字符串）
BGM_FILE = ""   # 例如 "bgm/background.mp3"
BGM_VOLUME = 0.15
VOICE_VOLUME = 1.0

# 预生成缓冲区大小（提前准备几段）
PREFETCH_SIZE = 2

# ==================== 知识库 ====================
KNOWLEDGE = {
    "店铺": "我们的卡丁车俱乐部位于咸阳西站地铁C口，场地面积超过400平米，作为室内儿童卡丁车场馆我们做到更宽敞的赛道，更亲民的价格，更贴心的服务",
    "套餐": "我们提供多种套餐选择：体验套餐38元12圈，首次开车的小车手有3圈，5圈的体验价格，可以直接小黄车购买",
    "安全": "所有车辆都经过严格检测，配备专业安全装备，现场有专业教练指导，适合3岁以上儿童和成人。",
    "儿童成长价值": "卡丁车可以锻炼孩子的反应能力、专注力和身体协调性，是很好的亲子活动。",
    "位置": "我们就在咸阳西站地铁口，地铁直达，停车方便。",
    "营业时间": "每天上午10点到晚上9点，全年无休，随时欢迎来体验。",
    "购买方式": "可以直接到店购买，也可以在抖音团购下单，还有更多优惠哦。"
}

# 话题权重：转化相关话题出现频率更高
TOPIC_WEIGHTS = {
    "店铺": 1.0,
    "套餐": 2.0,          # 重点推
    "安全": 1.2,
    "儿童成长价值": 1.0,
    "位置": 1.5,          # 常被问
    "营业时间": 1.0,
    "购买方式": 2.0,      # 重点推
}

TOPICS = list(KNOWLEDGE.keys())

# ==================== 话题选择 ====================
recent_topics = []  # 最近用过的，避免短期重复
MAX_RECENT = 3

def pick_topic():
    """加权随机选择话题，避免短期重复"""
    candidates = [t for t in TOPICS if t not in recent_topics]
    if not candidates:
        candidates = TOPICS
    weights = [TOPIC_WEIGHTS.get(t, 1.0) for t in candidates]
    topic = random.choices(candidates, weights=weights, k=1)[0]

    recent_topics.append(topic)
    if len(recent_topics) > MAX_RECENT:
        recent_topics.pop(0)
    return topic

# ==================== AI生成话术 ====================
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

def generate_script():
    """调用DeepSeek生成直播话术，失败时降级使用知识库"""
    topic = pick_topic()
    knowledge = KNOWLEDGE[topic]

    prompt = f"""你是一个卡丁车俱乐部的主播，正在直播间里自然地跟观众介绍店里的情况。

话题：{topic}
相关信息：{knowledge}

请生成一段20-30秒的直播话术，要求：
1. 语气以"介绍、分享"为主，就像平时面对面跟朋友聊天、介绍东西一样，自然、亲切、可信。
2. 不用叫卖式词语，比如"家人们""冲呀""赶紧下单""错过就没了""321上链接"这类，不要有很强的推销腔，而是把信息讲清楚、讲舒服。
3. 整段话里必须使用一到两处倒装句来增加口语感，比如"我们这边给小朋友准备的呀，是这样一套体验套餐""特别适合带娃来放电的，就是我们这个场地"。注意：倒装句整段出现一两次就够了，不要句句倒装，否则会很别扭。
4. 口语化，可以适当加一点语气词，但不要太夸张。
5. 长度控制在200到300字左右，内容完整。
6. 不要使用特殊符号，只输出话术内容本身。
7. 严禁提及任何具体价格、数字、折扣金额（如"便宜几十块""XX元""打X折"等），只能引导观众"到店咨询"或"私信了解优惠"，绝对不要说出任何价格数字。
8. 第一句使用问句放一个疑问句作为钩子。
9.严禁使用“家人们”这三个字。
"""

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个亲切自然、不爱叫卖的卡丁车俱乐部主播。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.9
        )
        script = response.choices[0].message.content.strip()
        return script, topic
    except Exception as e:
        print(f"[警告] AI生成失败，使用降级话术: {e}")
        return f"跟大家介绍一下，{knowledge}有兴趣的可以到店或者私信了解一下哈。", topic
# ==================== TTS生成语音 ====================
async def _tts(text, voice, output_file):
    communicate = edge_tts.Communicate(text, voice, rate="+10%")
    await communicate.save(output_file)

def generate_audio(text, voice, output_file):
    """同步包装，方便在线程里调用"""
    asyncio.run(_tts(text, voice, output_file))

# ==================== 预生成线程（生产者） ====================
def producer(queue: Queue, stop_event: threading.Event):
    """后台不断生成 (话术, 音频文件) 放入队列"""
    idx = 0
    os.makedirs("temp", exist_ok=True)
    while not stop_event.is_set():
        if queue.full():
            time.sleep(0.3)
            continue
        try:
            script, topic = generate_script()
            voice = random.choice(VOICES)
            # 用轮换文件名，避免占用冲突
            audio_file = f"temp/audio_{idx % (PREFETCH_SIZE + 2)}.mp3"
            generate_audio(script, voice, audio_file)
            queue.put({
                "script": script,
                "topic": topic,
                "voice": voice,
                "file": audio_file
            })
            idx += 1
        except Exception as e:
            print(f"[错误] 预生成失败: {e}")
            time.sleep(3)

# ==================== 音频播放 ====================
def init_audio():
    pygame.mixer.init()
    # 用单独 Channel 播放 BGM，music 通道播放人声
    if BGM_FILE and os.path.exists(BGM_FILE):
        try:
            bgm_sound = pygame.mixer.Sound(BGM_FILE)
            bgm_sound.set_volume(BGM_VOLUME)
            bgm_channel = pygame.mixer.Channel(0)
            bgm_channel.play(bgm_sound, loops=-1)
            print("[BGM] 背景音乐已启动")
        except Exception as e:
            print(f"[警告] BGM加载失败: {e}")

def play_audio(file_path):
    pygame.mixer.music.load(file_path)
    pygame.mixer.music.set_volume(VOICE_VOLUME)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    pygame.mixer.music.unload()

# ==================== 主循环（消费者） ====================
def main():
    print("=" * 50)
    print("抖音无人直播系统 V1（预生成无缝版）")
    print("按 Ctrl+C 停止")
    print("=" * 50)

    if not DEEPSEEK_API_KEY:
        print("[警告] 未检测到环境变量 DEEPSEEK_API_KEY，AI将无法调用，仅使用降级话术。")

    init_audio()

    queue = Queue(maxsize=PREFETCH_SIZE)
    stop_event = threading.Event()

    # 启动后台预生成线程
    worker = threading.Thread(target=producer, args=(queue, stop_event), daemon=True)
    worker.start()

    print("\n[状态] 正在预生成首段内容，请稍候...")
    count = 1

    try:
        while True:
            # 从队列取一段（阻塞等待，预生成保证基本不会等太久）
            item = queue.get()

            print(f"\n{'='*50}")
            print(f"第 {count} 段  [话题: {item['topic']}]  [音色: {item['voice']}]")
            print(f"[话术]: {item['script']}")
            print(f"{'='*50}")
            print(f"[状态] 播放中... (后台已缓冲 {queue.qsize()} 段)")

            play_audio(item["file"])
            print("[状态] 播放完成 ✓")

            # 随机停顿，更像真人节奏
            pause = random.uniform(1.5, 3.5)
            print(f"[等待] 停顿 {pause:.1f} 秒...")
            time.sleep(pause)

            count += 1

    except KeyboardInterrupt:
        print("\n\n[停止] 正在关闭...")
        stop_event.set()
        pygame.mixer.quit()
        print("[停止] 程序已退出")

if __name__ == "__main__":
    main()