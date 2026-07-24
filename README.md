# YouTube Downloader Web App

Een moderne web applicatie voor het downloaden van YouTube video's en audio in verschillende formaten.

## ✨ Features

- Download video's in MP4, WebM, MKV, AVI, MOV, FLV
- Download audio in MP3, M4A, WAV, FLAC, OGG, OPUS, AAC, WMA
- Selecteer kwaliteit van 144p tot 4K
- Kies FPS (24, 25, 30, 50, 60, 120)
- Selecteer audio bitrate (64-320 kbps)
- Download geschiedenis met bestandsbeheer
- Dark/Light mode
- Modern en intuïtieve interface
- Fast downloads met progress tracking

## 🚀 Deploy op Render

### Optie 1: Via Render Dashboard (Aanbevolen)

1. Maak een account aan op [Render.com](https://render.com)
2. Klik **"New +"** → **"Web Service"**
3. Connect je GitHub repository
4. Vul volgende gegevens in:
   - **Name**: yt-downloader (of eigen keuze)
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free (of paid voor meer resources)

5. Klik **"Create Web Service"**

### Optie 2: Via render.yaml

Maak een `render.yaml` bestand in de root van je repo:

```yaml
services:
  - type: web
    name: yt-downloader
    env: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python main.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

## 📋 Vereisten

- Python 3.8+
- FFmpeg (automatisch geïnstalleerd op Render)
- yt-dlp (wordt geïnstalleerd via requirements.txt)

## 🔧 Lokale Installatie

1. Clone de repo:
```bash
git clone <je-repo-url>
cd yt_downloader_web
```

2. Maak een virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
# of
source venv/bin/activate  # Mac/Linux
```

3. Installeer dependencies:
```bash
pip install -r requirements.txt
```

4. Start de applicatie:
```bash
python main.py
```

5. Open je browser op: http://localhost:8000

## 📁 Project Structuur

```
yt_downloader_web/
├── main.py                 # Backend server (FastAPI)
├── requirements.txt        # Python dependencies
├── start.bat              # Windows start script
├── .gitignore             # Git ignore bestand
├── README.md              # Deze file
├── static/
│   ├── index.html         # Frontend HTML
│   ├── styles.css         # CSS styles
│   └── app.js             # JavaScript functionaliteit
├── downloads/             # Download map (git ignored)
├── download_history.json  # Geschiedenis (git ignored)
└── downloader_config.json # Configuratie (git ignored)
```

## ⚠️ Belangrijke Opmerkingen

### Render Free Tier
- Service stopt na 15 minuten inactiviteit
- Max 512 MB RAM
- Downloads moeten binnen tijdlimiet voltooien
- Geen persistent storage tussen sessies

### Beperkingen
- Bestanden worden niet opgeslagen tussen sessies op de free tier
- Gebruik Render Persistent Disks (paid) voor opslag
- Rate limiting wordt aanbevolen voor productie gebruik

## 🔒 Security

Voor productie gebruik:
- Voeg rate limiting toe om misbruik te voorkomen
- Beveilig de delete endpoints
- Overweeg authenticatie toe te voegen
- Gebruik HTTPS (automatisch op Render)

## 📝 Licentie

Dit project is open source. Gebruik het verantwoordelijk.

## 🤝 Bijdragen

Voel je vrij om issues te melden of pull requests te indienen.

---

**Let op**: YouTube's service voorwaarden verbieden het downloaden van content zonder toestemming. Gebruik deze tool verantwoordelijk en alleen voor content die je het recht hebt te downloaden.