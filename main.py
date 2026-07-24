#!/usr/bin/env python3
"""
YouTube Downloader Web App - Backend Server
Provides API endpoints for downloading videos and audio
"""

import os
import sys
import json
import threading
import uuid
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
import yt_dlp

# ===== CONFIGURATION =====
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "downloader_config.json"
HISTORY_FILE = BASE_DIR / "download_history.json"
DOWNLOADS_DIR = BASE_DIR / "downloads"
FFMPEG_PATH = BASE_DIR / "ffmpeg.exe"

# Ensure directories exist
DOWNLOADS_DIR.mkdir(exist_ok=True)

# Check if ffmpeg is available
ffmpeg_available = FFMPEG_PATH.exists()
if not ffmpeg_available:
    # Also check PATH
    import shutil
    ffmpeg_available = shutil.which("ffmpeg") is not None
if ffmpeg_available:
    print(f"FFmpeg found at: {FFMPEG_PATH if FFMPEG_PATH.exists() else 'system PATH'}")
else:
    print("WARNING: ffmpeg not found. Video downloads that need merging may fail.")
    print("Place ffmpeg.exe in the application folder for full functionality.")

# ===== FASTAPI APP =====
app = FastAPI(title="YouTube Downloader API")

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# ===== MODELS =====
class DownloadRequest(BaseModel):
    url: str
    mode: str  # "video" or "audio"
    quality: str = "best"
    format: str = "mp4"
    fps: str = "30"
    audio_format: str = "mp3"
    audio_bitrate: str = "192"
    output_path: Optional[str] = None

class VideoInfoRequest(BaseModel):
    url: str

class ConfigUpdate(BaseModel):
    download_folder: str
    always_ask_location: bool = False
    default_video_quality: str = "best"
    default_video_format: str = "mp4"
    default_fps: str = "30"
    default_audio_bitrate: str = "192"
    default_audio_format: str = "mp3"

# ===== GLOBAL STATE =====
active_downloads = {}
download_lock = threading.Lock()

# ===== CONFIG MANAGEMENT =====
def load_config():
    """Load configuration from JSON file"""
    default_config = {
        "download_folder": str(DOWNLOADS_DIR),
        "always_ask_location": False,
        "default_video_quality": "best",
        "default_video_format": "mp4",
        "default_fps": "30",
        "default_audio_bitrate": "192",
        "default_audio_format": "mp3",
        "last_used": {
            "video_quality": "1080p",
            "video_format": "mp4",
            "fps": "60",
            "audio_bitrate": "192",
            "audio_format": "mp3"
        }
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                default_config.update(loaded)
        except:
            pass
    return default_config

def save_config(config):
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except:
        pass

def load_history():
    """Load download history"""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return []

def save_history(history):
    """Save download history"""
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except:
        pass

def add_to_history(title, mode, quality, format_type, fps=None, bitrate=None, path=""):
    """Add download to history"""
    history = load_history()
    entry = {
        "title": title,
        "mode": mode,
        "quality": quality,
        "format": format_type,
        "fps": fps,
        "bitrate": bitrate,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "path": path
    }
    history.insert(0, entry)
    if len(history) > 50:
        history = history[:50]
    save_history(history)
    return entry

# ===== API ROUTES =====

@app.get("/")
async def root():
    """Serve the main HTML file"""
    return FileResponse(BASE_DIR / "static" / "index.html")

@app.get("/api/config")
async def get_config():
    """Get current configuration"""
    config = load_config()
    return JSONResponse(config)

@app.post("/api/config")
async def update_config(config: ConfigUpdate):
    """Update configuration"""
    current = load_config()
    current.update(config.model_dump())
    save_config(current)
    return JSONResponse({"status": "success", "message": "Settings saved successfully!"})

@app.get("/api/history")
async def get_history():
    """Get download history"""
    history = load_history()
    return JSONResponse(history)

@app.delete("/api/history")
async def clear_history():
    """Clear download history"""
    save_history([])
    return JSONResponse({"status": "success", "message": "History cleared"})

@app.post("/api/video-info")
async def get_video_info(request: VideoInfoRequest):
    """Get video information"""
    try:
        # Use a simpler approach with yt-dlp
        import yt_dlp
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'ignoreerrors': True,
            'no_color': True,
            'socket_timeout': 30,
            'retries': 3
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info without downloading
            info = ydl.extract_info(request.url, download=False, process=True)
            
            if not info:
                raise HTTPException(status_code=400, detail="Could not extract video information")
            
            # Extract relevant information
            title = info.get('title', 'Unknown')
            uploader = info.get('uploader', 'Unknown')
            duration = info.get('duration', 0) or 0
            view_count = info.get('view_count', 0) or 0
            
            # Format duration
            if duration > 0:
                hours, remainder = divmod(int(duration), 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m {seconds}s"
            else:
                duration_str = "Unknown"
            
            # Get best quality
            formats = info.get('formats', [])
            best_quality = "?"
            for fmt in formats:
                if fmt.get('vcodec') != 'none' and fmt.get('height'):
                    best_quality = f"{fmt.get('height')}p"
                    break
            
            return JSONResponse({
                "title": title,
                "uploader": uploader,
                "duration": duration_str,
                "duration_seconds": int(duration) if duration else 0,
                "view_count": view_count,
                "best_quality": best_quality,
                "thumbnail": info.get('thumbnail', ''),
                "webpage_url": info.get('webpage_url', request.url)
            })
            
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Video info error: {error_msg}")
        print(traceback.format_exc())
        
        # Provide user-friendly error messages
        if "RequestsResponseAdapter" in error_msg or "_http_error" in error_msg:
            error_msg = "Network error. Please check your internet connection and try again."
        elif "Private video" in error_msg:
            error_msg = "This video is private or unavailable."
        elif "not available" in error_msg.lower():
            error_msg = "Video not found or not available."
        
        raise HTTPException(status_code=400, detail=error_msg)

@app.post("/api/download")
async def start_download(request: DownloadRequest):
    """Start a download"""
    download_id = str(uuid.uuid4())
    
    # Determine output path
    if request.output_path:
        output_path = Path(request.output_path)
    else:
        config = load_config()
        output_path = Path(config.get("download_folder", str(DOWNLOADS_DIR)))
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Create download entry
    with download_lock:
        active_downloads[download_id] = {
            "id": download_id,
            "url": request.url,
            "mode": request.mode,
            "status": "preparing",
            "progress": 0,
            "speed": 0,
            "eta": 0,
            "title": "",
            "error": None
        }
    
    # Start download in background thread
    def download_thread():
        try:
            if request.mode == "video":
                download_video(download_id, request, output_path)
            else:
                download_audio(download_id, request, output_path)
        except Exception as e:
            with download_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = "error"
                    active_downloads[download_id]["error"] = str(e)
    
    thread = threading.Thread(target=download_thread, daemon=True)
    thread.start()
    
    return JSONResponse({"download_id": download_id, "status": "started"})

def download_video(download_id, request, output_path):
    """Download video"""
    try:
        with download_lock:
            active_downloads[download_id]["status"] = "downloading"
        
        quality = request.quality
        fmt = request.format
        fps = request.fps
        
        # Build format selector
        if quality == "best":
            format_selector = "bestvideo+bestaudio/best"
        elif quality == "worst":
            format_selector = "worstvideo+worstaudio/worst"
        else:
            height = quality.split("p")[0].split(" ")[0]
            if height.isdigit():
                format_selector = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
            else:
                format_selector = "bestvideo+bestaudio/best"
        
        # Add FPS filter if selected
        if fps and fps != "30":
            format_selector = format_selector.replace("bestvideo", f"bestvideo[fps={fps}]")
        
        downloaded_file_path = None
        
        def progress_hook(d):
            if d["status"] == "downloading":
                try:
                    total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        progress = int((downloaded / total) * 100)
                        speed = d.get('speed', 0) or 0
                        eta = d.get('eta', 0) or 0
                        
                        with download_lock:
                            if download_id in active_downloads:
                                active_downloads[download_id]["progress"] = progress
                                active_downloads[download_id]["speed"] = speed
                                active_downloads[download_id]["eta"] = eta
                except:
                    pass
            elif d["status"] == "finished":
                with download_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["progress"] = 95
                        active_downloads[download_id]["status"] = "converting"
                # Store the downloaded filename
                nonlocal downloaded_file_path
                downloaded_file_path = d.get('filename')
        
        ydl_opts = {
            'format': format_selector,
            'outtmpl': str(output_path / '%(title)s.%(ext)s'),
            'merge_output_format': fmt,
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=True)
            title = info.get('title', 'Unknown')
            
            with download_lock:
                active_downloads[download_id]["status"] = "completed"
                active_downloads[download_id]["progress"] = 100
                active_downloads[download_id]["title"] = title
            
            # Determine the actual file path
            if downloaded_file_path:
                file_ext = Path(downloaded_file_path).suffix
            else:
                file_ext = f".{fmt}"
            file_name = f"{title}{file_ext}"
            # Sanitize filename
            file_name = "".join(c for c in file_name if c.isalnum() or c in " ._-()").strip()
            full_path = str(output_path / file_name)
            
            # Add to history
            add_to_history(title, "video", request.quality, fmt, fps=request.fps, path=full_path)
            
    except Exception as e:
        with download_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "error"
                active_downloads[download_id]["error"] = str(e)

def download_audio(download_id, request, output_path):
    """Download audio"""
    try:
        with download_lock:
            active_downloads[download_id]["status"] = "downloading"
        
        audio_format = request.audio_format
        bitrate = request.audio_bitrate
        
        codecs = {
            "mp3": "libmp3lame",
            "m4a": "aac",
            "wav": "pcm_s16le",
            "flac": "flac",
            "ogg": "libvorbis",
            "opus": "libopus",
            "aac": "aac",
            "wma": "wmav2"
        }
        codec = codecs.get(audio_format, "libmp3lame")
        
        downloaded_file_path = None
        
        def progress_hook(d):
            if d["status"] == "downloading":
                try:
                    total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
                    downloaded = d.get('downloaded_bytes', 0)
                    if total > 0:
                        progress = int((downloaded / total) * 100)
                        speed = d.get('speed', 0) or 0
                        eta = d.get('eta', 0) or 0
                        
                        with download_lock:
                            if download_id in active_downloads:
                                active_downloads[download_id]["progress"] = progress
                                active_downloads[download_id]["speed"] = speed
                                active_downloads[download_id]["eta"] = eta
                except:
                    pass
            elif d["status"] == "finished":
                with download_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["progress"] = 95
                        active_downloads[download_id]["status"] = "converting"
                nonlocal downloaded_file_path
                downloaded_file_path = d.get('filename')
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': str(output_path / '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
            }],
            'postprocessor_args': ['-codec:a', codec, '-b:a', f'{bitrate}k'],
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=True)
            title = info.get('title', 'Unknown')
            
            with download_lock:
                active_downloads[download_id]["status"] = "completed"
                active_downloads[download_id]["progress"] = 100
                active_downloads[download_id]["title"] = title
            
            # Determine the actual file path
            if downloaded_file_path:
                file_path = str(downloaded_file_path)
            else:
                file_name = "".join(c for c in title if c.isalnum() or c in " ._-()").strip()
                file_path = str(output_path / f"{file_name}.{audio_format}")
            
            # Add to history
            add_to_history(title, "audio", audio_format, audio_format, bitrate=f"{bitrate} kbps", path=file_path)
            
    except Exception as e:
        with download_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "error"
                active_downloads[download_id]["error"] = str(e)

@app.get("/api/download/{download_id}/status")
async def get_download_status(download_id: str):
    """Get download status"""
    with download_lock:
        if download_id not in active_downloads:
            raise HTTPException(status_code=404, detail="Download not found")
        return JSONResponse(active_downloads[download_id])

@app.get("/api/downloads")
async def get_active_downloads():
    """Get all active downloads"""
    with download_lock:
        return JSONResponse(list(active_downloads.values()))

@app.post("/api/history/delete")
async def delete_history_item(data: dict):
    """Delete a history item and its file"""
    index = data.get("index")
    delete_file = data.get("delete_file", True)
    
    history = load_history()
    if index is None or index < 0 or index >= len(history):
        raise HTTPException(status_code=404, detail="History item not found")
    
    item = history.pop(index)
    
    # Delete the actual file if it exists
    if delete_file and item.get("path"):
        file_path = Path(item["path"])
        if file_path.exists():
            try:
                os.remove(file_path)
                print(f"Deleted file: {file_path}")
            except Exception as e:
                print(f"Failed to delete file {file_path}: {e}")
        else:
            print(f"File not found: {file_path}")
    
    save_history(history)
    return JSONResponse({"status": "success", "message": "Item deleted"})

@app.get("/api/download/{filename}/path")
async def get_download_path(filename: str):
    """Get full path of a downloaded file"""
    # Search in downloads folder
    for file in DOWNLOADS_DIR.iterdir():
        if file.is_file() and file.name == filename:
            return JSONResponse({"path": str(file.absolute())})
    
    # Also check in configured download folders from history
    history = load_history()
    for item in history:
        if item.get("path"):
            p = Path(item["path"])
            if p.exists() and p.name == filename:
                return JSONResponse({"path": str(p.absolute())})
    
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/history/{index}/path")
async def get_history_item_path(index: int):
    """Get path of a history item by index"""
    history = load_history()
    if index < 0 or index >= len(history):
        raise HTTPException(status_code=404, detail="History item not found")
    
    item = history[index]
    if item.get("path"):
        p = Path(item["path"])
        if p.exists():
            return JSONResponse({"path": str(p.absolute())})
    
    raise HTTPException(status_code=404, detail="File path not found")

if __name__ == "__main__":
    import uvicorn
    print("Starting YouTube Downloader Web App...")
    print("Open your browser to: http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)