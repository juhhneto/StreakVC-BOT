# 🔥 StreakVC Bot

A Discord bot that tracks voice channel activity, builds daily streaks, and ranks members by weekly voice time.

---


## ✨ Features

-  **Voice tracking** — monitors members in voice channels every 60 seconds
-  **Daily streaks** — awards a streak day when a member reaches 30+ minutes in VC
-  **XP & Level system** — 50 levels based on daily voice minutes
-  **Weekly ranking** — top 3 members by weekly voice time per server
-  **Multi-server support** — each server has its own independent data
-  **Bilingual** — supports Portuguese 🇧🇷 and English 🇺🇸
-  **Mid-session flush** — saves progress every 30 minutes without requiring the user to leave VC

---

## ⚙️ How It Works

The bot joins a voice channel via `/join` and polls it every **60 seconds**, tracking which members are present. When a member leaves, their session duration is saved to the database.

Every **30 minutes**, active sessions are flushed to the database so that `/streak` reflects live progress without needing to disconnect.

A streak day is counted once the member accumulates **30 minutes** of voice time in a single day. Streaks reset if a day is missed.

---

## 🤖 Commands

| Command | Description |
|---|---|
| `/join` | Bot joins your current voice channel and starts tracking |
| `/leave` | Bot leaves and saves all open sessions |
| `/streak` | Shows your streak, today's voice time, XP and level |
| `/ranking` | Shows the top 3 members by weekly voice time |
| `/language` | Switch bot language (Portuguese / English) |

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/your-username/StreakVC-BOT.git
cd StreakVC-BOT
```

**2. Create and activate a virtual environment**
```bash
python -m venv .venv

# Windows
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables** — see [Configuration](#-configuration)

**5. Run the bot**
```bash
python bot.py
```

### Required Bot Permissions

| Permission | Reason |
|---|---|
| `View Channels` | See voice channels |
| `Connect` | Join voice channels |
| `Speak` | Stay present in voice |
| `Send Messages` | Respond to commands |
| `Embed Links` | Send rich embeds |
| `Use Slash Commands` | Register and respond to `/` commands |
| `Read Message History` | Required by Discord for slash commands |

---

## 🗄️ Database Schema

SQLite database — `streakVCBot.db`

```
voice_activity
─────────────────────────────
user_id           INTEGER  ──┐ PRIMARY KEY (composite)
guild_id          INTEGER  ──┘
username          TEXT
streak            INTEGER
last_streak_date  TEXT
daily_vc_minutes  INTEGER
last_reset_date   TEXT
weekly_vc_minutes INTEGER
week_start_date   TEXT
```

- `user_id` + `guild_id` form the composite primary key, ensuring each user has independent data per server.
- The database is created and migrated automatically on bot startup — no manual setup required.

---

## 📁 Project Structure

```
StreakVC-BOT/
├── bot.py           # Main bot file
├── i18n.py           # Internationalization (pt/en)
├── streakVCBot.db    # SQLite database (auto-created)
├── requirements.txt  # Python dependencies
├── .env              # Bot token (not committed)
├── .gitignore
└── README.md
```

---

## 📦 Requirements

- Python 3.8 – 3.13
- discord.py
- python-dotenv
- colorama
- cachetools

Install all at once:
```bash
pip install -r requirements.txt
```

---

## 📄 License

This project is open source. Feel free to use, modify and distribute it.
