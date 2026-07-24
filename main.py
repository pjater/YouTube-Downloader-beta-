#!/usr/bin/env python3
"""
YouTube Downloader Web App - Backend Server
"""

import os
import sys
import json
import threading
import uuid
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
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

DOWNLOADS_DIR.mkdir(exist_ok=True)

# Check ffmpeg
ffmpeg_available = FFMPEG_PATH.exists()
if not ffmpeg_available:
    import shutil
    ffmpeg_available = shutil.which("ffmpeg") is not None
if ffmpeg_available:
    print(f"FFmpeg found: {'system PATH' if not FFMPEG_PATH.exists() else FFMPEG_PATH}")
else:
    print("WARNING: ffmpeg not found")

# ===== FASTAPI APP =====
app = FastAPI(title="YouTube Downloader API")

# Mount static files
static_dir = BASE_DIR / "static"
print(f"Static directory: {static_dir}")
print(f"Static exists: {static_dir.exists()}")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    print("Static files mounted")
else:
    print(f"ERROR: Static directory not found at {static_dir}")

# ===== MODELS =====
class DownloadRequest(BaseModel):
    url: str
    mode: str
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
active_downloads: Dict[str, Dict[str, Any]] = {}
download_lock = threading.Lock()

# ===== CONFIG MANAGEMENT =====
def load_config() -> Dict[str, Any]:
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
        except Exception:
            pass
    return default_config

def save_config(config: Dict[str, Any]) -> None:
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def load_history() -> List[Dict[str, Any]]:
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_history(history: List[Dict[str, Any]]) -> None:
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def add_to_history(title: str, mode: str, quality: str, format_type: str, fps: Optional[str] = None, bitrate: Optional[str] = None, path: str = ""):
    history = load_history()
    entry = {
        "title": title or "Unknown",
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
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"error": "index.html not found"}, status_code=404)

# Serve static files
@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    """Serve static files"""
    full_path = static_dir / file_path
    if full_path.exists() and full_path.is_file():
        return FileResponse(full_path)
    return JSONResponse({"error": "Not found"}, status_code=404)

@app.get("/api/config")
async def get_config():
    config = load_config()
    return JSONResponse(config)

@app.post("/api/config")
async def update_config(config: ConfigUpdate):
    current = load_config()
    current.update(config.model_dump())
    save_config(current)
    return JSONResponse({"status": "success", "message": "Settings saved successfully!"})

@app.get("/api/history")
async def get_history():
    history = load_history()
    return JSONResponse(history)

@app.delete("/api/history")
async def clear_history():
    save_history([])
    return JSONResponse({"status": "success", "message": "History cleared"})

@app.post("/api/video-info")
async def get_video_info(request: VideoInfoRequest):
    try:
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
            info = ydl.extract_info(request.url, download=False, process=True)
            
            if not info:
                raise HTTPException(status_code=400, detail="Could not extract video information")
            
            title = info.get('title') or 'Unknown'
            uploader = info.get('uploader') or 'Unknown'
            duration = info.get('duration') or 0
            view_count = info.get('view_count') or 0
            
            if duration > 0:
                hours, remainder = divmod(int(duration), 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m {seconds}s"
            else:
                duration_str = "Unknown"
            
            formats = info.get('formats') or []
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
        error_msg = str(e)
        print(f"Video info error: {error_msg}")
        
        if "RequestsResponseAdapter" in error_msg or "_http_error" in error_msg:
            error_msg = "Network error. Please check your internet connection and try again."
        elif "Private video" in error_msg:
            error_msg = "This video is private or unavailable."
        elif "not available" in error_msg.lower():
            error_msg = "Video not found or not available."
        
        raise HTTPException(status_code=400, detail=error_msg)

@app.post("/api/download")
async def start_download(request: DownloadRequest):
    download_id = str(uuid.uuid4())
    
    if request.output_path:
        output_path = Path(request.output_path)
    else:
        config = load_config()
        output_path = Path(config.get("download_folder", str(DOWNLOADS_DIR)))
    
    output_path.mkdir(parents=True, exist_ok=True)
    
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

def download_video(download_id: str, request: DownloadRequest, output_path: Path):
    try:
        with download_lock:
            active_downloads[download_id]["status"] = "downloading"
        
        quality = request.quality
        fmt = request.format
        fps = request.fps
        
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
                except Exception:
                    pass
            elif d["status"] == "finished":
                with download_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["progress"] = 95
                        active_downloads[download_id]["status"] = "converting"
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
            title = info.get('title') or 'Unknown'
            
            with download_lock:
                active_downloads[download_id]["status"] = "completed"
                active_downloads[download_id]["progress"] = 100
                active_downloads[download_id]["title"] = title
            
            if downloaded_file_path:
                file_ext = Path(downloaded_file_path).suffix
            else:
                file_ext = f".{fmt}"
            file_name = f"{title}{file_ext}"
            file_name = "".join(c for c in file_name if c.isalnum() or c in " ._-()").strip()
            full_path = str(output_path / file_name)
            
            add_to_history(title, "video", request.quality, fmt, fps=request.fps, path=full_path)
            
    except Exception as e:
        with download_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "error"
                active_downloads[download_id]["error"] = str(e)

def download_audio(download_id: str, request: DownloadRequest, output_path: Path):
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
                except Exception:
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
            title = info.get('title') or 'Unknown'
            
            with download_lock:
                active_downloads[download_id]["status"] = "completed"
                active_downloads[download_id]["progress"] = 100
                active_downloads[download_id]["title"] = title
            
            if downloaded_file_path:
                file_path = str(downloaded_file_path)
            else:
                file_name = "".join(c for c in title if c.isalnum() or c in " ._-()").strip()
                file_path = str(output_path / f"{file_name}.{audio_format}")
            
            add_to_history(title, "audio", audio_format, audio_format, bitrate=f"{bitrate} kbps", path=file_path)
            
    except Exception as e:
        with download_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "error"
                active_downloads[download_id]["error"] = str(e)

@app.get("/api/download/{download_id}/status")
async def get_download_status(download_id: str):
    with download_lock:
        if download_id not in active_downloads:
            raise HTTPException(status_code=404, detail="Download not found")
        return JSONResponse(active_downloads[download_id])

@app.get("/api/downloads")
async def get_active_downloads():
    with download_lock:
        return JSONResponse(list(active_downloads.values()))

@app.post("/api/history/delete")
async def delete_history_item(data: Dict[str, Any]):
    index = data.get("index")
    delete_file = data.get("delete_file", True)
    
    history = load_history()
    if index is None or not isinstance(index, int) or index < 0 or index >= len(history):
        raise HTTPException(status_code=404, detail="History item not found")
    
    item = history.pop(index)
    
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
    for file in DOWNLOADS_DIR.iterdir():
        if file.is_file() and file.name == filename:
            return JSONResponse({"path": str(file.absolute())})
    
    history = load_history()
    for item in history:
        if item.get("path"):
            p = Path(item["path"])
            if p.exists() and p.name == filename:
                return JSONResponse({"path": str(p.absolute())})
    
    raise HTTPException(status_code=404, detail="File not found")

@app.get("/api/history/{index}/path")
async def get_history_item_path(index: int):
    history = load_history()
    if not history or index < 0 or index >= len(history):
        raise HTTPException(status_code=404, detail="History item not found")
    
    item = history[index]
    if item.get("path"):
        p = Path(item["path"])
        if p.exists():
            return JSONResponse({"path": str(p.absolute())})
    
    raise HTTPException(status_code=404, detail="File path not found")

# Catch-all route for SPA - MUST BE LAST
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Catch all routes and serve index.html"""
    # Skip API routes and static files
    if full_path.startswith("api/") or full_path.startswith("static/"):
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    # Serve index.html for all other routes
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"error": "Not found"}, status_code=404)

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"
    
    print("=" * 50)
    print("YouTube Downloader Web App")
    print("=" * 50)
    print(f"Starting server on {host}:{port}")
    print(f"Working directory: {BASE_DIR}")
    print(f"Static files: {static_dir}")
    print("=" * 50)
    
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except Exception as e:
        print(f"ERROR: Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
