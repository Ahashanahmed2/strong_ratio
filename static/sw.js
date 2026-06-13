// sw.js - Service Worker for Strong Ratio Signals Dashboard
const CACHE_NAME = 'strong-ratio-dashboard-v1.0.0';
const OFFLINE_URL = '/offline';

// Assets to cache on install
const PRECACHE_ASSETS = [
    '/',
    '/offline',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css',
    'https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css',
    'https://cdn.jsdelivr.net/npm/sweetalert2@11/dist/sweetalert2.min.css',
    'https://code.jquery.com/jquery-3.6.0.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/js/bootstrap.bundle.min.js',
    'https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js',
    'https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js',
    'https://cdn.jsdelivr.net/npm/sweetalert2@11'
];

// Install event - cache initial assets
self.addEventListener('install', (event) => {
    console.log('[Service Worker] Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[Service Worker] Caching app shell');
                return cache.addAll(PRECACHE_ASSETS);
            })
            .then(() => {
                console.log('[Service Worker] Skip waiting');
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
    console.log('[Service Worker] Activating...');
    
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cacheName) => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('[Service Worker] Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('[Service Worker] Now ready to handle fetches');
            return self.clients.claim();
        })
    );
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        event.respondWith(fetch(request));
        return;
    }
    
    // Skip API calls (don't cache them)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Clone the response
                    const responseToCache = response.clone();
                    
                    // Cache API responses for offline (optional)
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseToCache);
                    });
                    
                    return response;
                })
                .catch(() => {
                    // Return cached API response if offline
                    return caches.match(request);
                })
        );
        return;
    }
    
    // For static assets - cache first then network
    if (url.pathname.match(/\.(css|js|json|png|jpg|jpeg|svg|ico)$/)) {
        event.respondWith(
            caches.match(request)
                .then((cachedResponse) => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    
                    return fetch(request).then((response) => {
                        if (!response || response.status !== 200) {
                            return response;
                        }
                        
                        const responseToCache = response.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseToCache);
                        });
                        
                        return response;
                    });
                })
        );
        return;
    }
    
    // For HTML pages - network first, then cache fallback
    if (url.pathname === '/' || url.pathname === '/index.html') {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    // Cache the latest version
                    const responseToCache = response.clone();
                    caches.open(CACHE_NAME).then((cache) => {
                        cache.put(request, responseToCache);
                    });
                    return response;
                })
                .catch(() => {
                    // Return cached version if offline
                    return caches.match(request).then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // Return offline page
                        return caches.match(OFFLINE_URL);
                    });
                })
        );
        return;
    }
    
    // Default: network with cache fallback
    event.respondWith(
        fetch(request)
            .catch(() => {
                return caches.match(request);
            })
    );
});

// Background sync for offline data
self.addEventListener('sync', (event) => {
    console.log('[Service Worker] Background sync:', event.tag);
    
    if (event.tag === 'sync-data') {
        event.waitUntil(syncData());
    }
});

// Push notification event
self.addEventListener('push', (event) => {
    console.log('[Service Worker] Push received:', event);
    
    let data = {
        title: 'Strong Ratio Dashboard',
        body: 'New data available!',
        icon: '/static/icon-192x192.png',
        badge: '/static/badge-72x72.png'
    };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    event.waitUntil(
        self.registration.showNotification(data.title, {
            body: data.body,
            icon: data.icon,
            badge: data.badge,
            vibrate: [200, 100, 200],
            tag: 'strong-ratio-update',
            requireInteraction: false,
            actions: [
                {
                    action: 'open',
                    title: 'Open Dashboard'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss'
                }
            ]
        })
    );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
    console.log('[Service Worker] Notification click:', event);
    
    event.notification.close();
    
    if (event.action === 'open') {
        event.waitUntil(
            clients.openWindow('/')
        );
    } else if (event.action === 'dismiss') {
        // Just close the notification
    } else {
        event.waitUntil(
            clients.openWindow('/')
        );
    }
});

// Function to sync data in background
async function syncData() {
    try {
        // Fetch latest data
        const response = await fetch('/api/data');
        const data = await response.json();
        
        // Store in IndexedDB for offline access
        const db = await openDatabase();
        const tx = db.transaction('dashboard_data', 'readwrite');
        const store = tx.objectStore('dashboard_data');
        
        await store.clear();
        await store.put({ id: 'latest', data: data, timestamp: Date.now() });
        
        await tx.done;
        
        console.log('[Service Worker] Data synced successfully');
        
        // Show notification
        self.registration.showNotification('Data Updated', {
            body: `${data.length} records synced`,
            icon: '/static/icon-192x192.png',
            tag: 'sync-complete'
        });
        
    } catch (error) {
        console.error('[Service Worker] Sync failed:', error);
    }
}

// Helper to open IndexedDB
function openDatabase() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('StrongRatioDB', 1);
        
        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
        
        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains('dashboard_data')) {
                db.createObjectStore('dashboard_data', { keyPath: 'id' });
            }
        };
    });
}

// Message event for communication with main thread
self.addEventListener('message', (event) => {
    console.log('[Service Worker] Message received:', event.data);
    
    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    
    if (event.data.type === 'GET_DATA') {
        // Send cached data to client
        caches.match('/api/data').then((response) => {
            if (response) {
                response.json().then((data) => {
                    event.source.postMessage({
                        type: 'CACHED_DATA',
                        data: data
                    });
                });
            }
        });
    }
});
