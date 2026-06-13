from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from datetime import datetime
import os
import json
from dotenv import load_dotenv
import threading
import time
import requests
from contextlib import asynccontextmanager
import base64

load_dotenv()

# =========================================================
# CONFIGURATION
# =========================================================
MONGODB_URI = os.environ.get("MONGODBEMAIL_URI", "")
DATABASE_NAME = "swing_trading_db"
COLLECTION_NAME = "strong_ratio_signals"

# Create static directory
os.makedirs("static", exist_ok=True)

# =========================================================
# CREATE STATIC FILES
# =========================================================

# 1. manifest.json
MANIFEST_JSON = {
    "name": "Strong Ratio Signals Dashboard",
    "short_name": "Strong Ratio",
    "description": "Real-time MongoDB dashboard for strong ratio signals",
    "start_url": "/",
    "display": "standalone",
    "theme_color": "#667eea",
    "background_color": "#ffffff",
    "orientation": "portrait-primary",
    "scope": "/",
    "lang": "en",
    "icons": [
        {
            "src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='192' height='192' viewBox='0 0 192 192'%3E%3Crect width='192' height='192' fill='%23667eea'/%3E%3Ccircle cx='96' cy='96' r='76.8' fill='%23764ba2'/%3E%3Ctext x='96' y='120' font-size='64' text-anchor='middle' fill='white' font-family='Arial' font-weight='bold'%3ESR%3C/text%3E%3C/svg%3E",
            "sizes": "192x192",
            "type": "image/svg+xml",
            "purpose": "any maskable"
        },
        {
            "src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='512' height='512' viewBox='0 0 512 512'%3E%3Crect width='512' height='512' fill='%23667eea'/%3E%3Ccircle cx='256' cy='256' r='204.8' fill='%23764ba2'/%3E%3Ctext x='256' y='320' font-size='170' text-anchor='middle' fill='white' font-family='Arial' font-weight='bold'%3ESR%3C/text%3E%3C/svg%3E",
            "sizes": "512x512",
            "type": "image/svg+xml",
            "purpose": "any maskable"
        }
    ],
    "shortcuts": [
        {
            "name": "Dashboard",
            "short_name": "Home",
            "description": "View main dashboard",
            "url": "/",
            "icons": [{"src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='192' height='192' viewBox='0 0 192 192'%3E%3Crect width='192' height='192' fill='%23667eea'/%3E%3Ctext x='96' y='120' font-size='64' text-anchor='middle' fill='white'%3ESR%3C/text%3E%3C/svg%3E", "sizes": "192x192"}]
        }
    ]
}

# 2. Service Worker (sw.js)
SERVICE_WORKER_JS = '''// Strong Ratio Dashboard Service Worker
const CACHE_NAME = 'strong-ratio-v1.0.0';
const STATIC_ASSETS = [
    '/',
    '/static/offline.html',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css',
    'https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css',
    'https://code.jquery.com/jquery-3.6.0.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
    'https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js',
    'https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js',
    'https://cdn.jsdelivr.net/npm/sweetalert2@11'
];

self.addEventListener('install', event => {
    console.log('[SW] Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('[SW] Caching static assets');
            return cache.addAll(STATIC_ASSETS);
        }).then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    console.log('[SW] Activating...');
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(keys.map(key => {
                if (key !== CACHE_NAME) {
                    console.log('[SW] Deleting old cache:', key);
                    return caches.delete(key);
                }
            }));
        }).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const url = new URL(event.request.url);
    
    if (event.request.method !== 'GET') {
        event.respondWith(fetch(event.request));
        return;
    }
    
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(event.request).catch(() => {
                return new Response(JSON.stringify({error: 'Offline - API unavailable'}), {
                    headers: {'Content-Type': 'application/json'}
                });
            })
        );
        return;
    }
    
    event.respondWith(
        caches.match(event.request).then(cached => {
            return cached || fetch(event.request).then(response => {
                const responseToCache = response.clone();
                caches.open(CACHE_NAME).then(cache => {
                    cache.put(event.request, responseToCache);
                });
                return response;
            });
        }).catch(() => {
            if (url.pathname === '/' || url.pathname === '/index.html') {
                return caches.match('/static/offline.html');
            }
            return new Response('Offline - Page not cached', {status: 404});
        })
    );
});

self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {title: 'Strong Ratio', body: 'Data updated!'};
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192"%3E%3Crect width="192" height="192" fill="%23667eea"/%3E%3Ctext x="96" y="120" font-size="64" text-anchor="middle" fill="white"%3ESR%3C/text%3E%3C/svg%3E',
            badge: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="72" height="72" viewBox="0 0 72 72"%3E%3Crect width="72" height="72" fill="%23667eea"/%3E%3Ctext x="36" y="48" font-size="24" text-anchor="middle" fill="white"%3ESR%3C/text%3E%3C/svg%3E',
            vibrate: [200, 100, 200],
            actions: [{action: 'open', title: 'Open Dashboard'}]
        })
    );
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    event.waitUntil(clients.openWindow('/'));
});
'''

# 3. Offline HTML
OFFLINE_HTML = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#667eea">
    <title>Offline - Strong Ratio Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            padding: 20px;
        }
        .container {
            background: white;
            border-radius: 30px;
            padding: 50px 40px;
            text-align: center;
            max-width: 500px;
            width: 100%;
            box-shadow: 0 30px 60px rgba(0,0,0,0.3);
            animation: slideIn 0.5s ease;
        }
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .icon { font-size: 80px; margin-bottom: 20px; }
        h1 { color: #667eea; margin-bottom: 10px; font-size: 1.8em; }
        .subtitle { color: #764ba2; margin-bottom: 30px; }
        .message-box {
            background: #f8f9fa;
            border-radius: 15px;
            padding: 20px;
            margin: 20px 0;
            border-left: 4px solid #667eea;
        }
        .message-box p { color: #666; margin: 5px 0; }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            margin-top: 20px;
            transition: transform 0.3s;
        }
        button:hover { transform: translateY(-2px); }
        .countdown {
            margin-top: 20px;
            font-size: 14px;
            color: #667eea;
        }
        .timer { font-weight: bold; font-size: 18px; }
        @media (max-width: 480px) {
            .container { padding: 30px 20px; }
            h1 { font-size: 1.4em; }
            .icon { font-size: 60px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">📡</div>
        <h1>You're Offline</h1>
        <div class="subtitle">Connection Lost</div>
        <div class="message-box">
            <p>⚠️ Unable to connect to the server</p>
            <p>Please check your internet connection</p>
        </div>
        <button onclick="retry()">🔄 Retry Now</button>
        <div class="countdown">
            Auto-retry in <span class="timer" id="timer">5</span> seconds
        </div>
    </div>
    <script>
        let countdown = 5;
        function startCountdown() {
            const timer = setInterval(() => {
                countdown--;
                document.getElementById('timer').textContent = countdown;
                if (countdown <= 0) {
                    clearInterval(timer);
                    retry();
                }
            }, 1000);
        }
        function retry() {
            if (navigator.onLine) {
                window.location.reload();
            } else {
                countdown = 5;
                document.getElementById('timer').textContent = countdown;
                startCountdown();
            }
        }
        startCountdown();
        window.addEventListener('online', () => window.location.reload());
    </script>
</body>
</html>'''

def create_static_files():
    """Create all static files"""
    # Create manifest.json
    with open("static/manifest.json", "w") as f:
        json.dump(MANIFEST_JSON, f, indent=2)
    print("✅ Created static/manifest.json")
    
    # Create sw.js
    with open("static/sw.js", "w") as f:
        f.write(SERVICE_WORKER_JS)
    print("✅ Created static/sw.js")
    
    # Create offline.html
    with open("static/offline.html", "w") as f:
        f.write(OFFLINE_HTML)
    print("✅ Created static/offline.html")

# Create static files
create_static_files()

# =========================================================
# MONGODB CONNECTION
# =========================================================
def get_db():
    """Get MongoDB database connection"""
    if not MONGODB_URI:
        print("❌ MONGODBEMAIL_URI not set!")
        return None
    
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        print("✅ MongoDB Connected")
        return client[DATABASE_NAME]
    except Exception as e:
        print(f"❌ MongoDB Error: {e}")
        return None

# =========================================================
# HTML TEMPLATE
# =========================================================
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#667eea">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <meta name="apple-mobile-web-app-title" content="Strong Ratio">
    <link rel="manifest" href="/static/manifest.json">
    <link rel="apple-touch-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='192' height='192' viewBox='0 0 192 192'%3E%3Crect width='192' height='192' fill='%23667eea'/%3E%3Ctext x='96' y='120' font-size='64' text-anchor='middle' fill='white'%3ESR%3C/text%3E%3C/svg%3E">
    <title>Strong Ratio Signals Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .container-main {
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.1);
            padding: 30px;
            animation: fadeIn 0.5s ease;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }
        .header h1 { color: #333; font-weight: bold; font-size: 2.2em; }
        .header p { color: #666; }
        .btn-install {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 30px;
            border-radius: 25px;
            font-weight: bold;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .btn-install:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102,126,234,0.4); color: white; }
        .btn-refresh {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            padding: 10px 30px;
            border-radius: 25px;
            font-weight: bold;
            margin-left: 10px;
            transition: all 0.3s;
        }
        .btn-refresh:hover { transform: translateY(-2px); color: white; }
        .stats-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
        }
        .stats-card:hover { transform: translateY(-5px); }
        .stats-card h3 { font-size: 32px; font-weight: bold; margin: 0; }
        .stats-card p { margin: 10px 0 0; opacity: 0.9; }
        .table-container { overflow-x: auto; margin-top: 30px; }
        #dataTable { font-size: 14px; }
        #dataTable th { background: #667eea; color: white; padding: 12px; text-align: center; }
        #dataTable td { text-align: center; vertical-align: middle; padding: 10px; }
        .btn-delete {
            background: #dc3545; color: white; border: none; padding: 5px 12px;
            border-radius: 5px; cursor: pointer; transition: all 0.3s;
        }
        .btn-delete:hover { background: #c82333; transform: scale(1.05); }
        .btn-delete-date {
            background: #ffc107; color: #333; border: none; padding: 5px 12px;
            border-radius: 5px; cursor: pointer; margin-left: 5px; transition: all 0.3s;
        }
        .btn-delete-date:hover { background: #e0a800; transform: scale(1.05); }
        .badge-bullish { background: #28a745; color: white; padding: 5px 10px; border-radius: 5px; font-weight: 600; }
        .badge-bearish { background: #dc3545; color: white; padding: 5px 10px; border-radius: 5px; font-weight: 600; }
        .badge-neutral { background: #ffc107; color: #333; padding: 5px 10px; border-radius: 5px; font-weight: 600; }
        .footer { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }
        .status-badge { display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: #28a745; margin-right: 8px; animation: pulse 2s infinite; }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(40,167,69,0.7); }
            70% { box-shadow: 0 0 0 10px rgba(40,167,69,0); }
            100% { box-shadow: 0 0 0 0 rgba(40,167,69,0); }
        }
        @media (max-width: 768px) {
            .container-main { padding: 15px; }
            .header h1 { font-size: 1.5em; }
            #dataTable { font-size: 11px; }
            .stats-card h3 { font-size: 24px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="container-main">
            <div class="header">
                <h1>📊 Strong Ratio Signals Dashboard</h1>
                <p>FastAPI + MongoDB | Real-time Data | PWA Ready</p>
                <div><span class="status-badge"></span> <small>Live Connection</small></div>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="stats-card"><p>📈 Total Records</p><h3 id="totalRecords">0</h3></div>
                </div>
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="stats-card"><p>📅 Unique Dates</p><h3 id="uniqueDates">0</h3></div>
                </div>
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="stats-card"><p>🎯 Avg Bullish Prob</p><h3 id="avgBullish">0%</h3></div>
                </div>
                <div class="col-md-3 col-sm-6 mb-3">
                    <div class="stats-card"><p>🕐 Last Update</p><h3 id="lastUpdate">-</h3></div>
                </div>
            </div>
            
            <div class="text-center">
                <button class="btn-install" id="installBtn" style="display:none;">📱 Install App</button>
                <button class="btn-refresh" onclick="refreshData()">🔄 Refresh Data</button>
            </div>
            
            <div class="table-container">
                <table id="dataTable" class="table table-bordered table-hover">
                    <thead>
                        <tr><th>No</th><th>Date</th><th>RT</th><th>BBR</th><th>Strong</th><th>Strong Ratio</th><th>Bullish Prob</th><th>Actions</th></tr>
                    </thead>
                    <tbody><tr><td colspan="8" class="text-center"><div class="spinner-border text-primary"></div><br>Loading...</td></tr></tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>🚀 FastAPI + MongoDB | 📡 Auto-sync | 💾 PWA Enabled | 🔄 Auto-refresh every 3 min</p>
                <small>Last refresh: <span id="refreshTime">-</span></small>
            </div>
        </div>
    </div>
    
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    
    <script>
        let dataTable, deferredPrompt;
        
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(reg => console.log('SW registered:', reg))
                .catch(err => console.log('SW failed:', err));
        }
        
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            document.getElementById('installBtn').style.display = 'inline-block';
            document.getElementById('installBtn').onclick = async () => {
                if (deferredPrompt) {
                    deferredPrompt.prompt();
                    const { outcome } = await deferredPrompt.userChoice;
                    deferredPrompt = null;
                    document.getElementById('installBtn').style.display = 'none';
                }
            };
        });
        
        function refreshData() { loadData(); }
        
        function loadData() {
            $.ajax({
                url: '/api/data',
                method: 'GET',
                timeout: 30000,
                success: function(data) {
                    if (data.error) { showError(data.error); return; }
                    updateStats(data);
                    renderTable(data);
                    document.getElementById('refreshTime').innerText = new Date().toLocaleTimeString();
                },
                error: function() { showError('Failed to load data'); }
            });
        }
        
        function updateStats(data) {
            document.getElementById('totalRecords').innerText = data.length;
            const uniqueDates = [...new Set(data.map(d => d.date).filter(d => d))];
            document.getElementById('uniqueDates').innerText = uniqueDates.length;
            let total = 0, count = 0;
            data.forEach(d => {
                if (d.bullish_probability) {
                    let p = parseFloat(d.bullish_probability);
                    if (!isNaN(p)) { total += p; count++; }
                }
            });
            let avg = count > 0 ? (total / count).toFixed(1) : 0;
            document.getElementById('avgBullish').innerText = avg + '%';
            if (data.length > 0) document.getElementById('lastUpdate').innerText = data[0].date || '-';
        }
        
        function renderTable(data) {
            const tbody = $('#dataTable tbody');
            tbody.empty();
            if (data.length === 0) {
                tbody.html('<tr><td colspan="8" class="text-center">No data available</td></tr>');
                if (dataTable) dataTable.destroy();
                return;
            }
            data.sort((a,b) => (b.date || '').localeCompare(a.date || ''));
            data.forEach((item, idx) => item.no = idx + 1);
            data.forEach(item => {
                let probHtml = '<span class="badge-neutral">N/A</span>';
                if (item.bullish_probability && item.bullish_probability !== 'N/A') {
                    let pv = parseFloat(item.bullish_probability);
                    let probClass = pv >= 60 ? 'badge-bearish' : (pv >= 45 ? 'badge-neutral' : 'badge-bullish');
                    probHtml = `<span class="${probClass}">${item.bullish_probability}</span>`;
                }
                let strongRatio = item.strong_ratio ? parseFloat(item.strong_ratio).toFixed(2) : '-';
                let row = `<tr>
                    <td><strong>${item.no}</strong></td>
                    <td><strong class="text-primary">${item.date || '-'}</strong></td>
                    <td><code>${item.rt || '-'}</code></td>
                    <td>${item.bbr || '-'}</td>
                    <td style="max-width:150px; overflow:hidden; text-overflow:ellipsis;">${item.strong || '-'}</td>
                    <td>${strongRatio}</td>
                    <td>${probHtml}</td>
                    <td>
                        <button class="btn-delete" onclick="deleteRecord('${item.date}', '${item.rt}')">🗑️ Delete</button>
                        <button class="btn-delete-date" onclick="deleteDate('${item.date}')">📅 Delete Date</button>
                    </td>
                </tr>`;
                tbody.append(row);
            });
            if (dataTable) dataTable.destroy();
            dataTable = $('#dataTable').DataTable({
                pageLength: 25,
                responsive: true,
                order: [[1, 'desc']],
                columnDefs: [{ orderable: false, targets: [7] }]
            });
        }
        
        function deleteRecord(date, rt) {
            Swal.fire({
                title: 'Confirm Delete',
                html: `Delete <strong>${rt}</strong> on <strong>${date}</strong>?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                confirmButtonText: 'Delete'
            }).then(result => {
                if (result.isConfirmed) {
                    $.ajax({
                        url: `/api/delete/${encodeURIComponent(date)}/${encodeURIComponent(rt)}`,
                        method: 'DELETE',
                        success: res => { Swal.fire('Deleted!', res.message, 'success'); loadData(); },
                        error: () => Swal.fire('Error!', 'Delete failed', 'error')
                    });
                }
            });
        }
        
        function deleteDate(date) {
            Swal.fire({
                title: 'Delete All Records?',
                html: `Delete ALL records for <strong>${date}</strong>?<br><small>This cannot be undone!</small>`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                confirmButtonText: 'Delete All'
            }).then(result => {
                if (result.isConfirmed) {
                    $.ajax({
                        url: `/api/delete/${encodeURIComponent(date)}`,
                        method: 'DELETE',
                        success: res => { Swal.fire('Deleted!', res.message, 'success'); loadData(); },
                        error: () => Swal.fire('Error!', 'Delete failed', 'error')
                    });
                }
            });
        }
        
        function showError(msg) { Swal.fire('Error', msg, 'error'); }
        
        $(document).ready(() => { loadData(); setInterval(loadData, 180000); });
    </script>
</body>
</html>'''

# =========================================================
# FASTAPI APP
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🚀 Strong Ratio Dashboard Starting...")
    print("=" * 60)
    yield
    print("🛑 Shutting down...")

app = FastAPI(title="Strong Ratio Dashboard", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# =========================================================
# API ROUTES
# =========================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.get("/api/data")
async def get_data():
    db = get_db()
    if not db:
        raise HTTPException(500, "Database connection failed")
    
    try:
        collection = db[COLLECTION_NAME]
        data = list(collection.find({}, {'_id': 0}))
        data.sort(key=lambda x: x.get('date', ''), reverse=True)
        for i, item in enumerate(data, 1):
            item['no'] = i
        return data
    except Exception as e:
        raise HTTPException(500, str(e))

@app.delete("/api/delete/{date}")
async def delete_by_date(date: str):
    db = get_db()
    if not db:
        raise HTTPException(500, "Database connection failed")
    
    result = db[COLLECTION_NAME].delete_many({'date': date})
    if result.deleted_count > 0:
        return {'success': True, 'message': f'Deleted {result.deleted_count} record(s)'}
    raise HTTPException(404, f'No records found for date {date}')

@app.delete("/api/delete/{date}/{rt}")
async def delete_by_date_rt(date: str, rt: str):
    db = get_db()
    if not db:
        raise HTTPException(500, "Database connection failed")
    
    result = db[COLLECTION_NAME].delete_one({'date': date, 'rt': rt})
    if result.deleted_count > 0:
        return {'success': True, 'message': f'Deleted {rt} on {date}'}
    raise HTTPException(404, 'Record not found')

@app.get("/health")
async def health_check():
    db = get_db()
    if not db:
        return {'status': 'unhealthy', 'mongodb': 'disconnected'}
    
    try:
        count = db[COLLECTION_NAME].count_documents({})
        return {
            'status': 'healthy',
            'mongodb': 'connected',
            'records': count,
            'timestamp': datetime.now().isoformat()
        }
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}

@app.get("/api/stats")
async def get_stats():
    db = get_db()
    if not db:
        raise HTTPException(500, "Database connection failed")
    
    collection = db[COLLECTION_NAME]
    return {
        'total_records': collection.count_documents({}),
        'unique_dates': len(collection.distinct('date')),
        'timestamp': datetime.now().isoformat()
    }

# =========================================================
# KEEP ALIVE FOR RENDER.COM
# =========================================================
def keep_alive():
    """Keep the app alive with periodic pings"""
    time.sleep(30)
    while True:
        try:
            response = requests.get('http://localhost:8000/health', timeout=5)
            if response.status_code == 200:
                print(f"[Keep Alive] OK at {datetime.now()}")
        except Exception as e:
            print(f"[Keep Alive] Error: {e}")
        time.sleep(300)

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    import uvicorn
    
    # Start keep-alive thread
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    
    port = int(os.environ.get('PORT', 8000))
    
    print("=" * 60)
    print("📊 STRONG RATIO SIGNALS DASHBOARD")
    print("=" * 60)
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"📱 PWA Ready: Install from browser")
    print(f"❤️ Health: http://0.0.0.0:{port}/health")
    print(f"📈 Stats: http://0.0.0.0:{port}/api/stats")
    print(f"📚 API Docs: http://0.0.0.0:{port}/docs")
    print("=" * 60)
    
    uvicorn.run(app, host='0.0.0.0', port=port)
