#!/usr/bin/env python3
"""
YouTube Downloader Web App - Backend Server
Downloads videos/audio and streams them directly to the client's browser.
"""

import os
import sys
import json
import threading
import uuid
import shutil
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel
import yt_dlp

# ===== CONFIGURATION =====
BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "downloader_config.json"
HISTORY_FILE = BASE_DIR / "download_history.json"
DOWNLOADS_DIR = BASE_DIR / "downloads"
COOKIES_FILE = BASE_DIR / "cookies.txt"
FFMPEG_PATH = BASE_DIR / "ffmpeg.exe"

DOWNLOADS_DIR.mkdir(exist_ok=True)

# Temporary download files - cleaned up after serving
TEMP_DOWNLOADS: Dict[str, Dict[str, Any]] = {}
TEMP_LOCK = threading.Lock()

# Check ffmpeg
ffmpeg_available = FFMPEG_PATH.exists()
if not ffmpeg_available:
    ffmpeg_available = shutil.which("ffmpeg") is not None
if ffmpeg_available:
    print(f"FFmpeg found: {'system PATH' if not FFMPEG_PATH.exists() else FFMPEG_PATH}")
else:
    print("WARNING: ffmpeg not found")

# ===== FASTAPI APP =====
app = FastAPI(title="YouTube Downloader API")

# Mount static files
static_dir = BASE_DIR / "static"
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

class VideoInfoRequest(BaseModel):
    url: str

class ConfigUpdate(BaseModel):
    default_video_quality: str = "best"
    default_video_format: str = "mp4"
    default_fps: str = "30"
    default_audio_bitrate: str = "192"
    default_audio_format: str = "mp3"

# ===== GLOBAL STATE =====
active_downloads: Dict[str, Dict[str, Any]] = {}
download_lock = threading.Lock()

# ===== COOKIE MANAGEMENT =====
def get_yt_dlp_cookie_options() -> Dict[str, Any]:
    """Get yt-dlp options for cookies, trying multiple methods."""
    opts = {}
    
    if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0:
        print(f"Using cookies from: {COOKIES_FILE}")
        opts['cookiefile'] = str(COOKIES_FILE)
        return opts
    
    print("No cookies found. YouTube may still block requests.")
    return opts

# ===== CONFIG MANAGEMENT =====
def load_config() -> Dict[str, Any]:
    default_config = {
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

def add_to_history(title: str, mode: str, quality: str, format_type: str, fps: Optional[str] = None, bitrate: Optional[str] = None):
    history = load_history()
    entry = {
        "title": title or "Unknown",
        "mode": mode,
        "quality": quality,
        "format": format_type,
        "fps": fps,
        "bitrate": bitrate,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    history.insert(0, entry)
    if len(history) > 50:
        history = history[:50]
    save_history(history)
    return entry

# ===== GENERIC YT-DLP OPTIONS HELPER =====
def get_base_ydl_opts(extra_opts: Optional[Dict] = None) -> Dict[str, Any]:
    """Get base yt-dlp options with anti-detection measures and cookie support."""
    opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'ignoreerrors': False,
        'no_color': True,
        'socket_timeout': 30,
        'retries': 10,
        'fragment_retries': 10,
        'extractor_retries': 5,
        'file_access_retries': 5,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
        'referer': 'https://www.youtube.com/',
        'extractor_args': {
            'youtube': {
                'skip': ['dash', 'hls', 'webpage_download'],
                'player_skip': ['js', 'configs', 'webpage'],
                'player_client': ['android', 'web', 'ios'],
            }
        },
    }
    
    cookie_opts = get_yt_dlp_cookie_options()
    opts.update(cookie_opts)
    
    if extra_opts:
        opts.update(extra_opts)
    
    return opts

# ===== API ROUTES =====

@app.get("/")
async def root():
    """Serve the main HTML file"""
    index_file = BASE_DIR / "static" / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"error": "index.html not found"}, status_code=404)

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
    config['cookies_available'] = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0
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

@app.post("/api/history/delete")
async def delete_history_item(data: Dict[str, Any]):
    index = data.get("index")
    history = load_history()
    if index is None or not isinstance(index, int) or index < 0 or index >= len(history):
        raise HTTPException(status_code=404, detail="History item not found")
    item = history.pop(index)
    save_history(history)
    return JSONResponse({"status": "success", "message": "Item deleted"})

# ===== COOKIE UPLOAD ENDPOINTS =====
@app.get("/api/cookies/status")
async def get_cookie_status():
    exists = COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0
    size = COOKIES_FILE.stat().st_size if exists else 0
    return JSONResponse({"available": exists, "size": size})

@app.post("/api/cookies/upload")
async def upload_cookies(file: UploadFile = File(...)):
    try:
        content = await file.read()
        content_str = content.decode('utf-8', errors='ignore')
        is_valid = (
            content_str.strip().startswith('#') or 
            '.youtube.com' in content_str or
            'youtube' in content_str.lower()
        )
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid cookies file format. The file should be a Netscape-format cookies.txt file exported from your browser.")
        with open(COOKIES_FILE, 'wb') as f:
            f.write(content)
        return JSONResponse({"status": "success", "message": "Cookies uploaded successfully! YouTube authentication is now active."})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to upload cookies: {str(e)}")

@app.post("/api/cookies/delete")
async def delete_cookies():
    if COOKIES_FILE.exists():
        COOKIES_FILE.unlink()
        return JSONResponse({"status": "success", "message": "Cookies deleted."})
    return JSONResponse({"status": "success", "message": "No cookies to delete."})

# ===== VIDEO INFO =====
@app.post("/api/video-info")
async def get_video_info(request: VideoInfoRequest):
    try:
        ydl_opts = get_base_ydl_opts({'extract_flat': False})
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=False, process=True)
            
            if not info:
                raise HTTPException(status_code=400, detail="Could not extract video information.")
            
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
        
        if "HTTP Error 429" in error_msg or "Too Many Requests" in error_msg:
            error_msg = "Too many requests. Please wait a moment and try again."
        elif "HTTP Error 403" in error_msg or "Forbidden" in error_msg:
            error_msg = "Access denied. YouTube is blocking requests from this server."
        elif "HTTP Error 404" in error_msg:
            error_msg = "Video not found. Please check the URL and try again."
        elif "Private video" in error_msg:
            error_msg = "This video is private or unavailable."
        elif "not available" in error_msg.lower():
            error_msg = "Video not found or not available."
        elif "Sign in to confirm" in error_msg or "bot" in error_msg.lower():
            error_msg = "YouTube requires authentication. Please upload your YouTube cookies (Settings → Upload Cookies) using a cookies.txt file exported from your browser."
        elif "copyright" in error_msg.lower():
            error_msg = "This video may be blocked due to copyright restrictions."
        else:
            error_msg = f"Could not extract video information. {error_msg}"
        
        raise HTTPException(status_code=400, detail=error_msg)


# ===== DOWNLOAD (Stream to Browser) =====
@app.post("/api/download")
async def start_download(request: DownloadRequest):
    download_id = str(uuid.uuid4())
    
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
            "error": None,
            "filename": None,
            "download_url": None,
            "filesize": 0,
        }
    
    def download_thread():
        try:
            if request.mode == "video":
                result = download_video(download_id, request)
            else:
                result = download_audio(download_id, request)
            
            if result and "error" not in result:
                # File is ready in TEMP_DOWNLOADS - generate download URL
                with download_lock:
                    if download_id in active_downloads:
                        active_downloads[download_id]["status"] = "completed"
                        active_downloads[download_id]["progress"] = 100
                        active_downloads[download_id]["download_url"] = f"/api/download/{download_id}/file"
                        active_downloads[download_id]["filename"] = result.get("filename", "download")
        except Exception as e:
            with download_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["status"] = "error"
                    active_downloads[download_id]["error"] = str(e)
    
    thread = threading.Thread(target=download_thread, daemon=True)
    thread.start()
    
    return JSONResponse({"download_id": download_id, "status": "started"})

def download_video(download_id: str, request: DownloadRequest) -> Optional[Dict]:
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
        
        # Download to a temp ID-based filename to avoid path issues on Render
        temp_filename = f"{download_id}.%(ext)s"
        temp_path = str(DOWNLOADS_DIR / temp_filename)
        
        actual_filepath = [None]
        
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
                actual_filepath[0] = d.get('filename')
        
        ydl_opts = get_base_ydl_opts({
            'format': format_selector,
            'outtmpl': temp_path,
            'merge_output_format': fmt,
            'progress_hooks': [progress_hook],
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=True)
            title = info.get('title') or 'Unknown'
        
        # Find the actual downloaded file
        if actual_filepath[0]:
            dl_path = Path(actual_filepath[0])
        else:
            # Fallback: find by download_id prefix
            dl_path = None
            for f in DOWNLOADS_DIR.iterdir():
                if f.name.startswith(download_id) and f.is_file():
                    dl_path = f
                    break
        
        if dl_path and dl_path.exists():
            # Sanitize filename for browser download
            safe_title = re.sub(r'[^\w\s\-_()\[\]]', '', title).strip() or f"video_{download_id[:8]}"
            safe_filename = f"{safe_title}.{fmt}"
            filesize = dl_path.stat().st_size
            
            with TEMP_LOCK:
                TEMP_DOWNLOADS[download_id] = {
                    "path": str(dl_path),
                    "filename": safe_filename,
                    "title": title,
                    "mode": "video",
                    "filesize": filesize,
                    "created": time.time(),
                }
            
            with download_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["filename"] = safe_filename
                    active_downloads[download_id]["filesize"] = filesize
            
            add_to_history(title, "video", request.quality, fmt, fps=request.fps)
            
            return {"filename": safe_filename, "filesize": filesize}
        
        raise Exception("Downloaded file not found on server.")
        
    except Exception as e:
        with download_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "error"
                active_downloads[download_id]["error"] = str(e)
        return None

def download_audio(download_id: str, request: DownloadRequest) -> Optional[Dict]:
    try:
        with download_lock:
            active_downloads[download_id]["status"] = "downloading"
        
        audio_format = request.audio_format
        bitrate = request.audio_bitrate
        
        codecs = {
            "mp3": "libmp3lame", "m4a": "aac", "wav": "pcm_s16le",
            "flac": "flac", "ogg": "libvorbis", "opus": "libopus",
            "aac": "aac", "wma": "wmav2"
        }
        codec = codecs.get(audio_format, "libmp3lame")
        
        temp_filename = f"{download_id}.%(ext)s"
        temp_path = str(DOWNLOADS_DIR / temp_filename)
        
        actual_filepath = [None]
        
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
                actual_filepath[0] = d.get('filename')
        
        ydl_opts = get_base_ydl_opts({
            'format': 'bestaudio/best',
            'outtmpl': temp_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
            }],
            'postprocessor_args': ['-codec:a', codec, '-b:a', f'{bitrate}k'],
            'progress_hooks': [progress_hook],
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(request.url, download=True)
            title = info.get('title') or 'Unknown'
        
        # Find the actual downloaded file
        if actual_filepath[0]:
            dl_path = Path(actual_filepath[0])
        else:
            dl_path = None
            for f in DOWNLOADS_DIR.iterdir():
                if f.name.startswith(download_id) and f.is_file():
                    dl_path = f
                    break
        
        if dl_path and dl_path.exists():
            safe_title = re.sub(r'[^\w\s\-_()\[\]]', '', title).strip() or f"audio_{download_id[:8]}"
            safe_filename = f"{safe_title}.{audio_format}"
            filesize = dl_path.stat().st_size
            
            with TEMP_LOCK:
                TEMP_DOWNLOADS[download_id] = {
                    "path": str(dl_path),
                    "filename": safe_filename,
                    "title": title,
                    "mode": "audio",
                    "filesize": filesize,
                    "created": time.time(),
                }
            
            with download_lock:
                if download_id in active_downloads:
                    active_downloads[download_id]["filename"] = safe_filename
                    active_downloads[download_id]["filesize"] = filesize
            
            add_to_history(title, "audio", audio_format, audio_format, bitrate=f"{bitrate} kbps")
            
            return {"filename": safe_filename, "filesize": filesize}
        
        raise Exception("Downloaded file not found on server.")
        
    except Exception as e:
        with download_lock:
            if download_id in active_downloads:
                active_downloads[download_id]["status"] = "error"
                active_downloads[download_id]["error"] = str(e)
        return None


@app.get("/api/download/{download_id}/file")
async def download_file(download_id: str):
    """Stream the downloaded file to the client's browser."""
    with TEMP_LOCK:
        if download_id not in TEMP_DOWNLOADS:
            raise HTTPException(status_code=404, detail="Download file not found or expired")
        temp_info = TEMP_DOWNLOADS[download_id]
    
    file_path = Path(temp_info["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on server")
    
    filename = temp_info["filename"]
    filesize = file_path.stat().st_size
    
    def iterfile():
        with open(file_path, "rb") as f:
            yield from f
        # Clean up after serving
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
        with TEMP_LOCK:
            TEMP_DOWNLOADS.pop(download_id, None)
    
    return StreamingResponse(
        iterfile(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(filesize),
        }
    )


@app.get("/api/download/{download_id}/status")
async def get_download_status(download_id: str):
    with download_lock:
        if download_id not in active_downloads:
            raise HTTPException(status_code=404, detail="Download not found")
        status_data = dict(active_downloads[download_id])
        return JSONResponse(status_data)


# Cleanup task for expired temp files (runs every 5 minutes)
def cleanup_temp_files():
    while True:
        time.sleep(300)
        now = time.time()
        with TEMP_LOCK:
            expired = [did for did, info in TEMP_DOWNLOADS.items() if now - info["created"] > 600]
            for did in expired:
                try:
                    p = Path(TEMP_DOWNLOADS[did]["path"])
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
                TEMP_DOWNLOADS.pop(did, None)

cleanup_thread = threading.Thread(target=cleanup_temp_files, daemon=True)
cleanup_thread.start()


# Catch-all route for SPA - MUST BE LAST
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/"):
        return JSONResponse({"error": "Not found"}, status_code=404)
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
    print(f"Temp downloads dir: {DOWNLOADS_DIR}")
    print(f"Cookies: {'AVAILABLE' if COOKIES_FILE.exists() and COOKIES_FILE.stat().st_size > 0 else 'NOT UPLOADED'}")
    print("Downloads stream directly to client browser")
    print("=" * 50)
    
    try:
        uvicorn.run(app, host=host, port=port, log_level="info")
    except Exception as e:
        print(f"ERROR: Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
