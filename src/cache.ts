import LRU from "lru-cache";

type Key = string;
type Val<T> = { value: T; ts: number; stale?: boolean };

export function createCache<T>(ttlMs: number) {
  const lru = new LRU<Key, Val<T>>({ max: 64, ttl: ttlMs });
  return {
    get: (k: Key) => lru.get(k)?.value,
    set: (k: Key, v: T) => lru.set(k, { value: v, ts: Date.now() }),
    has: (k: Key) => lru.has(k)
  };
}
