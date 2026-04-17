/* Service Worker — Fëgg Jaay Dashboard — notifications push nouvelles commandes */

self.addEventListener("push", function (event) {
  if (!event.data) return;

  let data = {};
  try {
    data = event.data.json();
  } catch (e) {
    data = { title: "Fëgg Jaay", body: event.data.text() };
  }

  const title = data.title || "Fëgg Jaay";
  const options = {
    body: data.body || "Nouvelle notification",
    icon: data.icon || "/static/dashboard/icon-192.png",
    badge: "/static/dashboard/icon-192.png",
    tag: data.tag || "fegg-jaay",
    data: { url: data.url || "/dashboard/" },
    requireInteraction: true,
  };

  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", function (event) {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/dashboard/";
  event.waitUntil(clients.openWindow(url));
});
