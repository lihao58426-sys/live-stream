"""
直播话术生成模块
================
职责：管理知识库 + 加权选话题 + 调 DeepSeek 生成自然口播话术。

这是无人直播的"大脑"——决定主播接下来说什么。
"""

import logging
import os
import random

from openai import OpenAI

from exceptions import AIGenerationError

logger = logging.getLogger(__name__)

# ======================== 知识库 ========================
# 每个话题对应一段事实信息，AI 基于这些信息生成口播话术
KNOWLEDGE: dict[str, str] = {
    "店铺": (
        "我们的卡丁车俱乐部位于咸阳西站地铁C口，场地面积超过400平米，"
        "作为室内儿童卡丁车场馆我们做到更宽敞的赛道，更亲民的价格，更贴心的服务"
    ),
    "套餐": (
        "我们提供多种套餐选择：体验套餐38元12圈，首次开车的小车手有3圈，"
        "5圈的体验价格，可以直接小黄车购买"
    ),
    "安全": (
        "所有车辆都经过严格检测，配备专业安全装备，"
        "现场有专业教练指导，适合3岁以上儿童和成人。"
    ),
    "儿童成长价值": (
        "卡丁车可以锻炼孩子的反应能力、专注力和身体协调性，是很好的亲子活动。"
    ),
    "位置": "我们就在咸阳西站地铁口，地铁直达，停车方便。",
    "营业时间": "每天上午10点到晚上9点，全年无休，随时欢迎来体验。",
    "购买方式": "可以直接到店购买，也可以在抖音团购下单，还有更多优惠哦。",
}

# 话题权重：转化相关话题出现频率更高
TOPIC_WEIGHTS: dict[str, float] = {
    "店铺": 1.0,
    "套餐": 2.0,          # 重点推
    "安全": 1.2,
    "儿童成长价值": 1.0,
    "位置": 1.5,          # 常被问
    "营业时间": 1.0,
    "购买方式": 2.0,      # 重点推
}

TOPICS = list(KNOWLEDGE.keys())

# ======================== 话题选择 ========================
_recent_topics: list[str] = []  # 最近用过的，避免短期重复
MAX_RECENT = 3


def pick_topic() -> str:
    """加权随机选择话题，避免短期内重复

    权重高的（套餐、购买方式）出现频率更高，
    但同一个话题不会在 3 轮内重复。
    """
    candidates = [t for t in TOPICS if t not in _recent_topics]
    if not candidates:
        candidates = TOPICS

    weights = [TOPIC_WEIGHTS.get(t, 1.0) for t in candidates]
    topic = random.choices(candidates, weights=weights, k=1)[0]

    _recent_topics.append(topic)
    if len(_recent_topics) > MAX_RECENT:
        _recent_topics.pop(0)

    return topic


# ======================== AI 话术生成 ========================
# OpenAI 客户端（兼容 DeepSeek API）
_api_key = os.getenv("DEEPSEEK_API_KEY", "")
_base_url = "https://api.deepseek.com"
_client = OpenAI(api_key=_api_key, base_url=_base_url)


def generate_script() -> tuple[str, str]:
    """调用 DeepSeek 生成一段 20-30 秒的直播口播话术

    失败时自动降级：用知识库原文拼一段简单介绍。

    Returns:
        (话术文本, 话题名) — 话题名供 main.py 打印日志用
    """
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
9. 严禁使用"家人们"这三个字。
"""

    try:
        response = _client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "你是一个亲切自然、不爱叫卖的卡丁车俱乐部主播。"},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1000,
            temperature=0.9,
        )
        script = response.choices[0].message.content.strip()
        return script, topic
    except Exception as e:
        # 任何 AI 调用异常 → 降级话术，直播不能停
        logger.warning(f"AI生成失败，使用降级话术: {e}")
        fallback = f"跟大家介绍一下，{knowledge}有兴趣的可以到店或者私信了解一下哈。"
        return fallback, topic
