 📚 Study Tracker Bot

A Telegram bot that helps students track their study sessions,
analyze progress with AI, and generate weekly study plans.

✨ Features

- ⏱️ Log and track study sessions by subject
- 🤖 AI-powered weekly progress analysis
- 📅 Personalized study plan generation
- 🎙️ Voice report delivery
- ⭐ Premium subscription system

 🛠️ Tech Stack

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![aiogram](https://img.shields.io/badge/aiogram-3.x-blue)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-asyncpg-blue?logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-green?logo=openai)

🚀 Getting Started

### Prerequisites
- Python 3.11+
- PostgreSQL
- Telegram Bot Token

 Installation

git clone https://github.com/یوزرنیمت/study-bot.git
cd study-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

 Configuration

cp .env.example .env
 Edit .env with your credentials
 Run

python main.py

📁 Project Structure

study-bot/
├── bot/              # Telegram handlers & keyboards
├── ai/               # AI analyzer & planner
├── database/         # Models & repositories
├── premium/          # Subscription system
├── voice/            # Voice generation
└── main.py
 📄 License
MIT
