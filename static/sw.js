// Service Worker — ALCRET PWA
const CACHE_STATIC = 'alcret-static-v3';
const CACHE_PAGES = 'alcret-pages-v2';
const CACHE_API = 'alcret-api-v1';

// Recursos precacheados al instalar. Todos existen en el repositorio
// (tailwind.css se genera con `npm run build:css`).
const STATIC_FILES = [
    '/',
    '/static/css/tailwind.css',
    '/static/img/logo-icon.png',
    '/static/img/logo.png',
];

// URLs que NUNCA deben cachearse
const NETWORK_ONLY = [
    /\/admin\//,
    /\/accounts\/logout\//,
    /\/exportar\//,
    /\/facturas\/.*\/archivo\//,
];

// URLs de API dinámicas (network-first, sin fallback offline)
const API_URLS = [
    /\/api\/datos-dashboard\//,
    /\/finanzas\/api\/datos\//,
];

// URLs que son vistas de solo lectura (cacheables offline)
const READONLY_PAGES = [
    /^\/productos\/$/,
    /^\/productos\/\?/,
    /^\/productos\/.+/,
    /^\/almacenes\/$/,
    /^\/categorias\/$/,
    /^\/movimientos\/$/,
    /^\/finanzas\/$/,
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_STATIC)
            .then((cache) =>
                // Precache resiliente: un recurso ausente no rompe la instalación
                Promise.all(
                    STATIC_FILES.map((url) =>
                        cache.add(url).catch(() => console.warn('SW: no se pudo precachear', url))
                    )
                )
            )
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

    // Solo GET y mismo origen
    if (request.method !== 'GET') return;
    if (url.origin !== self.location.origin) return;

    // Network-only: admin, logout, exports, descargas de facturas
    if (NETWORK_ONLY.some((pattern) => pattern.test(url.pathname))) {
        event.respondWith(fetch(request));
        return;
    }

    // APIs dinámicas: network-only (datos de sesión; nunca cacheados)
    if (API_URLS.some((pattern) => pattern.test(url.pathname))) {
        event.respondWith(fetch(request));
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
