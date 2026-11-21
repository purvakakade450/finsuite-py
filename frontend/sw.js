/* FinSuite service worker: makes the app installable, lets it open offline, and shows push alerts.
   Served from /sw.js (see app/main.py); __BUILD__ changes whenever a front-end file does, so
   browsers pick up each new version. API calls are never cached. */
const BUILD = "__BUILD__";
const CACHE = "finsuite-" + BUILD;
const LIBS = /(^|\.)(cdnjs\.cloudflare\.com|fonts\.googleapis\.com|fonts\.gstatic\.com)$/;

self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(c => c.add("/")).then(() => self.skipWaiting()));
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k.startsWith("finsuite-") && k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

function remember(request, response) {
  if (response && (response.ok || response.type === "opaque")) {
    const copy = response.clone();
    caches.open(CACHE).then(c => c.put(request, copy));
  }
  return response;
}

const OFFLINE = () => new Response(
  "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'><title>FinSuite offline</title>" +
  "<body style='font-family:Georgia,serif;max-width:30rem;margin:15vh auto;padding:0 1rem;color:#0F2240'>" +
  "<h1>You are offline</h1><p>FinSuite needs an internet connection for live prices and the AI assistant. " +
  "Please reconnect and reload this page.</p></body>", { headers: { "Content-Type": "text/html; charset=utf-8" } });

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (url.origin === self.location.origin) {
    if (req.mode === "navigate") {                       // the page: newest if online, last copy if not
      event.respondWith(
        fetch(req).then(res => { remember("/", res.clone()); return res; })
          .catch(() => caches.match("/").then(hit => hit || OFFLINE()))
      );
    } else if (url.pathname.startsWith("/static/")) {    // files named with ?v=<time>: cache first
      event.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => remember(req, res))));
    }
    return;                                              // everything else (the API) goes straight to the network
  }
  if (LIBS.test(url.hostname)) {                         // chart, markdown and font libraries
    event.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => remember(req, res))));
  }
});

self.addEventListener("push", event => {
  let data = {};
  try { data = event.data.json(); } catch (e) { data = { body: event.data ? event.data.text() : "" }; }
  event.waitUntil(self.registration.showNotification(data.title || "FinSuite", {
    body: data.body || "",
    icon: "/static/icons/icon-192.png",
    badge: "/static/icons/icon-192.png",
    tag: "finsuite-alert",
    data: { url: data.url || "/" },
  }));
});

self.addEventListener("notificationclick", event => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/";
  event.waitUntil(clients.matchAll({ type: "window", includeUncontrolled: true }).then(list => {
    for (const c of list) {
      if ("focus" in c) { c.navigate(url).catch(() => {}); return c.focus(); }
    }
    return clients.openWindow(url);
  }));
});
