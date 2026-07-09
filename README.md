# ZETA v1.0 — AI Chat Platform

**Your intelligence, refined.**

ZETA is a full-stack AI chat **desktop application** for Windows that connects you to **any AI model** — OpenAI, Anthropic Claude, Google Gemini, DeepSeek V4 Flash, Mistral, Groq, Together AI, Ollama (local), and more — all through a single, clean native window. No browser tabs, no subscriptions, no vendor lock-in.

Just add your API key from any provider and start chatting instantly.

---

## Features

- Multi-provider chat (OpenAI, Claude, Gemini, DeepSeek, Groq, Mistral, Together, OpenRouter, ZenMux, Ollama)
- Real-time token-by-token streaming
- Conversation management (create, rename, pin, favorite, search, delete)
- Prompt library with 50+ master prompts categorized by domain
- Image generation (via OpenAI-compatible providers)
- Theme system — Dark, Light, Graphite
- Full user authentication (register, login, password reset, remember me)
- Profile management with avatar upload
- API key management with Fernet encryption at rest
- Session-based authentication
- Export account data (chats, prompts, images as JSON)
- Native Windows desktop window (no browser)
- Responsive design — desktop and mobile

---

## How to Get API Keys (Free Options)

| Provider | Key Website | Free Tier |
|----------|-------------|-----------|
| **OpenRouter** | https://openrouter.ai/keys | $1 free credit on signup, free models available |
| **DeepSeek** | https://platform.deepseek.com/api_keys | Trial credits on signup |
| **Groq** | https://console.groq.com/keys | Free tier with rate limits |
| **Google Gemini** | https://aistudio.google.com/apikey | Free tier with rate limits |
| **OpenAI** | https://platform.openai.com/api-keys | $5 free credit for new accounts |
| **Anthropic** | https://console.anthropic.com/ | $5 free credit for new accounts |
| **Mistral** | https://console.mistral.ai/api-keys/ | Free tier available |
| **Together AI** | https://api.together.xyz/settings/api-keys | $1 free credit |
| **ZenMux** | https://zenmux.ai | Check website for free tier |
| **Ollama** | https://ollama.com | Free (local, no key needed) |

### Recommended Free Path

1. Go to **https://openrouter.ai/keys**
2. Create an account (email or Google/GitHub — free, no credit card)
3. Generate an API key
4. Add it to ZETA → Settings → API Keys → OpenRouter
5. You now have access to DeepSeek V4 Flash, Llama 3, Mistral, and many other models for free

---

## Quick Start

### Windows desktop app (recommended):
```
1. Double-click ZETA.exe
```

The app opens in its own native window — no browser needed.

### Or run from source:
```bash
pip install -r requirements.txt
python app.py
```

The app runs at **http://127.0.0.1:3000**

### First steps:
1. Launch ZETA.exe (or open http://127.0.0.1:3000)
2. Create an account (register)
3. Go to Settings → API Keys → add your key
4. Start chatting!

---

## Tech Stack

- **Backend:** Python, Flask, SQLite (extensible to PostgreSQL)
- **Frontend:** Vanilla JS, CSS (glassmorphism design system)
- **Desktop Window:** pywebview (Microsoft Edge WebView2)
- **Encryption:** Fernet (cryptography library)
- **Streaming:** Server-Sent Events (SSE)

---

## Project Structure

```
zeta-ai/
├── app.py              # Flask application entry point
├── auth.py             # Authentication routes & decorators
├── chat.py             # Chat CRUD & streaming routes
├── api.py              # Prompts, API keys, settings, images
├── models.py           # Data access layer
├── database.py         # SQLite connection & schema
├── crypto_utils.py     # Fernet encryption for API keys
├── settings.py         # Flask config & JSON loader
├── config.json         # Themes, providers, categories
├── requirements.txt    # Python dependencies
├── run.bat             # One-click browser launcher
├── zeta_desktop.py     # Desktop entry point (pywebview)
├── build_exe.bat        # Build ZETA.exe with PyInstaller
├── database/
│   └── users.db        # SQLite database (auto-created)
└── statics/
    ├── css/
    │   └── style.css    # Full design system
    └── js/
        ├── main.js      # Shared utilities, dropdown, avatar upload
        ├── chat.js      # Chat application logic
        ├── auth.js      # Auth form handling
        └── theme.js     # Theme manager
```

---

## Building the Desktop App

Run `build_exe.bat` to produce a single `.exe`:

```bash
.\build_exe.bat
```

Output: `dist\ZETA.exe` — a standalone Windows executable (no Python required).

---

## Contact

- **Developer:** Bakre Lamcharki (a.k.a. shelby__x1 / RichardRamirez333)
- **Email:** 1thomas8shelby1@gmail.com
- **Phone:** 0700616121
- **Location:** Morocco

---

## License

MIT License

Copyright © 2025–2026 **shelby__x1 (RichardRamirez333) / Bakre Lamcharki**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE."# ZETA-AI-chatbot-" 
