/**
 * GenericEventBus — slug-namespaced CustomEvent pub/sub for app bridges.
 *
 * Events are dispatched on `document` as `{slug}:{eventName}`.
 * Apps wrap this with typed helpers in their own bridge/EventBus.ts.
 */

const target = document;

/**
 * Emit a bridge event namespaced by app slug.
 *
 * @param slug - App slug (e.g. "figrecipe")
 * @param eventName - Event name (e.g. "fileSelect")
 * @param detail - Event payload
 */
export function emitBridgeEvent<T = unknown>(
  slug: string,
  eventName: string,
  detail: T,
): void {
  target.dispatchEvent(new CustomEvent(`${slug}:${eventName}`, { detail }));
}

/**
 * Listen for a bridge event namespaced by app slug.
 *
 * @returns Cleanup function that removes the listener.
 */
export function onBridgeEvent<T = unknown>(
  slug: string,
  eventName: string,
  handler: (detail: T) => void,
): () => void {
  const fullName = `${slug}:${eventName}`;
  const listener = (e: Event) => handler((e as CustomEvent).detail);
  target.addEventListener(fullName, listener);
  return () => target.removeEventListener(fullName, listener);
}
