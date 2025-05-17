const CACHE_NAME = 'idiotic-test-room';
const ASSETS = [
  '/',
  '/static/index.html',
  '/static/main.css', // if you extract CSS
  '/static/icons/icons-192.png',
  '/static/icons/icons-512.png'
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
});
self.addEventListener('fetch', e => {
  const req = e.request;
  e.respondWith(
    caches.match(req).then(res => res || fetch(req))
  );
});