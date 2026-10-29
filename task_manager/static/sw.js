const CACHE_NAME = 'bordik-static-v3';
const OFFLINE_URL = '/static/offline.html';
const FALLBACK_HTML =
  '<!DOCTYPE html><html lang="fa" dir="rtl"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width, initial-scale=1">' +
  '<title>اتصال برقرار نشد</title></head>' +
  '<body style="font-family:Tahoma,sans-serif;padding:2rem;line-height:2">' +
  '<h2>اتصال برقرار نشد</h2>' +
  '<p>سایت در دسترس نیست. اینترنت و آدرس سرور را بررسی کن و دوباره تلاش کن.</p>' +
  '<button onclick="location.reload()" style="padding:.6rem 1.2rem;font:inherit">تلاش دوباره</button>' +
  '</body></html>';
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
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      );
      const cache = await caches.open(CACHE_NAME);
      try {
        await cache.add(OFFLINE_URL);
      } catch (error) {
        /* the offline page stays available from the previous install */
      }
      await self.clients.claim();
    })()
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
    const offline =
      (await cache.match(OFFLINE_URL)) ||
      (await caches.match(OFFLINE_URL));
    if (offline) {
      return offline;
    }
    return new Response(FALLBACK_HTML, {
      status: 503,
      headers: { 'Content-Type': 'text/html; charset=utf-8' },
    });
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
