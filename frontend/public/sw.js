/* Career Navigator service worker — handles Web Push notifications. */

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'Career Navigator', body: event.data && event.data.text() };
  }
  const title = data.title || 'Career Navigator';
  const options = {
    body: data.body || '',
    tag: data.tag || undefined,
    data: { url: data.url || '/' },
    requireInteraction: false,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || '/';
  event.waitUntil(
    self.clients
      .matchAll({ type: 'window', includeUncontrolled: true })
      .then((wins) => {
        for (const w of wins) {
          if ('focus' in w) {
            if ('navigate' in w) w.navigate(url);
            return w.focus();
          }
        }
        return self.clients.openWindow(url);
      }),
  );
});
