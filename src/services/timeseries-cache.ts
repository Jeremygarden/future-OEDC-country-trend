import type { TimeSeriesPoint } from '../core/timeseries.js';

type CacheEntry = {
  value: TimeSeriesPoint[];
  createdAt: number;
};

export class TimeseriesLruCache {
  private readonly store = new Map<string, CacheEntry>();

  constructor(
    private readonly maxEntries = 200,
    private readonly ttlMs = 60_000
  ) {}

  get(key: string): TimeSeriesPoint[] | null {
    const entry = this.store.get(key);
    if (!entry) return null;

    if (Date.now() - entry.createdAt > this.ttlMs) {
      this.store.delete(key);
      return null;
    }

    this.store.delete(key);
    this.store.set(key, entry);
    return entry.value;
  }

  set(key: string, value: TimeSeriesPoint[]) {
    if (this.store.has(key)) {
      this.store.delete(key);
    }

    this.store.set(key, {
      value,
      createdAt: Date.now()
    });

    while (this.store.size > this.maxEntries) {
      const lruKey = this.store.keys().next().value;
      if (lruKey) {
        this.store.delete(lruKey);
      } else {
        break;
      }
    }
  }

  stats() {
    return {
      size: this.store.size,
      maxEntries: this.maxEntries,
      ttlMs: this.ttlMs
    };
  }

  clear() {
    this.store.clear();
  }
}

export const timeseriesLruCache = new TimeseriesLruCache();
