const CACHE_NAME = 'hn-translator-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/manifest.json',
  // أضف أيقونات التطبيق هنا
];

// تثبيت السيرفيس ووركر
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('تم التخزين المؤقت للملفات');
        return cache.addAll(urlsToCache);
      })
  );
});

// اعتراض الطلبات وتقديم نسخة مخزنة
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // إذا كانت الصفحة موجودة في التخزين المؤقت، قدمها
        if (response) {
          return response;
        }
        // وإلا، احصل عليها من الشبكة
        return fetch(event.request)
          .then(response => {
            // لا تخزن الطلبات التي تفشل
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            // تخزين نسخة من الاستجابة
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
              });
            return response;
          });
      })
  );
});

// تحديث التخزين المؤقت عند تفعيل السيرفيس الجديد
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});
