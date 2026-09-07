/* Minimal offline-first service worker for VChaTie.
   Caches app shell assets on install so the UI loads after the first visit. */

const CACHE_NAME = 'vchatie-cache-v1';

self.addEventListener('install', function (event) {
    self.skipWaiting();
});

self.addEventListener('activate', function (event) {
    event.waitUntil(
        caches.keys().then(function (keys) {
            return Promise.all(
                keys.filter(function (key) {
                    return key !== CACHE_NAME;
                }).map(function (key) {
                    return caches.delete(key);
                })
            );
        })
    );
    self.clients.claim();
});

// Network-first with cache fallback: fresh data when online, stale shell offline.
self.addEventListener('fetch', function (event) {
    const url = event.request.url;

    // Never cache WebSocket or non-GET requests.
    if (event.request.method !== 'GET') return;
    if (url.startsWith('ws:') || url.startsWith('wss:')) return;

    event.respondWith(
        fetch(event.request)
            .then(function (response) {
                if (response && response.status === 200 && event.request.method === 'GET') {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then(function (cache) {
                        cache.put(event.request, clone);
                    });
                }
                return response;
            })
            .catch(function () {
                return caches.match(event.request, { ignoreSearch: true });
            })
    );
});