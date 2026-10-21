/**
 * Aanya Service Worker - Static Asset Cache Only
 *
 * CRITICAL SECURITY & DATA POLICY:
 * - Only safe static UI assets (HTML, CSS, JS, icons) are cached.
 * - API requests (/api/*) are NEVER cached under any circumstance.
 * - No user data or AI responses are stored in the service worker cache.
 */

const CACHE_NAME = 'aanya-static-v1.0.0';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/static/css/styles.css',
  '/static/js/app.js',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon.svg'
];

// Install Event: Pre-cache static frontend shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: Cleanup older cache generations
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Network-only for API, Cache-first for safe static assets
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // STRICT RULE: Never cache API requests
  if (url.pathname.startsWith('/api/') || event.request.method !== 'GET') {
    event.respondWith(fetch(event.request));
    return;
  }

  // Safe static asset handling: Stale-While-Revalidate with network fallback
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
            const responseToCache = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, responseToCache);
            });
          }
          return networkResponse;
        })
        .catch(() => {
          // If offline and request is navigation, serve cached index.html
          if (event.request.mode === 'navigate') {
            return caches.match('/index.html');
          }
        });

      return cachedResponse || fetchPromise;
    })
  );
});
