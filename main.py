from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
from datetime import datetime, timedelta
import os
import json
from dotenv import load_dotenv
from contextlib import asynccontextmanager

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
# DEFINE STATIC FILES CONTENT
# =========================================================

MANIFEST_JSON = {
    "name": "Strong Ratio Signals Dashboard",
    "short_name": "Strong Ratio",
    "description": "Real-time MongoDB dashboard for strong ratio signals",
    "start_url": "/",
    "display": "standalone",
    "theme_color": "#667eea",
    "background_color": "#ffffff",
    "icons": [
        {
            "src": "https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/icons/favicon.ico",
            "sizes": "64x64",
            "type": "image/x-icon"
        }
    ]
}

SERVICE_WORKER_JS = '''// Simple service worker for offline support
const CACHE_NAME = 'strong-ratio-v1';

self.addEventListener('install', event => {
    console.log('Service Worker installing');
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    console.log('Service Worker activating');
    event.waitUntil(clients.claim());
});

self.addEventListener('fetch', event => {
    event.respondWith(fetch(event.request));
});
'''

OFFLINE_HTML = '''<!DOCTYPE html>
<html>
<head><title>Offline</title></head>
<body>
<h1>You are offline</h1>
<p>Please check your internet connection.</p>
</body>
</html>'''

def create_static_files():
    """Create all static files"""
    try:
        with open("static/manifest.json", "w") as f:
            json.dump(MANIFEST_JSON, f, indent=2)
        print("✅ Created static/manifest.json")

        with open("static/sw.js", "w") as f:
            f.write(SERVICE_WORKER_JS)
        print("✅ Created static/sw.js")

        with open("static/offline.html", "w") as f:
            f.write(OFFLINE_HTML)
        print("✅ Created static/offline.html")
    except Exception as e:
        print(f"⚠️ Error creating static files: {e}")

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
# HELPER FUNCTIONS
# =========================================================
def calculate_bullish_probability(bbr):
    """Calculate bullish probability based on BBR value"""
    if bbr is None:
        return "N/A"
    try:
        bbr_val = float(bbr)
        if bbr_val > 3.0:
            return "70%"
        elif bbr_val > 2.5:
            return "60%"
        elif bbr_val > 2.0:
            return "50%"
        elif bbr_val > 1.5:
            return "40%"
        else:
            return "30%"
    except:
        return "N/A"

def parse_strong_ratio(strong_str):
    """Parse strong field (format: '19:3' -> ratio 6.33)"""
    if not strong_str or strong_str == '-':
        return None
    try:
        if ':' in str(strong_str):
            parts = str(strong_str).split(':')
            if len(parts) == 2:
                numerator = float(parts[0])
                denominator = float(parts[1])
                if denominator > 0:
                    return round(numerator / denominator, 2)
        return None
    except:
        return None

def calculate_3day_avg_strong_ratio(collection):
    """Calculate 3-day average strong ratio"""
    try:
        three_days_ago = datetime.now() - timedelta(days=3)
        
        recent_records = list(collection.find(
            {'saved_at': {'$gte': three_days_ago}},
            {'strong': 1, 'saved_at': 1}
        ))
        
        if not recent_records:
            return 0.0, 0
        
        ratios = []
        for doc in recent_records:
            ratio = parse_strong_ratio(doc.get('strong'))
            if ratio is not None:
                ratios.append(ratio)
        
        if not ratios:
            return 0.0, 0
            
        avg_ratio = sum(ratios) / len(ratios)
        return round(avg_ratio, 2), len(ratios)
        
    except Exception as e:
        print(f"Error calculating 3-day average: {e}")
        return 0.0, 0

# =========================================================
# FASTAPI APP
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 60)
    print("🚀 Strong Ratio Dashboard Starting...")
    print("=" * 60)

    db = get_db()
    if db is not None:
        try:
            collection = db[COLLECTION_NAME]
            count = collection.count_documents({})
            print(f"📊 Found {count} records in database")
            
            # Show sample data
            sample = collection.find_one()
            if sample:
                print(f"📝 Sample record: {sample}")
        except Exception as e:
            print(f"⚠️ Error accessing collection: {e}")
    else:
        print("⚠️ Database connection failed on startup")

    yield
    print("🛑 Shutting down...")

create_static_files()

app = FastAPI(title="Strong Ratio Dashboard", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("✅ Static files mounted")
except Exception as e:
    print(f"⚠️ Error mounting static files: {e}")

# =========================================================
# HTML TEMPLATE (FIXED VERSION)
# =========================================================
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strong Ratio Signals Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css" rel="stylesheet">
    <style>
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
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }
        .header h1 {
            color: #333;
            font-weight: bold;
        }
        .stats-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            transition: transform 0.3s;
        }
        .stats-card:hover {
            transform: translateY(-5px);
        }
        .stats-card h3 {
            font-size: 32px;
            font-weight: bold;
            margin: 0;
        }
        .stats-card p {
            margin: 10px 0 0;
            opacity: 0.9;
        }
        .stats-card small {
            font-size: 11px;
            opacity: 0.8;
        }
        .btn-refresh {
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            padding: 10px 30px;
            border-radius: 25px;
            font-weight: bold;
            margin-bottom: 20px;
            transition: all 0.3s;
        }
        .btn-refresh:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(40,167,69,0.3);
        }
        .btn-delete {
            background: #dc3545;
            color: white;
            border: none;
            padding: 5px 12px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .btn-delete:hover {
            background: #c82333;
            transform: scale(1.05);
        }
        .badge-bullish {
            background: #28a745;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
        }
        .badge-bearish {
            background: #dc3545;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
        }
        .badge-neutral {
            background: #ffc107;
            color: #333;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: 600;
        }
        .trend-up {
            color: #28a745;
            font-weight: bold;
        }
        .trend-down {
            color: #dc3545;
            font-weight: bold;
        }
        .trend-neutral {
            color: #ffc107;
            font-weight: bold;
        }
        .table-container {
            overflow-x: auto;
            margin-top: 20px;
        }
        #dataTable {
            font-size: 14px;
        }
        #dataTable th {
            background: #667eea;
            color: white;
            text-align: center;
        }
        #dataTable td {
            text-align: center;
            vertical-align: middle;
        }
        .loading {
            text-align: center;
            padding: 50px;
        }
        @media (max-width: 768px) {
            .container-main {
                padding: 15px;
            }
            .header h1 {
                font-size: 1.5em;
            }
            #dataTable {
                font-size: 11px;
            }
            .stats-card h3 {
                font-size: 24px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="container-main">
            <div class="header">
                <h1>📊 Strong Ratio Signals Dashboard</h1>
                <p>FastAPI + MongoDB | Real-time Data</p>
            </div>
            
            <div class="row mb-4">
                <div class="col-md-4 col-sm-6 mb-3">
                    <div class="stats-card">
                        <p>📈 Total Records</p>
                        <h3 id="totalRecords">0</h3>
                    </div>
                </div>
                <div class="col-md-4 col-sm-6 mb-3">
                    <div class="stats-card">
                        <p>⭐ Overall Avg Ratio</p>
                        <h3 id="avgStrongRatio">0.00</h3>
                        <small>All time</small>
                    </div>
                </div>
                <div class="col-md-4 col-sm-6 mb-3">
                    <div class="stats-card">
                        <p>📅 3-Day Avg Ratio</p>
                        <h3 id="avg3DayRatio">0.00</h3>
                        <small id="avg3DayInfo">Calculating...</small>
                    </div>
                </div>
            </div>
            
            <div class="text-center">
                <button class="btn-refresh" onclick="refreshData()">🔄 Refresh Data</button>
            </div>
            
            <div class="table-container">
                <table id="dataTable" class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>RT</th>
                            <th>BBR</th>
                            <th>Strong</th>
                            <th>Strong Ratio</th>
                            <th>Bullish Prob</th>
                            <th>Saved At</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr class="loading">
                            <td colspan="8">
                                <div class="spinner-border text-primary"></div><br>
                                Loading data...
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="footer text-center mt-4 pt-3 border-top">
                <p>🚀 FastAPI + MongoDB | Auto-refresh every 3 minutes</p>
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
        let dataTable;
        
        function refreshData() {
            loadData();
            load3DayStats();
        }
        
        function loadData() {
            console.log("Loading data...");
            $.ajax({
                url: '/api/data',
                method: 'GET',
                timeout: 30000,
                success: function(response) {
                    console.log("Data received:", response);
                    if (response.error) {
                        showError(response.error);
                        return;
                    }
                    if (Array.isArray(response) && response.length > 0) {
                        updateStats(response);
                        renderTable(response);
                    } else {
                        console.log("No data found");
                        showNoData();
                    }
                    document.getElementById('refreshTime').innerText = new Date().toLocaleTimeString();
                },
                error: function(xhr, status, error) {
                    console.error('Error:', error, xhr.responseText);
                    showError('Failed to load data: ' + error);
                    showNoData();
                }
            });
        }
        
        function showNoData() {
            const tbody = $('#dataTable tbody');
            tbody.html('<tr><td colspan="8" class="text-center">No data available in database</td></tr>');
            if (dataTable) dataTable.destroy();
            dataTable = null;
            document.getElementById('totalRecords').innerText = '0';
            document.getElementById('avgStrongRatio').innerHTML = '0.00';
        }
        
        function load3DayStats() {
            $.ajax({
                url: '/api/3day-avg',
                method: 'GET',
                success: function(data) {
                    console.log("3-day stats:", data);
                    if (data.avg_strong_ratio_3day > 0) {
                        $('#avg3DayRatio').html(data.avg_strong_ratio_3day.toFixed(2));
                        $('#avg3DayInfo').html(`Last 3 days (${data.record_count_3day} records) | Trend: ${data.trend}`);
                    } else {
                        $('#avg3DayRatio').html('0.00');
                        $('#avg3DayInfo').html('No data in last 3 days');
                    }
                },
                error: function(err) {
                    console.error("3-day stats error:", err);
                    $('#avg3DayRatio').html('0.00');
                    $('#avg3DayInfo').html('Error loading 3-day data');
                }
            });
        }
        
        function updateStats(data) {
            document.getElementById('totalRecords').innerText = data.length;
            
            let totalRatio = 0, ratioCount = 0;
            data.forEach(d => {
                if (d.strong_ratio && !isNaN(parseFloat(d.strong_ratio))) {
                    totalRatio += parseFloat(d.strong_ratio);
                    ratioCount++;
                }
            });
            let avgRatio = ratioCount > 0 ? (totalRatio / ratioCount).toFixed(2) : '0.00';
            document.getElementById('avgStrongRatio').innerHTML = avgRatio;
        }
        
        function renderTable(data) {
            const tbody = $('#dataTable tbody');
            tbody.empty();
            
            if (!data || data.length === 0) {
                tbody.html('<tr><td colspan="8" class="text-center">No data available</td></tr>');
                if (dataTable) dataTable.destroy();
                return;
            }
            
            // Sort by saved_at descending
            data.sort((a, b) => {
                if (!a.saved_at) return 1;
                if (!b.saved_at) return -1;
                return new Date(b.saved_at) - new Date(a.saved_at);
            });
            
            data.forEach((item, idx) => {
                let strongRatioDisplay = item.strong_ratio ? parseFloat(item.strong_ratio).toFixed(2) : '-';
                let bullishClass = 'badge-neutral';
                let bullishText = item.bullish_probability || 'N/A';
                
                if (bullishText !== 'N/A') {
                    let num = parseFloat(bullishText);
                    if (num >= 60) bullishClass = 'badge-bearish';
                    else if (num >= 45) bullishClass = 'badge-neutral';
                    else bullishClass = 'badge-bullish';
                }
                
                let savedDate = item.saved_at ? new Date(item.saved_at).toLocaleString() : '-';
                let rtValue = item.rt || '-';
                let bbrValue = item.bbr ? parseFloat(item.bbr).toFixed(2) : '-';
                let strongValue = item.strong || '-';
                
                let row = `
                    <tr>
                        <td><strong>${idx + 1}</strong></td>
                        <td><code>${rtValue}</code></td>
                        <td>${bbrValue}</td>
                        <td>${strongValue}</td>
                        <td><strong>${strongRatioDisplay}</strong></td>
                        <td><span class="${bullishClass}">${bullishText}</span></td>
                        <td><small>${savedDate}</small></td>
                        <td><button class="btn-delete" onclick="deleteRecord('${rtValue.replace(/'/g, "\\'")}')">🗑️ Delete</button></td>
                    </tr>
                `;
                tbody.append(row);
            });
            
            // Initialize DataTable
            if (dataTable) {
                dataTable.destroy();
            }
            dataTable = $('#dataTable').DataTable({
                pageLength: 25,
                responsive: true,
                order: [[6, 'desc']],
                columnDefs: [
                    { orderable: false, targets: [7] }
                ],
                language: {
                    emptyTable: "No data available in table"
                }
            });
        }
        
        function deleteRecord(rt) {
            Swal.fire({
                title: 'Confirm Delete',
                html: `Delete record for <strong>${rt}</strong>?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                confirmButtonText: 'Delete'
            }).then((result) => {
                if (result.isConfirmed) {
                    $.ajax({
                        url: `/api/delete/${encodeURIComponent(rt)}`,
                        method: 'DELETE',
                        success: function(res) {
                            Swal.fire('Deleted!', res.message, 'success');
                            loadData();
                            load3DayStats();
                        },
                        error: function() {
                            Swal.fire('Error!', 'Delete failed', 'error');
                        }
                    });
                }
            });
        }
        
        function showError(msg) {
            Swal.fire('Error', msg, 'error');
        }
        
        $(document).ready(() => {
            console.log("Document ready, loading data...");
            loadData();
            load3DayStats();
            setInterval(() => {
                loadData();
                load3DayStats();
            }, 180000);
        });
    </script>
</body>
</html>'''

# =========================================================
# API ROUTES
# =========================================================
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML_TEMPLATE

@app.get("/api/data")
async def get_data():
    """Fetch data from MongoDB and transform to match UI requirements"""
    db = get_db()
    if db is None:
        raise HTTPException(500, "Database connection failed")

    try:
        collection = db[COLLECTION_NAME]
        documents = list(collection.find({}, {'_id': 0}))
        
        print(f"Found {len(documents)} documents in MongoDB")

        transformed_data = []
        for doc in documents:
            strong_ratio = parse_strong_ratio(doc.get('strong'))
            bullish_prob = calculate_bullish_probability(doc.get('bbr'))
            
            transformed_item = {
                'rt': doc.get('rt', '-'),
                'bbr': doc.get('bbr', 0),
                'strong': doc.get('strong', '-'),
                'strong_ratio': strong_ratio,
                'bullish_probability': bullish_prob,
                'saved_at': doc.get('saved_at', datetime.now().isoformat())
            }
            transformed_data.append(transformed_item)
            
            # Debug first item
            if len(transformed_data) == 1:
                print(f"First transformed item: {transformed_item}")

        print(f"✅ Returning {len(transformed_data)} records")
        return transformed_data

    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        raise HTTPException(500, str(e))

@app.get("/api/3day-avg")
async def get_3day_average():
    """Get 3-day average strong ratio with trend analysis"""
    db = get_db()
    if db is None:
        raise HTTPException(500, "Database connection failed")
    
    try:
        collection = db[COLLECTION_NAME]
        
        three_day_avg, record_count = calculate_3day_avg_strong_ratio(collection)
        
        # Calculate overall average
        all_docs = list(collection.find({}, {'strong': 1}))
        all_ratios = []
        for doc in all_docs:
            ratio = parse_strong_ratio(doc.get('strong'))
            if ratio is not None:
                all_ratios.append(ratio)
        
        overall_avg = round(sum(all_ratios) / len(all_ratios), 2) if all_ratios else 0
        
        # Calculate trend
        trend = 'neutral'
        if three_day_avg > 0 and overall_avg > 0:
            if three_day_avg > overall_avg:
                trend = 'up'
            elif three_day_avg < overall_avg:
                trend = 'down'
        
        return {
            'avg_strong_ratio_3day': three_day_avg,
            'record_count_3day': record_count,
            'overall_avg': overall_avg,
            'trend': trend,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        print(f"❌ Error in 3-day average: {e}")
        raise HTTPException(500, str(e))

@app.delete("/api/delete/{rt}")
async def delete_by_rt(rt: str):
    """Delete a record by RT value"""
    db = get_db()
    if db is None:
        raise HTTPException(500, "Database connection failed")

    result = db[COLLECTION_NAME].delete_one({'rt': rt})
    if result.deleted_count > 0:
        return {'success': True, 'message': f'Deleted record for {rt}'}
    raise HTTPException(404, f'Record not found for RT: {rt}')

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db = get_db()
    if db is None:
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
    """Get statistics about the data"""
    db = get_db()
    if db is None:
        raise HTTPException(500, "Database connection failed")

    collection = db[COLLECTION_NAME]
    total = collection.count_documents({})

    all_docs = list(collection.find({}, {'strong': 1}))
    ratios = []
    for doc in all_docs:
        ratio = parse_strong_ratio(doc.get('strong'))
        if ratio:
            ratios.append(ratio)

    avg_ratio = sum(ratios) / len(ratios) if ratios else 0
    three_day_avg, three_day_count = calculate_3day_avg_strong_ratio(collection)

    return {
        'total_records': total,
        'avg_strong_ratio': round(avg_ratio, 2),
        'avg_strong_ratio_3day': three_day_avg,
        'records_last_3days': three_day_count,
        'timestamp': datetime.now().isoformat()
    }

# =========================================================
# HEAD ROUTES FOR MONITORING
# =========================================================
@app.head("/")
async def head_index():
    return Response(status_code=200)

@app.head("/api/data")
async def head_data():
    return Response(status_code=200)

@app.head("/api/3day-avg")
async def head_3day_avg():
    return Response(status_code=200)

@app.head("/health")
async def head_health():
    db = get_db()
    if db is None:
        return Response(status_code=503)
    return Response(status_code=200)

@app.head("/api/stats")
async def head_stats():
    return Response(status_code=200)

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get('PORT', 8000))

    print("=" * 60)
    print("📊 STRONG RATIO SIGNALS DASHBOARD (FIXED VERSION)")
    print("=" * 60)
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"❤️ Health: http://0.0.0.0:{port}/health")
    print(f"📈 Stats: http://0.0.0.0:{port}/api/stats")
    print(f"📊 3-Day Avg: http://0.0.0.0:{port}/api/3day-avg")
    print(f"📚 API Docs: http://0.0.0.0:{port}/docs")
    print("=" * 60)

    uvicorn.run(app, host='0.0.0.0', port=port)