# YouTube Downloader - Web App

A modern, browser-based YouTube downloader with a standalone window experience. This application replicates the functionality and visual design of the original tkinter app, but with a web-based frontend and Python FastAPI backend.

## Features

- **Download Videos**: Download YouTube videos in multiple formats (MP4, WebM, MKV, AVI, MOV, FLV)
- **Download Audio**: Extract audio in multiple formats (MP3, M4A, WAV, FLAC, OGG, OPUS, AAC, WMA)
- **Quality Selection**: Choose from 144p to 4K video quality
- **FPS Selection**: Select frame rate (24, 25, 30, 50, 60, 120 FPS)
- **Audio Bitrate**: Choose audio quality (64-320 kbps)
- **Download History**: Track all your downloads with timestamps
- **Persistent Settings**: Save your preferences for future sessions
- **Modern Dark Theme**: Beautiful, intuitive interface
- **Standalone Window**: Opens in its own app window (Edge/Chrome app mode)

## Architecture

### Backend (Python/FastAPI)
- **Framework**: FastAPI with Uvicorn server
- **Download Engine**: yt-dlp for video/audio extraction
- **Processing**: FFmpeg for format conversion
- **API Endpoints**:
  - `GET /` - Serves the frontend
  - `GET /api/config` - Get application settings
  - `POST /api/config` - Update settings
  - `GET /api/history` - Get download history
  - `DELETE /api/history` - Clear history
  - `POST /api/video-info` - Get video information
  - `POST /api/download` - Start a download
  - `GET /api/download/{id}/status` - Check download progress

### Frontend (HTML/CSS/JavaScript)
- **Pure vanilla JavaScript** - No frameworks required
- **Responsive Design** - Adapts to different screen sizes
- **Real-time Progress** - Live download progress updates
- **Modern UI** - Dark theme with smooth animations

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows 10/11
- Microsoft Edge or Google Chrome (for app mode)

### Setup

1. **Navigate to the project folder**:
   ```bash
   cd yt_downloader_web
   ```

2. **Run the start script**:
   ```bash
   start.bat
   ```

   This will automatically:
   - Create a virtual environment (if needed)
   - Install all dependencies
   - Start the backend server
   - Open the application in a standalone window

## Manual Setup (Alternative)

If you prefer to set up manually:

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate.bat
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the backend server**:
   ```bash
   python main.py
   ```

4. **Open in browser**:
   - Navigate to `http://localhost:8000`
   - Or use Edge/Chrome app mode:
     ```
     msedge --app=http://localhost:8000 --window-size=1000,750
     ```

## Usage

### Getting Started
1. Launch the application using `start.bat`
2. The app will open in a standalone window
3. Navigate using the bottom navigation bar or home page buttons

### Downloading Videos
1. Go to the **Downloader** page
2. Paste a YouTube URL in the URL field
3. Click **Get Info** to fetch video details
4. Select download type (Video or Audio)
5. Choose your preferred format, quality, and settings
6. Select download location (or use default)
7. Click **DOWNLOAD** to start

### Managing Settings
1. Go to the **Settings** page
2. Configure your preferences:
   - Default download folder
   - Default video quality and format
   - Default audio format and bitrate
   - FPS preference
3. Click **Save Settings** to persist changes

### Viewing History
- Click the **History** button on the downloader page
- View your last 20 downloads
- History is automatically saved and persists between sessions

## File Structure

```
yt_downloader_web/
├── main.py                 # FastAPI backend server
├── requirements.txt        # Python dependencies
├── start.bat              # Windows launcher script
├── README.md              # This file
├── downloads/             # Default download directory
├── static/
│   ├── index.html         # Main HTML file
│   ├── styles.css         # All styling
│   └── app.js             # Frontend JavaScript logic
├── downloader_config.json # User settings (auto-generated)
└── download_history.json  # Download history (auto-generated)
```

## Configuration

The app stores configuration in `downloader_config.json`:
- Download folder path
- Default video/audio settings
- "Last used" preferences
- Always-ask-location flag

## History

Download history is stored in `download_history.json`:
- Up to 50 most recent downloads
- Includes title, mode, quality, format, timestamp
- Persists between sessions

## Troubleshooting

### Server won't start
- Ensure Python 3.8+ is installed
- Check that port 8000 is not in use
- Verify all dependencies are installed

### Downloads fail
- Ensure FFmpeg is available (included with yt-dlp)
- Check internet connection
- Verify YouTube URL is valid
- Check available disk space

### Window won't open
- Ensure Edge or Chrome is installed
- Try using the default browser option in `start.bat`
- Check if popup blocker is active

## Technical Details

### Backend Technologies
- **FastAPI**: Modern, fast web framework for Python
- **Uvicorn**: ASGI server for running the app
- **yt-dlp**: YouTube video downloader library
- **FFmpeg**: Audio/video processing (auto-downloaded by yt-dlp)

### Frontend Technologies
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with flexbox/grid
- **Vanilla JavaScript**: No frameworks, pure ES6+
- **Fetch API**: For async API calls

### Browser Compatibility
- Microsoft Edge (recommended for app mode)
- Google Chrome (alternative for app mode)
- Any modern browser (standard mode)

## Differences from Original Tkinter App

While maintaining the same functionality and visual design, the web version offers:
- **Cross-platform potential**: Can run on any OS with Python
- **Easier updates**: Frontend can be updated without reinstalling
- **Better performance**: Faster UI rendering
- **Modern web technologies**: Easier to maintain and extend
- **Standalone window**: App mode provides native-like experience

## License

This project is for educational purposes. Please respect YouTube's Terms of Service and copyright laws when downloading content.

## Credits

Built with:
- FastAPI
- yt-dlp
- FFmpeg
- Vanilla JavaScript
