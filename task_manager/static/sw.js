const CACHE_NAME = 'bordik-static-v1';
const OFFLINE_URL = '/static/offline.html';
const PRECACHE_URLS = [
  OFFLINE_URL,
  '/static/manifest.webmanifest',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
  '/static/icons/icon-maskable-192.png',
  '/static/icons/icon-maskable-512.png',
  '/static/icons/apple-touch-icon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener('message', (event) => {
  if (event.data === 'skip-waiting') {
    self.skipWaiting();
  }
});

function isStaticAsset(url) {
  return url.pathname.startsWith('/static/');
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) {
    return cached;
  }
  const response = await fetch(request);
  if (response && response.ok && response.type === 'basic') {
    cache.put(request, response.clone());
  }
  return response;
}

async function networkFirst(request) {
  try {
    return await fetch(request);
  } catch (error) {
    const cache = await caches.open(CACHE_NAME);
    const offline = await cache.match(OFFLINE_URL);
    if (offline) {
      return offline;
    }
    throw error;
  }
}

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request));
    return;
  }

  if (isStaticAsset(url)) {
    event.respondWith(
      cacheFirst(request).catch(() => networkFirst(request))
    );
  }
});
