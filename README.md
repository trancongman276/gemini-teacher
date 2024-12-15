# Gemini 英语口语助手

这是一个基于 Google Gemini AI 的英语口语练习助手，它能实时识别你的英语发音，提供即时反馈和纠正建议。

Make by [Box](https://x.com/boxmrchen)

## 功能特点

- 🎤 实时语音识别
- 🤖 AI 驱动的发音评估
- 📝 语法纠正
- 🔄 情景对话练习
- 🎯 针对性发音指导
- 💡 智能场景切换

## 系统要求

- Python 3.8+ (Python 3.11+ 推荐)
- 麦克风设备
- 网络连接

## 前置依赖

需要一个 Gemini的API Key，这个API Key每天免费四百万次，足够使用了。

到这个页面 [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) 生成即可。

## 安装

1. 克隆仓库：
```bash
git clone https://github.com/nishuzumi/gemini-teacher.git
cd gemini_teacher
```

2. 创建并激活虚拟环境（推荐）：
```bash
python -m venv .venv
source .venv/bin/activate  # Unix/macOS
# 或
.venv\Scripts\activate  # Windows
```

3. 安装依赖：

在安装 Python 依赖前，请先安装以下系统依赖：

- Windows: 无需额外安装
- macOS: `brew install portaudio`
- Ubuntu/Debian: `sudo apt-get install portaudio19-dev python3-pyaudio`

```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行程序：
```bash
export GOOGLE_API_KEY=[your-api-key]
python starter.py
```

2. 按照提示说出英语句子
3. 等待 AI 助手的反馈
4. 根据反馈改进发音

## 交互说明

- 🎤 : 正在录音
- ♻️ : 正在处理
- 🤖 : AI 反馈

## 许可证

MIT

## 贡献

欢迎提交 Issue 和 Pull Request！
