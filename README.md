# AI 无人直播系统

基于 DeepSeek 的 AI 话术生成 + Edge TTS 语音合成 + Pygame 音频播放，实现 24 小时不间断无人直播。

## 功能

- **AI 话术生成**：DeepSeek 实时生成直播话术，话题加权随机避免重复
- **多音色轮换**：Edge TTS 多音色切换，避免被识别为 AI
- **生产者-消费者模式**：asyncio + threading 并发，预生成话术队列，无缝衔接
- **降级运行**：无 API Key 时使用内置话术库

## 技术栈

Python · DeepSeek API · Edge TTS · Pygame · asyncio

## 环境要求

- Python >= 3.10
- 环境变量：

| 变量名 | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |

## 安装

```bash
git clone https://github.com/lihao58426-sys/live-stream.git
cd live-stream
pip install -r requirements.txt
```

## 使用

```bash
python 直播.py
```

## 注意事项

本项目仅用于技术学习，实际使用需遵守直播平台规则。
