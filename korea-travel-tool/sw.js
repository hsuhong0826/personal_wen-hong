const CACHE_NAME = 'korea-travel-tool-v1';
const APP_FILES = [
  './', './index.html', './css/style.css', './js/app.js',
  './js/exchange.js', './js/quick-table.js', './js/phrases.js',
  './data/korean.json', './manifest.json', './icons/icon.svg',
  './icons/icon-192.png', './icons/icon-512.png'
];

// 安裝時預存頁面與語句，初次成功載入後可離線開啟。
self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
      .then(() => self.clients.claim())
  );
});

// 僅快取本站檔案；即時匯率由頁面透過網路取得並存於 localStorage。
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET' || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(caches.match(event.request).then((cached) => cached || fetch(event.request)));
});
