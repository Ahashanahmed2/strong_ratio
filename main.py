from flask import Flask, render_template_string, request, jsonify
from pymongo import MongoClient
from datetime import datetime
import os
from dotenv import load_dotenv
import threading
import time
import requests

load_dotenv()

app = Flask(__name__)

# MongoDB Connection
MONGODB_URI = os.environ.get("MONGODBEMAIL_URI", "")
DATABASE_NAME = "swing_trading_db"
COLLECTION_NAME = "strong_ratio_signals"

# HTML Template with CSS and JavaScript
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Strong Ratio Signals - Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css" rel="stylesheet">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        
        .container-main {
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 30px;
            margin-top: 20px;
            animation: fadeIn 0.5s ease-in;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
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
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        
        .header p {
            color: #666;
            font-size: 14px;
        }
        
        .btn-install {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 30px;
            border-radius: 25px;
            font-weight: bold;
            margin-bottom: 20px;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        
        .btn-install:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(102, 126, 234, 0.4);
            color: white;
        }
        
        .stats-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
            transition: transform 0.3s;
        }
        
        .stats-card:hover {
            transform: translateY(-5px);
        }
        
        .stats-card h3 {
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }
        
        .stats-card p {
            margin: 5px 0 0;
            opacity: 0.9;
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
            padding: 12px;
            text-align: center;
            font-weight: 600;
        }
        
        #dataTable td {
            text-align: center;
            vertical-align: middle;
            padding: 10px;
        }
        
        #dataTable tr:hover {
            background-color: #f5f5f5;
        }
        
        .btn-delete {
            background: #dc3545;
            color: white;
            border: none;
            padding: 5px 12px;
            border-radius: 5px;
            cursor: pointer;
            transition: all 0.3s;
            margin: 0 3px;
        }
        
        .btn-delete:hover {
            background: #c82333;
            transform: scale(1.05);
        }
        
        .btn-delete-date {
            background: #ffc107;
            color: #333;
            border: none;
            padding: 5px 12px;
            border-radius: 5px;
            cursor: pointer;
            margin-left: 5px;
            transition: all 0.3s;
        }
        
        .btn-delete-date:hover {
            background: #e0a800;
            transform: scale(1.05);
        }
        
        .badge-bullish {
            background: #28a745;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .badge-bearish {
            background: #dc3545;
            color: white;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .badge-neutral {
            background: #ffc107;
            color: #333;
            padding: 5px 10px;
            border-radius: 5px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .loading {
            text-align: center;
            padding: 50px;
            font-size: 18px;
            color: #667eea;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
        }
        
        .status-badge {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #28a745;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.7);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(40, 167, 69, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(40, 167, 69, 0);
            }
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
            
            .btn-delete, .btn-delete-date {
                padding: 3px 8px;
                font-size: 11px;
            }
            
            .stats-card h3 {
                font-size: 20px;
            }
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #667eea;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #764ba2;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="container-main">
            <div class="header">
                <h1>📊 Strong Ratio Signals Dashboard</h1>
                <p>Real-time MongoDB Data Management | Strong Divergence Analysis | Auto-sync with Daily Script</p>
                <div class="mt-2">
                    <span class="status-badge"></span>
                    <small>Live Connection Active</small>
                </div>
            </div>
            
            <div class="row">
                <div class="col-md-3 col-sm-6">
                    <div class="stats-card">
                        <p>📈 Total Records</p>
                        <h3 id="totalRecords">0</h3>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6">
                    <div class="stats-card">
                        <p>📅 Unique Dates</p>
                        <h3 id="uniqueDates">0</h3>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6">
                    <div class="stats-card">
                        <p>🎯 Avg Bullish Prob</p>
                        <h3 id="avgBullish">0%</h3>
                    </div>
                </div>
                <div class="col-md-3 col-sm-6">
                    <div class="stats-card">
                        <p>🕐 Last Update</p>
                        <h3 id="lastUpdate">-</h3>
                    </div>
                </div>
            </div>
            
            <div class="text-center">
                <button class="btn btn-install" onclick="installData()">
                    🔄 Install / Refresh Data
                </button>
            </div>
            
            <div class="table-container">
                <table id="dataTable" class="table table-bordered table-hover">
                    <thead>
                        <tr>
                            <th>No</th>
                            <th>Date (D-M-Y)</th>
                            <th>RT (Symbol)</th>
                            <th>BBR</th>
                            <th>Strong</th>
                            <th>Strong Ratio</th>
                            <th>Bullish Probability</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td colspan="8" class="loading">
                                <div class="spinner-border text-primary" role="status">
                                    <span class="visually-hidden">Loading...</span>
                                </div>
                                <div class="mt-2">Loading data from MongoDB...</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <div class="footer">
                <p>🚀 Powered by Flask + MongoDB | 📡 Auto-sync with daily script | 🔄 UptimeRobot Enabled | 💾 All data preserved</p>
                <p class="small">Last auto-refresh: <span id="refreshTime">-</span></p>
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
        let autoRefreshInterval;
        
        // Load data on page load
        $(document).ready(function() {
            loadData();
            startAutoRefresh();
            updateRefreshTime();
        });
        
        function startAutoRefresh() {
            // Auto-refresh every 3 minutes
            autoRefreshInterval = setInterval(function() {
                loadData();
                updateRefreshTime();
            }, 180000);
        }
        
        function updateRefreshTime() {
            const now = new Date();
            const timeString = now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            $('#refreshTime').text(timeString);
        }
        
        function loadData() {
            $.ajax({
                url: '/api/data',
                method: 'GET',
                timeout: 30000,
                success: function(data) {
                    if (data.error) {
                        showError(data.error);
                        return;
                    }
                    
                    updateStats(data);
                    renderTable(data);
                },
                error: function(xhr, status, error) {
                    console.error('Load error:', error);
                    if (status === 'timeout') {
                        showError('Request timeout - MongoDB connection may be slow');
                    } else {
                        showError('Failed to load data: ' + (xhr.responseJSON?.error || error || 'Unknown error'));
                    }
                }
            });
        }
        
        function updateStats(data) {
            // Total records
            $('#totalRecords').text(data.length.toLocaleString());
            
            // Unique dates
            const uniqueDates = [...new Set(data.map(item => item.date).filter(d => d))];
            $('#uniqueDates').text(uniqueDates.length.toLocaleString());
            
            // Average bullish probability
            let totalProb = 0;
            let countProb = 0;
            data.forEach(item => {
                if (item.bullish_probability) {
                    const prob = parseFloat(item.bullish_probability);
                    if (!isNaN(prob)) {
                        totalProb += prob;
                        countProb++;
                    }
                }
            });
            const avgProb = countProb > 0 ? (totalProb / countProb).toFixed(1) : 0;
            $('#avgBullish').text(avgProb + '%');
            
            // Last update (latest date)
            if (data.length > 0) {
                const sortedDates = data.map(d => d.date).filter(d => d).sort().reverse();
                $('#lastUpdate').text(sortedDates[0] || '-');
            }
        }
        
        function renderTable(data) {
            const tbody = $('#dataTable tbody');
            tbody.empty();
            
            if (data.length === 0) {
                tbody.html('<tr><td colspan="8" class="text-center">📭 No data available in database</td></tr>');
                if (dataTable) {
                    dataTable.destroy();
                    dataTable = null;
                }
                return;
            }
            
            // Sort by date (latest first) and add serial numbers
            data.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
            data.forEach((item, index) => {
                item.no = index + 1;
            });
            
            // Render rows
            data.forEach(item => {
                const bullishProb = item.bullish_probability || 'N/A';
                let probClass = '';
                let probValue = 0;
                
                if (bullishProb !== 'N/A') {
                    probValue = parseFloat(bullishProb);
                    if (probValue >= 60) {
                        probClass = 'badge-bearish';
                    } else if (probValue >= 45) {
                        probClass = 'badge-neutral';
                    } else {
                        probClass = 'badge-bullish';
                    }
                }
                
                const strongRatio = item.strong_ratio ? parseFloat(item.strong_ratio).toFixed(2) : '-';
                
                const row = `
                    <tr>
                        <td><strong>${item.no}</strong></td>
                        <td><strong class="text-primary">${item.date || '-'}</strong></td>
                        <td><code>${item.rt || '-'}</code></td>
                        <td>${item.bbr || '-'}</td>
                        <td class="text-truncate" style="max-width: 150px;">${item.strong || '-'}</td>
                        <td>${strongRatio}</td>
                        <td>
                            ${bullishProb !== 'N/A' ? 
                                `<span class="${probClass}">${bullishProb}</span>` : 
                                '<span class="badge-neutral">N/A</span>'}
                        </td>
                        <td>
                            <button class="btn-delete" onclick="deleteRecord('${item.date}', '${item.rt}')" title="Delete this record">
                                🗑️ Delete
                            </button>
                            <button class="btn-delete-date" onclick="deleteDate('${item.date}')" title="Delete all records for this date">
                                📅 Delete Date
                            </button>
                        </td>
                    </tr>
                `;
                tbody.append(row);
            });
            
            // Initialize or reinitialize DataTable
            if (dataTable) {
                dataTable.destroy();
            }
            
            dataTable = $('#dataTable').DataTable({
                pageLength: 25,
                responsive: true,
                order: [[1, 'desc']],
                language: {
                    search: "🔍 Search:",
                    lengthMenu: "Show _MENU_ entries",
                    info: "Showing _START_ to _END_ of _TOTAL_ records",
                    infoEmpty: "Showing 0 to 0 of 0 records",
                    infoFiltered: "(filtered from _MAX_ total records)",
                    paginate: {
                        first: "First",
                        last: "Last",
                        next: "Next",
                        previous: "Previous"
                    },
                    zeroRecords: "No matching records found"
                },
                columnDefs: [
                    { orderable: false, targets: [7] } // Disable sorting on action column
                ]
            });
        }
        
        function deleteRecord(date, rt) {
            if (!date || !rt) {
                Swal.fire('Error!', 'Invalid record data', 'error');
                return;
            }
            
            Swal.fire({
                title: '⚠️ Are you sure?',
                html: `Delete record for <strong>${rt}</strong> on <strong>${date}</strong>?`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                cancelButtonColor: '#6c757d',
                confirmButtonText: 'Yes, delete it!',
                cancelButtonText: 'Cancel'
            }).then((result) => {
                if (result.isConfirmed) {
                    $.ajax({
                        url: `/api/delete/${encodeURIComponent(date)}/${encodeURIComponent(rt)}`,
                        method: 'DELETE',
                        success: function(response) {
                            if (response.success) {
                                Swal.fire('Deleted!', response.message, 'success');
                                loadData(); // Reload data
                            } else {
                                Swal.fire('Error!', response.message, 'error');
                            }
                        },
                        error: function(xhr) {
                            Swal.fire('Error!', xhr.responseJSON?.message || 'Delete failed', 'error');
                        }
                    });
                }
            });
        }
        
        function deleteDate(date) {
            if (!date) {
                Swal.fire('Error!', 'Invalid date', 'error');
                return;
            }
            
            Swal.fire({
                title: '⚠️ Delete Entire Date?',
                html: `Delete <strong>ALL records</strong> for <strong>${date}</strong>?<br><small>This action cannot be undone!</small>`,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#dc3545',
                cancelButtonColor: '#6c757d',
                confirmButtonText: 'Yes, delete all!',
                cancelButtonText: 'Cancel'
            }).then((result) => {
                if (result.isConfirmed) {
                    $.ajax({
                        url: `/api/delete/${encodeURIComponent(date)}`,
                        method: 'DELETE',
                        success: function(response) {
                            if (response.success) {
                                Swal.fire('Deleted!', response.message, 'success');
                                loadData(); // Reload data
                            } else {
                                Swal.fire('Error!', response.message, 'error');
                            }
                        },
                        error: function(xhr) {
                            Swal.fire('Error!', xhr.responseJSON?.message || 'Delete failed', 'error');
                        }
                    });
                }
            });
        }
        
        function installData() {
            Swal.fire({
                title: '🔄 Install / Refresh Data',
                html: `
                    <div class="text-left">
                        <p>Data is automatically synced from the daily script.</p>
                        <p><strong>Manual refresh:</strong> The daily script runs automatically and updates this database.</p>
                        <p><small class="text-muted">Last sync: ${$('#lastUpdate').text()}</small></p>
                    </div>
                `,
                icon: 'info',
                confirmButtonText: 'OK',
                confirmButtonColor: '#667eea'
            });
        }
        
        function showError(message) {
            Swal.fire({
                title: 'Error!',
                text: message,
                icon: 'error',
                confirmButtonText: 'OK',
                confirmButtonColor: '#dc3545'
            });
        }
        
        // Manual refresh button (hidden feature - F5)
        $(document).keydown(function(e) {
            if (e.key === 'F5') {
                e.preventDefault();
                loadData();
                Swal.fire({
                    title: 'Refreshed',
                    text: 'Data has been refreshed',
                    icon: 'success',
                    timer: 1500,
                    showConfirmButton: false
                });
            }
        });
    </script>
</body>
</html>
"""

# MongoDB Connection Function
def get_db():
    """Get MongoDB database connection"""
    try:
        if not MONGODB_URI:
            print("❌ MONGODBEMAIL_URI environment variable not set!")
            return None
        
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)
        client.admin.command('ping')
        print("✅ MongoDB Connected Successfully!")
        return client[DATABASE_NAME]
    except Exception as e:
        print(f"❌ MongoDB Connection Error: {e}")
        return None

# Flask Routes
@app.route('/')
def index():
    """Render the main dashboard"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/data')
def get_data():
    """Get all data from strong_ratio_signals collection"""
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        collection = db[COLLECTION_NAME]
        
        # Get all data, sorted by date (latest first)
        data = list(collection.find({}, {'_id': 0}))
        
        # Sort by date (latest first)
        data.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Add serial number
        for idx, item in enumerate(data, 1):
            item['no'] = idx
        
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete/<date>', methods=['DELETE'])
def delete_by_date(date):
    """Delete all records for a specific date"""
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        collection = db[COLLECTION_NAME]
        
        # Delete all documents with given date
        result = collection.delete_many({'date': date})
        
        if result.deleted_count > 0:
            return jsonify({
                'success': True, 
                'message': f'✅ Deleted {result.deleted_count} record(s) for date {date}'
            })
        else:
            return jsonify({
                'success': False, 
                'message': f'⚠️ No records found for date {date}'
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete/<date>/<rt>', methods=['DELETE'])
def delete_by_date_and_rt(date, rt):
    """Delete a specific record by date and rt"""
    db = get_db()
    if db is None:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        collection = db[COLLECTION_NAME]
        
        result = collection.delete_one({'date': date, 'rt': rt})
        
        if result.deleted_count > 0:
            return jsonify({
                'success': True, 
                'message': f'✅ Deleted record for {rt} on {date}'
            })
        else:
            return jsonify({
                'success': False, 
                'message': f'⚠️ No record found for {rt} on {date}'
            }), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/install', methods=['POST'])
def install_data():
    """Manual data installation/refresh endpoint"""
    return jsonify({
        'success': True,
        'message': 'Data is automatically synced from daily script. No manual installation needed.',
        'status': 'active',
        'last_sync': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/health')
def health_check():
    """Health check endpoint for UptimeRobot"""
    db = get_db()
    if db is None:
        return jsonify({'status': 'unhealthy', 'mongodb': 'disconnected'}), 500
    
    try:
        collection = db[COLLECTION_NAME]
        count = collection.count_documents({})
        return jsonify({
            'status': 'healthy',
            'mongodb': 'connected',
            'record_count': count,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# Keep Alive Function for Render.com
def keep_alive():
    """Keep the app alive with periodic pings"""
    time.sleep(30)  # Wait for app to start
    while True:
        try:
            # Ping the health endpoint
            response = requests.get('http://localhost:5000/health', timeout=5)
            if response.status_code == 200:
                print(f"[Keep Alive] Health check passed at {datetime.now()}")
            else:
                print(f"[Keep Alive] Health check returned {response.status_code}")
        except Exception as e:
            print(f"[Keep Alive] Error: {e}")
        time.sleep(300)  # Every 5 minutes

if __name__ == '__main__':
    # Start keep-alive thread if not in production
    import sys
    if '--no-keep-alive' not in sys.argv:
        keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
        keep_alive_thread.start()
        print("✅ Keep-alive thread started")
    
    # Get port from environment variable (Render.com uses PORT)
    port = int(os.environ.get('PORT', 5000))
    
    print("=" * 60)
    print("🚀 Strong Ratio Signals Dashboard")
    print("=" * 60)
    print(f"📅 Server Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 MongoDB URI: {'Set' if MONGODB_URI else 'Not Set'}")
    print(f"🗄️  Database: {DATABASE_NAME}")
    print(f"📂 Collection: {COLLECTION_NAME}")
    print(f"🌐 Running on: http://0.0.0.0:{port}")
    print(f"📊 Dashboard: http://0.0.0.0:{port}/")
    print(f"❤️ Health Check: http://0.0.0.0:{port}/health")
    print("=" * 60)
    
    app.run(debug=False, host='0.0.0.0', port=port)
