const CACHE_NAME = "feggjaay-v1";
const OFFLINE_URLS = ["/dashboard/", "/dashboard/commandes/"];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((c) => c.addAll(OFFLINE_URLS).catch(() => {}))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET") return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});

self.addEventListener("push", (e) => {
  let data = {};
  try { data = e.data.json(); } catch (_) { data = { title: "Fëgg Jaay", body: e.data ? e.data.text() : "" }; }

  const title = data.title || "Fëgg Jaay";
  const options = {
    body: data.body || "",
    icon: "/static/img/fegg_jaay_icon_transparent.png",
    badge: "/static/img/fegg_jaay_icon_transparent.png",
    tag: data.tag || "feggjaay",
    data: { url: data.url || "/dashboard/commandes/" },
    requireInteraction: true,
    vibrate: [200, 100, 200],
  };

  e.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (e) => {
  e.notification.close();
  const url = (e.notification.data && e.notification.data.url) || "/dashboard/commandes/";
  e.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((wins) => {
      for (const win of wins) {
        if (win.url.includes("/dashboard/") && "focus" in win) {
          win.navigate(url);
          return win.focus();
        }
      }
      return clients.openWindow(url);
    })
  );
});
