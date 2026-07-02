import { api } from '../api/client';

/** VAPID public keys are base64url; the browser wants a Uint8Array. */
function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(base64);
  const buffer = new ArrayBuffer(raw.length);
  const output = new Uint8Array(buffer);
  for (let i = 0; i < raw.length; i += 1) output[i] = raw.charCodeAt(i);
  return output;
}

export function pushSupported(): boolean {
  return (
    typeof navigator !== 'undefined' &&
    'serviceWorker' in navigator &&
    typeof window !== 'undefined' &&
    'PushManager' in window &&
    'Notification' in window
  );
}

export function permissionState(): NotificationPermission | 'unsupported' {
  if (!pushSupported()) return 'unsupported';
  return Notification.permission;
}

async function currentSubscription(): Promise<PushSubscription | null> {
  if (!('serviceWorker' in navigator)) return null;
  const reg = await navigator.serviceWorker.ready;
  return reg.pushManager.getSubscription();
}

export async function isSubscribed(): Promise<boolean> {
  if (!pushSupported()) return false;
  return (await currentSubscription()) !== null;
}

export type EnableResult =
  | { ok: true }
  | { ok: false; reason: 'unsupported' | 'denied' | 'server-disabled' | 'error' };

/** Ask permission, subscribe via the browser Push API, and register the
 *  subscription with the backend so job alerts can reach this device. */
export async function enablePush(): Promise<EnableResult> {
  if (!pushSupported()) return { ok: false, reason: 'unsupported' };
  try {
    const permission = await Notification.requestPermission();
    if (permission !== 'granted') return { ok: false, reason: 'denied' };

    const { data } = await api.get('/notifications/vapid-public-key/');
    if (!data.enabled || !data.public_key) return { ok: false, reason: 'server-disabled' };

    const reg = await navigator.serviceWorker.ready;
    const sub =
      (await reg.pushManager.getSubscription()) ||
      (await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(data.public_key) as BufferSource,
      }));

    const json = sub.toJSON();
    await api.post('/notifications/push/register/', {
      endpoint: json.endpoint,
      p256dh: json.keys?.p256dh,
      auth: json.keys?.auth,
    });
    return { ok: true };
  } catch {
    return { ok: false, reason: 'error' };
  }
}

/** Unsubscribe this device and tell the backend to forget it. */
export async function disablePush(): Promise<void> {
  const sub = await currentSubscription();
  if (!sub) return;
  await api.post('/notifications/push/unregister/', { endpoint: sub.endpoint }).catch(() => undefined);
  await sub.unsubscribe().catch(() => undefined);
}
