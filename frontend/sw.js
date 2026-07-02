const CACHE_NAME = "kalame-hayat-v8";

const APP_FILES = [
  "/",
  "/index.html",
  "/manifest.json",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_FILES))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names
          .filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("push", (event) => {
  event.waitUntil(
    fetch("https://square-silence-9274.mahi-pasha1986.workers.dev/bible/daily-verse", {
      cache: "no-store"
    })
      .then((res) => res.json())
      .then((data) => {
        const verse = Array.isArray(data) ? data[0] : data;
        const bookName = verse?.bible_books?.name_fa || "";

        return self.registration.showNotification("آیه روز", {
          body: verse
            ? `${verse.verse_text}\n\n${bookName} ${verse.chapter_number}:${verse.verse_number}`
            : "آیه امروز آماده است.",
          data: {
            url: "/"
          }
        });
      })
      .catch(() => {
        return self.registration.showNotification("آیه روز", {
          body: "آیه امروز آماده است.",
          data: {
            url: "/"
          }
        });
      })
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  event.waitUntil(
    clients.openWindow(
      event.notification.data?.url || "/"
    )
  );
});
