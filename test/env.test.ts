import { describe, expect, it } from 'vitest';
import { loadEnv } from '../src/plugins/env.js';

describe('loadEnv', () => {
  it('uses defaults when env values are missing', () => {
    const env = loadEnv({});

    expect(env.NODE_ENV).toBe('development');
    expect(env.PORT).toBe(3000);
    expect(env.HOST).toBe('0.0.0.0');
  });

  it('coerces and validates explicit env values', () => {
    const env = loadEnv({
      NODE_ENV: 'production',
      PORT: '8080',
      HOST: '127.0.0.1'
    });

    expect(env.NODE_ENV).toBe('production');
    expect(env.PORT).toBe(8080);
    expect(env.HOST).toBe('127.0.0.1');
  });

  it('throws when PORT is not positive', () => {
    expect(() => loadEnv({ PORT: '0' })).toThrow();
  });
});
