import { describe, expect, it } from 'vitest';
import { TimeseriesLruCache } from '../src/services/timeseries-cache.js';

const sample = [
  {
    countryCode: 'US',
    countryName: 'United States',
    indicator: 'GDP',
    year: 2022,
    value: 25.44,
    source: 'fixture'
  }
];

describe('TimeseriesLruCache', () => {
  it('returns null on cache miss and value on hit', () => {
    const cache = new TimeseriesLruCache(2, 1_000);

    expect(cache.get('missing')).toBeNull();

    cache.set('a', sample);
    expect(cache.get('a')).toEqual(sample);
  });

  it('evicts least-recently-used entries when max size is exceeded', () => {
    const cache = new TimeseriesLruCache(2, 60_000);

    cache.set('a', sample);
    cache.set('b', sample);

    // touch a so b becomes LRU
    expect(cache.get('a')).toEqual(sample);

    cache.set('c', sample);

    expect(cache.get('b')).toBeNull();
    expect(cache.get('a')).toEqual(sample);
    expect(cache.get('c')).toEqual(sample);
    expect(cache.stats().size).toBe(2);
  });

  it('expires entries after ttl', async () => {
    const cache = new TimeseriesLruCache(2, 5);

    cache.set('a', sample);

    await new Promise((resolve) => setTimeout(resolve, 12));

    expect(cache.get('a')).toBeNull();
  });
});
