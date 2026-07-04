// Rejection cool-down: after a rejection we discourage re-applying to the same
// role for a fixed window, and surface how long is left. Kept on the client as a
// single source of truth so every surface (job detail, pipeline) agrees.
export const REJECTION_COOLDOWN_DAYS = 90;

const DAY = 86_400_000;

export interface AppEventLike {
  type: string;
  payload?: { status?: string } | null;
  created_at?: string;
}

export interface CooldownApp {
  status: string;
  updated_at?: string;
  events?: AppEventLike[];
}

/** When the application was first moved to `rejected` — from the status-change
 *  event history if available, else the last-updated timestamp. We anchor to the
 *  earliest rejection so later edits (which also emit a status_changed event)
 *  don't keep resetting the cool-down clock. */
export function rejectionDate(app: CooldownApp): Date | null {
  if (app.status !== 'rejected') return null;
  const rejectedEvents = (app.events ?? [])
    .filter((e) => e.type === 'status_changed' && e.payload?.status === 'rejected' && e.created_at)
    .map((e) => new Date(e.created_at as string).getTime())
    .sort((a, b) => a - b);
  if (rejectedEvents.length > 0) return new Date(rejectedEvents[0]);
  return app.updated_at ? new Date(app.updated_at) : null;
}

export interface Cooldown {
  active: boolean;
  daysLeft: number;
  until: Date;
  untilLabel: string;
}

/** Cool-down status for a rejected application, or null if not rejected. */
export function rejectionCooldown(app: CooldownApp): Cooldown | null {
  const rejected = rejectionDate(app);
  if (!rejected) return null;
  const until = new Date(rejected.getTime() + REJECTION_COOLDOWN_DAYS * DAY);
  const daysLeft = Math.ceil((until.getTime() - Date.now()) / DAY);
  return {
    active: daysLeft > 0,
    daysLeft: Math.max(0, daysLeft),
    until,
    untilLabel: until.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }),
  };
}
