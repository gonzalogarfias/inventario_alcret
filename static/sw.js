// static/js/sw.js
const CACHE_STATIC = 'alcret-static-v2';
const CACHE_PAGES = 'alcret-pages-v2';
const CACHE_API = 'alcret-api-v1';

const STATIC_FILES = [
    '/',
    '/static/manifest.json',
    '/static/css/tailwind.css',
    '/static/js/app.js',
    '/static/img/logo-icon.png',
    '/static/img/logo.png',
];

// URLs que NUNCA deben cachearse
const NETWORK_ONLY = [
    /\/api\//,
    /\/admin\//,
    /\/accounts\/logout\//,
    /\/exportar\//,
];

// URLs que son vistas de solo lectura (cacheables offline)
const READONLY_PAGES = [
    /^\/productos\/$/,
    /^\/almacenes\/$/,
    /^\/categorias\/$/,
    /^\/movimientos\/$/,
    /^\/finanzas\/$/,
    /^\/finanzas\/subir\//,
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_STATIC)
            .then((cache) => cache.addAll(STATIC_FILES))
            .catch((err) => console.error('SW install error:', err))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    const currentCaches = [CACHE_STATIC, CACHE_PAGES, CACHE_API];
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((k) => k.startsWith('alcret-') && !currentCaches.includes(k))
                    .map((k) => caches.delete(k))
            )
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const { request } = event;
    const url = new URL(request.url);

    // Solo GET
    if (request.method !== 'GET') return;

    // Solo mismo origen
    if (url.origin !== self.location.origin) return;

    // Network-only: APIs, admin, logout, exports
    if (NETWORK_ONLY.some((pattern) => pattern.test(url.pathname))) {
        event.respondWith(fetch(request));
        return;
    }

    // API endpoints: network first, cache fallback (stale-while-revalidate)
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(
            fetch(request)
                .then((response) => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_API).then((cache) =>
                            cache.put(request, clone)
                        );
                    }
                    return response;
                })
                .catch(() => caches.match(request))
        );
        return;
    }

    // Static assets: cache first
    if (request.destination === 'script' || 
        request.destination === 'style' || 
        request.destination === 'image' ||
        request.destination === 'font') {
        event.respondWith(
            caches.match(request).then((cached) => {
                if (cached) return cached;
                return fetch(request).then((response) => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_STATIC).then((cache) =>
                            cache.put(request, clone)
                        );
                    }
                    return response;
                });
            })
        );
        return;
    }

    // Readonly pages: stale-while-revalidate
    if (READONLY_PAGES.some((pattern) => pattern.test(url.pathname))) {
        event.respondWith(
            caches.match(request).then((cached) => {
                const networkFetch = fetch(request).then((response) => {
                    if (response.ok) {
                        const clone = response.clone();
                        caches.open(CACHE_PAGES).then((cache) =>
                            cache.put(request, clone)
                        );
                    }
                    return response;
                }).catch(() => cached);

                return cached || networkFetch;
            })
        );
        return;
    }

    // Default: network first
    event.respondWith(
        fetch(request).catch(() => caches.match(request))
    );
});

// Mensajes desde la app principal
self.addEventListener('message', (event) => {
    if (event.data === 'skipWaiting') {
        self.skipWaiting();
    }
});