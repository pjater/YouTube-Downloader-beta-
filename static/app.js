// ===== GLOBAL STATE =====
let currentMode = 'video';
let currentPage = 'downloader';
let config = {};
let history = [];
let currentDownloadId = null;
let pollingInterval = null;
let isDarkMode = true;

// ===== THEME MANAGEMENT =====
function initTheme() {
    const saved = localStorage.getItem('yt-dl-theme');
    isDarkMode = saved !== null ? saved === 'dark' : true;
    applyTheme();
}

function applyTheme() {
    const root = document.documentElement;
    if (isDarkMode) {
        root.style.setProperty('--bg-primary', '#0a0a0f');
        root.style.setProperty('--bg-secondary', '#111118');
        root.style.setProperty('--bg-card', '#16161d');
        root.style.setProperty('--bg-card-hover', '#1c1c25');
        root.style.setProperty('--bg-input', '#0d0d12');
        root.style.setProperty('--border-color', '#2a2a35');
        root.style.setProperty('--border-subtle', '#1f1f28');
        root.style.setProperty('--text-primary', '#ffffff');
        root.style.setProperty('--text-secondary', '#8b8b99');
        root.style.setProperty('--text-tertiary', '#6b6b78');
        document.querySelector('.theme-icon-sun').style.display = 'none';
        document.querySelector('.theme-icon-moon').style.display = '';
        document.getElementById('theme-label').textContent = 'Dark Mode';
    } else {
        root.style.setProperty('--bg-primary', '#f5f5f7');
        root.style.setProperty('--bg-secondary', '#ffffff');
        root.style.setProperty('--bg-card', '#ffffff');
        root.style.setProperty('--bg-card-hover', '#f0f0f2');
        root.style.setProperty('--bg-input', '#f5f5f7');
        root.style.setProperty('--border-color', '#d1d1d6');
        root.style.setProperty('--border-subtle', '#e5e5ea');
        root.style.setProperty('--text-primary', '#1c1c1e');
        root.style.setProperty('--text-secondary', '#636366');
        root.style.setProperty('--text-tertiary', '#aeaeb2');
        document.querySelector('.theme-icon-sun').style.display = '';
        document.querySelector('.theme-icon-moon').style.display = 'none';
        document.getElementById('theme-label').textContent = 'Light Mode';
    }
    localStorage.setItem('yt-dl-theme', isDarkMode ? 'dark' : 'light');
}

function toggleTheme() {
    isDarkMode = !isDarkMode;
    applyTheme();
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    await loadConfig();
    await loadHistory();
    updateUIFromConfig();
    renderRecentDownloads();
    
    // Setup event listeners
    setupEventListeners();
});

function setupEventListeners() {
    // Theme toggle
    document.getElementById('theme-toggle').addEventListener('click', toggleTheme);
    
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            showPage(page);
        });
    });
    
    // URL input
    const urlInput = document.getElementById('url-input');
    const clearBtn = document.getElementById('clear-url');
    const analyzeBtn = document.getElementById('analyze-btn');
    const pasteBtn = document.getElementById('paste-btn');
    
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            urlInput.value = text;
            urlInput.focus();
        } catch {
            alert('Could not access clipboard. Please paste manually (Ctrl+V).');
        }
    });
    
    clearBtn.addEventListener('click', () => {
        urlInput.value = '';
        urlInput.focus();
        document.getElementById('preview-card').style.display = 'none';
    });
    
    analyzeBtn.addEventListener('click', fetchVideoInfo);
    
    urlInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            fetchVideoInfo();
        }
    });
    
    // Mode tabs
    document.querySelectorAll('.segment').forEach(segment => {
        segment.addEventListener('click', () => {
            const mode = segment.dataset.mode;
            setMode(mode);
        });
    });
    
    // Download button
    document.getElementById('download-btn').addEventListener('click', startDownload);
    
    // View all history
    document.getElementById('view-all-history').addEventListener('click', () => {
        showPage('history');
    });
    
    // Refresh history
    document.getElementById('refresh-history').addEventListener('click', async () => {
        await loadHistory();
        renderRecentDownloads();
    });
    
    // Save settings
    document.getElementById('save-settings-btn').addEventListener('click', saveSettings);
}

// ===== API CALLS =====
async function apiCall(endpoint, method = 'GET', data = null) {
    try {
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json',
            }
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(endpoint, options);
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API error');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// ===== CONFIG MANAGEMENT =====
async function loadConfig() {
    try {
        config = await apiCall('/api/config');
    } catch (error) {
        console.error('Failed to load config:', error);
        config = getDefaultConfig();
    }
}

function getDefaultConfig() {
    return {
        default_video_quality: 'best',
        default_video_format: 'mp4',
        default_fps: '30',
        default_audio_bitrate: '192',
        default_audio_format: 'mp3',
        last_used: {
            video_quality: '1080p',
            video_format: 'mp4',
            fps: '60',
            audio_bitrate: '192',
            audio_format: 'mp3'
        }
    };
}

function updateUIFromConfig() {
    // Settings page
    document.getElementById('setting-vquality').value = config.default_video_quality || 'best';
    document.getElementById('setting-vformat').value = config.default_video_format || 'mp4';
    document.getElementById('setting-fps').value = config.default_fps || '30';
    document.getElementById('setting-abitrate').value = config.default_audio_bitrate || '192';
    document.getElementById('setting-aformat').value = config.default_audio_format || 'mp3';
    
    // Downloader page - apply last used or defaults
    const lastUsed = config.last_used || {};
    document.getElementById('video-quality').value = lastUsed.video_quality || config.default_video_quality || 'best';
    document.getElementById('video-format').value = lastUsed.video_format || config.default_video_format || 'mp4';
    document.getElementById('fps-select').value = lastUsed.fps || config.default_fps || '30';
    document.getElementById('audio-bitrate').value = lastUsed.audio_bitrate || config.default_audio_bitrate || '192';
    document.getElementById('audio-format').value = lastUsed.audio_format || config.default_audio_format || 'mp3';
}

async function saveSettings() {
    try {
        const settings = {
            default_video_quality: document.getElementById('setting-vquality').value,
            default_video_format: document.getElementById('setting-vformat').value,
            default_fps: document.getElementById('setting-fps').value,
            default_audio_bitrate: document.getElementById('setting-abitrate').value,
            default_audio_format: document.getElementById('setting-aformat').value
        };
        
        await apiCall('/api/config', 'POST', settings);
        
        // Update local config
        config = { ...config, ...settings };
        
        // Show confirmation
        const saveBtn = document.getElementById('save-settings-btn');
        const confirmation = document.getElementById('save-confirmation');
        
        saveBtn.style.display = 'none';
        confirmation.style.display = 'flex';
        
        setTimeout(() => {
            saveBtn.style.display = 'flex';
            confirmation.style.display = 'none';
        }, 2000);
        
    } catch (error) {
        alert('Failed to save settings: ' + error.message);
    }
}

// ===== HISTORY MANAGEMENT =====
async function loadHistory() {
    try {
        history = await apiCall('/api/history');
    } catch (error) {
        console.error('Failed to load history:', error);
        history = [];
    }
}

async function deleteHistoryItem(index) {
    if (!confirm('Are you sure you want to delete this download from history?')) {
        return;
    }
    
    try {
        const result = await apiCall('/api/history/delete', 'POST', { index });
        await loadHistory();
        renderRecentDownloads();
        if (currentPage === 'history') {
            renderHistoryPage();
        }
    } catch (error) {
        console.error('Delete error:', error);
        alert('Failed to delete: ' + error.message);
    }
}

function renderRecentDownloads() {
    const container = document.getElementById('recent-downloads');
    
    if (!history || history.length === 0) {
        container.innerHTML = `
            <div class="history-empty">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                </svg>
                <p>No downloads yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = history.slice(0, 10).map((item, index) => {
        const title = item.title.length > 30 ? item.title.substring(0, 30) + '...' : item.title;
        const mode = item.mode === 'video' ? 'Video' : 'Audio';
        let details = `${mode} • ${item.format}`;
        if (item.fps && item.mode === 'video') {
            details += ` • ${item.fps} FPS`;
        }
        if (item.bitrate && item.mode === 'audio') {
            details += ` • ${item.bitrate}`;
        }
        
        const thumbnail = `https://img.youtube.com/vi/${extractVideoIdFromTitle(item.title)}/hqdefault.jpg`;
        
        return `
            <div class="download-item">
                <div class="download-thumbnail">
                    <img src="${thumbnail}" alt="thumbnail" onerror="this.style.display='none'">
                </div>
                <div class="download-info">
                    <div class="download-title">${escapeHtml(title)}</div>
                    <div class="download-meta">${details}</div>
                    <div class="download-status">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"/>
                        </svg>
                        <span>Completed</span>
                    </div>
                </div>
                <div class="download-actions">
                    <button class="action-btn delete-btn" onclick="deleteHistoryItem(${index})" title="Delete">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function renderHistoryPage() {
    const container = document.getElementById('history-list');
    
    if (!history || history.length === 0) {
        container.innerHTML = `
            <div class="history-empty">
                <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <polyline points="12 6 12 12 16 14"/>
                </svg>
                <p>No downloads yet</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = history.map((item, index) => {
        const title = item.title.length > 50 ? item.title.substring(0, 50) + '...' : item.title;
        const mode = item.mode === 'video' ? 'Video' : 'Audio';
        let details = `${mode} • ${item.format}`;
        if (item.fps && item.mode === 'video') {
            details += ` • ${item.fps} FPS`;
        }
        if (item.bitrate && item.mode === 'audio') {
            details += ` • ${item.bitrate}`;
        }
        
        return `
            <div class="history-item">
                <div class="download-info">
                    <div class="download-title">${escapeHtml(title)}</div>
                    <div class="download-meta">${details}</div>
                    <div class="download-status">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="20 6 9 17 4 12"/>
                        </svg>
                        <span>Completed • ${item.timestamp}</span>
                    </div>
                </div>
                <div class="download-actions">
                    <button class="action-btn delete-btn" onclick="deleteHistoryItem(${index})" title="Delete">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="3 6 5 6 21 6"/>
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

// Helper to extract video ID from history (best effort)
function extractVideoIdFromTitle(title) {
    // We don't store video IDs, so use a generic approach
    return '';
}

// ===== NAVIGATION =====
function showPage(page) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    
    const pageEl = document.getElementById(`${page}-page`);
    if (pageEl) {
        pageEl.classList.add('active');
    }
    
    document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
    document.querySelector(`[data-page="${page}"]`)?.classList.add('active');
    
    currentPage = page;
    
    if (page === 'history') {
        loadHistory().then(() => {
            renderHistoryPage();
        });
    }
    
    if (page === 'downloader') {
        loadHistory().then(() => {
            renderRecentDownloads();
        });
    }
}

// ===== MODE SWITCHING =====
function setMode(mode) {
    currentMode = mode;
    
    const videoTab = document.querySelector('[data-mode="video"]');
    const audioTab = document.querySelector('[data-mode="audio"]');
    
    const videoOptions = document.querySelectorAll('#format-option, #resolution-option, #codec-option, #fps-option');
    const audioOptions = document.querySelectorAll('.audio-only');
    
    if (mode === 'video') {
        videoTab.classList.add('active');
        audioTab.classList.remove('active');
        
        videoOptions.forEach(opt => opt.style.display = 'flex');
        audioOptions.forEach(opt => opt.style.display = 'none');
    } else {
        audioTab.classList.add('active');
        videoTab.classList.remove('active');
        
        videoOptions.forEach(opt => opt.style.display = 'none');
        audioOptions.forEach(opt => opt.style.display = 'flex');
    }
}

// ===== VIDEO INFO =====
async function fetchVideoInfo() {
    const url = document.getElementById('url-input').value.trim();
    const previewCard = document.getElementById('preview-card');
    
    if (!url) {
        alert('Please enter a YouTube URL first.');
        return;
    }
    
    const analyzeBtn = document.getElementById('analyze-btn');
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span>Analyzing...</span>';
    
    try {
        const info = await apiCall('/api/video-info', 'POST', { url });
        
        const thumbnail = info.thumbnail || `https://img.youtube.com/vi/${extractVideoId(url)}/hqdefault.jpg`;
        document.getElementById('video-thumbnail').src = thumbnail;
        document.getElementById('video-title').textContent = info.title;
        document.getElementById('video-uploader').textContent = info.uploader;
        document.getElementById('video-views').textContent = formatViews(info.view_count);
        document.getElementById('video-duration').textContent = info.duration;
        document.getElementById('video-duration-meta').textContent = info.duration;
        
        const date = new Date();
        document.getElementById('video-date').textContent = date.toLocaleDateString('en-US', { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
        
        previewCard.style.display = 'block';
        
        document.getElementById('status-text').textContent = 'VIDEO ANALYZED';
        document.getElementById('status-info').textContent = `Best quality: ${info.best_quality}`;
        
    } catch (error) {
        alert('Failed to fetch video info: ' + error.message);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = `
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
            </svg>
            <span>Analyze</span>
        `;
    }
}

function extractVideoId(url) {
    const patterns = [
        /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)/,
        /youtube\.com\/watch\?.*v=([^&\n?#]+)/
    ];
    for (const pattern of patterns) {
        const match = url.match(pattern);
        if (match) return match[1];
    }
    return '';
}

function formatViews(views) {
    if (!views) return '0 views';
    if (views >= 1000000000) {
        return (views / 1000000000).toFixed(1) + 'B views';
    } else if (views >= 1000000) {
        return (views / 1000000).toFixed(1) + 'M views';
    } else if (views >= 1000) {
        return (views / 1000).toFixed(1) + 'K views';
    }
    return views + ' views';
}

// ===== DOWNLOAD MANAGEMENT =====
async function startDownload() {
    const url = document.getElementById('url-input').value.trim();
    
    if (!url) {
        alert('Please enter a YouTube URL first.');
        return;
    }
    
    // Show overlay
    const overlay = document.getElementById('download-overlay');
    overlay.style.display = 'flex';
    overlay.classList.add('active');
    
    // Reset overlay state
    document.getElementById('overlay-title').textContent = 'Downloading...';
    document.getElementById('overlay-info').textContent = 'Preparing your download on the server';
    document.getElementById('overlay-progress-fill').style.width = '0%';
    document.getElementById('overlay-progress-text').textContent = '0%';
    document.getElementById('overlay-details').style.display = 'none';
    overlay.classList.remove('success');
    
    try {
        const request = {
            url: url,
            mode: currentMode,
            quality: document.getElementById('video-quality').value,
            format: document.getElementById('video-format').value,
            fps: document.getElementById('fps-select').value,
            audio_format: document.getElementById('audio-format').value,
            audio_bitrate: document.getElementById('audio-bitrate').value,
        };
        
        const response = await apiCall('/api/download', 'POST', request);
        currentDownloadId = response.download_id;
        
        // Start polling for status
        startStatusPolling();
        
    } catch (error) {
        alert('Failed to start download: ' + error.message);
        hideOverlay();
    }
}

function startStatusPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
    
    pollingInterval = setInterval(async () => {
        if (!currentDownloadId) {
            clearInterval(pollingInterval);
            return;
        }
        
        try {
            const status = await apiCall(`/api/download/${currentDownloadId}/status`);
            updateOverlayProgress(status);
            
            if (status.status === 'completed' || status.status === 'error') {
                clearInterval(pollingInterval);
                
                if (status.status === 'completed') {
                    // Trigger browser download!
                    if (status.download_url) {
                        triggerBrowserDownload(status.download_url, status.filename);
                    }
                    
                    showSuccessState();
                    
                    await loadHistory();
                    renderRecentDownloads();
                    
                    setTimeout(() => {
                        hideOverlay();
                    }, 2000);
                }
                
                if (status.status === 'error') {
                    alert('Download failed: ' + status.error);
                    hideOverlay();
                }
            }
        } catch (error) {
            console.error('Failed to get download status:', error);
        }
    }, 500);
}

function triggerBrowserDownload(downloadUrl, filename) {
    // Create a temporary link element and click it to trigger browser download
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    
    // Clean up
    setTimeout(() => {
        document.body.removeChild(link);
    }, 1000);
}

function updateOverlayProgress(status) {
    const overlay = document.getElementById('download-overlay');
    const title = document.getElementById('overlay-title');
    const info = document.getElementById('overlay-info');
    const progressFill = document.getElementById('overlay-progress-fill');
    const progressText = document.getElementById('overlay-progress-text');
    const details = document.getElementById('overlay-details');
    const speedEl = document.getElementById('overlay-speed');
    const etaEl = document.getElementById('overlay-eta');
    
    if (status.status === 'preparing') {
        title.textContent = 'Downloading...';
        info.textContent = 'Preparing your download on the server';
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
        details.style.display = 'none';
    } else if (status.status === 'downloading') {
        const progress = status.progress || 0;
        const speed = status.speed ? `${(status.speed / 1024 / 1024).toFixed(1)} MB/s` : '?';
        const eta = status.eta ? `${status.eta}s` : '?';
        
        title.textContent = 'Downloading to server...';
        info.textContent = 'Downloading from YouTube to server';
        progressFill.style.width = `${progress}%`;
        progressText.textContent = `${progress}%`;
        details.style.display = 'flex';
        speedEl.textContent = speed;
        etaEl.textContent = eta;
    } else if (status.status === 'converting') {
        title.textContent = 'Processing...';
        info.textContent = 'Converting your file on server';
        progressFill.style.width = '95%';
        progressText.textContent = '95%';
        details.style.display = 'flex';
        speedEl.textContent = '-';
        etaEl.textContent = '-';
    }
}

function showSuccessState() {
    const overlay = document.getElementById('download-overlay');
    const title = document.getElementById('overlay-title');
    const info = document.getElementById('overlay-info');
    const progressFill = document.getElementById('overlay-progress-fill');
    const progressText = document.getElementById('overlay-progress-text');
    
    overlay.classList.add('success');
    title.textContent = 'Download Complete!';
    info.textContent = 'Your file is being downloaded to your browser';
    progressFill.style.width = '100%';
    progressText.textContent = '100%';
}

function hideOverlay() {
    const overlay = document.getElementById('download-overlay');
    overlay.classList.remove('active');
    setTimeout(() => {
        overlay.style.display = 'none';
    }, 300);
}

// ===== UTILITY FUNCTIONS =====
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== COOKIE MANAGEMENT =====
async function checkCookieStatus() {
    try {
        const status = await apiCall('/api/cookies/status');
        updateCookieUI(status.available);
        return status.available;
    } catch (error) {
        console.error('Failed to check cookie status:', error);
        const statusEl = document.getElementById('cookie-status');
        if (statusEl) {
            statusEl.className = 'cookie-status error';
            statusEl.innerHTML = `
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                </svg>
                <span>Could not check status</span>
            `;
        }
        return false;
    }
}

function updateCookieUI(available) {
    const statusEl = document.getElementById('cookie-status');
    const actionsEl = document.getElementById('cookie-actions');
    
    if (!statusEl) return;
    
    if (available) {
        statusEl.className = 'cookie-status uploaded';
        statusEl.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span>Cookies are active ✓ YouTube authentication is working</span>
        `;
        if (actionsEl) actionsEl.style.display = 'flex';
        const submitBtn = document.getElementById('cookie-submit-btn');
        const deleteBtn = document.getElementById('cookie-delete-btn');
        if (submitBtn) submitBtn.style.display = 'none';
        if (deleteBtn) deleteBtn.style.display = 'flex';
    } else {
        statusEl.className = 'cookie-status not-uploaded';
        statusEl.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/>
                <line x1="15" y1="9" x2="9" y2="15"/>
                <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <span>No cookies uploaded - YouTube may block downloads</span>
        `;
        if (actionsEl) actionsEl.style.display = 'flex';
        const submitBtn = document.getElementById('cookie-submit-btn');
        const deleteBtn = document.getElementById('cookie-delete-btn');
        if (submitBtn) submitBtn.style.display = 'flex';
        if (deleteBtn) deleteBtn.style.display = 'none';
    }
}

// Setup cookie file input listener
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        const fileInput = document.getElementById('cookie-file-input');
        if (fileInput) {
            fileInput.addEventListener('change', function() {
                const fileNameEl = document.getElementById('cookie-file-name');
                const actionsEl = document.getElementById('cookie-actions');
                if (this.files && this.files.length > 0) {
                    fileNameEl.textContent = this.files[0].name;
                    if (actionsEl) actionsEl.style.display = 'flex';
                    const submitBtn = document.getElementById('cookie-submit-btn');
                    const deleteBtn = document.getElementById('cookie-delete-btn');
                    if (submitBtn) submitBtn.style.display = 'flex';
                    if (deleteBtn) deleteBtn.style.display = 'none';
                } else {
                    fileNameEl.textContent = 'No file selected';
                }
            });
        }
        
        checkCookieStatus();
    }, 100);
});

async function uploadCookies() {
    const fileInput = document.getElementById('cookie-file-input');
    const submitBtn = document.getElementById('cookie-submit-btn');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        alert('Please select a cookies.txt file first.');
        return;
    }
    
    const file = fileInput.files[0];
    
    if (!file.name.endsWith('.txt')) {
        alert('Please select a .txt file (Netscape format cookies file).');
        return;
    }
    
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span>Uploading...</span>';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/cookies/upload', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Upload failed');
        }
        
        updateCookieUI(true);
        
        fileInput.value = '';
        document.getElementById('cookie-file-name').textContent = 'No file selected';
        
        alert('Cookies uploaded successfully! YouTube authentication is now active.');
        
    } catch (error) {
        alert('Failed to upload cookies: ' + error.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>Upload Cookies</span>
        `;
    }
}

async function deleteCookies() {
    if (!confirm('Are you sure you want to delete the uploaded cookies?')) {
        return;
    }
    
    try {
        await apiCall('/api/cookies/delete', 'POST');
        updateCookieUI(false);
        alert('Cookies deleted successfully.');
    } catch (error) {
        alert('Failed to delete cookies: ' + error.message);
    }
}

// ===== PERIODIC REFRESH =====
setInterval(async () => {
    if (currentPage === 'downloader') {
        await loadHistory();
        renderRecentDownloads();
    }
}, 30000);
