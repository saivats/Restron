const CACHE_VERSION = 'restron-v1';
const STATIC_CACHE = 'restron-static-v1';
const API_CACHE = 'restron-api-v1';

const STATIC_ASSETS = [
  '/static/login.html',
  '/static/menu.html',
  '/static/kitchen.html',
  '/static/waiter.html',
  '/static/manager.html',
  '/static/owner.html',
  '/static/superadmin.html',
  '/static/receipt.html',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png',
  'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=DM+Sans:wght@300;400;500;600&display=swap',
  'https://cdn.jsdelivr.net/npm/fuse.js@6.6.2'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(key => key !== STATIC_CACHE && key !== API_CACHE)
            .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  if (event.request.method === 'POST') {
    return;
  }

  if (url.pathname.startsWith('/static/') ||
      url.hostname === 'fonts.googleapis.com' ||
      url.hostname === 'fonts.gstatic.com' ||
      url.hostname === 'cdn.jsdelivr.net') {
    event.respondWith(
      caches.match(event.request)
        .then(cached => cached || fetch(event.request)
          .then(response => {
            const clone = response.clone();
            caches.open(STATIC_CACHE)
              .then(cache => cache.put(event.request, clone));
            return response;
          })
        )
    );
    return;
  }

  if (url.pathname.startsWith('/menu/') ||
      url.pathname.startsWith('/manager/tables/') ||
      url.pathname.startsWith('/kitchen-display/') ||
      url.pathname.startsWith('/manager/orders/') ||
      url.pathname.startsWith('/restaurant/') ||
      url.pathname.startsWith('/owner/analytics/') ||
      url.pathname.startsWith('/staff/') ||
      url.pathname.startsWith('/customers/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const clone = response.clone();
          caches.open(API_CACHE)
            .then(cache => cache.put(event.request, clone));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  event.respondWith(
    caches.match(event.request)
      .then(cached => cached || fetch(event.request))
  );
});

self.addEventListener('sync', event => {
  if (event.tag === 'sync-orders') {
    event.waitUntil(syncPendingOrders());
  }
  if (event.tag === 'sync-checkouts') {
    event.waitUntil(syncPendingCheckouts());
  }
});

async function syncPendingOrders() {
  const db = await openRestronDB();
  const pending = await getAllPending(db, 'pending_orders');

  for (const order of pending) {
    try {
      const response = await fetch(
        `/order/?slug=${order.slug}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify(order.data)
      });
      // Any real HTTP response — success or a definitive rejection like a
      // validation error — means the server has spoken; retrying an
      // identical request won't change that outcome, so clear it either
      // way. Only a genuine network failure (fetch throwing) should leave
      // it queued for the next sync attempt.
      await deletePending(db, 'pending_orders', order.id);
    } catch (e) {
      break;
    }
  }
}

async function syncPendingCheckouts() {
  const db = await openRestronDB();
  const pending = await getAllPending(db, 'pending_checkouts');

  for (const checkout of pending) {
    try {
      const response = await fetch('/manager/checkout/', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        credentials: 'include',
        body: JSON.stringify(checkout.data)
      });
      await deletePending(db, 'pending_checkouts', checkout.id);
    } catch (e) {
      break;
    }
  }
}

function openRestronDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('restron-offline', 1);
    req.onupgradeneeded = e => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains('pending_orders')) {
        db.createObjectStore('pending_orders',
          {keyPath: 'id', autoIncrement: true});
      }
      if (!db.objectStoreNames.contains('pending_checkouts')) {
        db.createObjectStore('pending_checkouts',
          {keyPath: 'id', autoIncrement: true});
      }
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e.target.error);
  });
}

function getAllPending(db, storeName) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    const req = tx.objectStore(storeName).getAll();
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = e => reject(e.target.error);
  });
}

function deletePending(db, storeName, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
    const req = tx.objectStore(storeName).delete(id);
    req.onsuccess = () => resolve();
    req.onerror = e => reject(e.target.error);
  });
}
