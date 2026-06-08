import { promises as fs } from 'node:fs';
import path from 'node:path';
import { z } from 'zod';
import type { CountryStat } from '../core/dashboard.js';
import { COUNTRY_STATS } from '../data/country-stats.js';

const countryStatSchema = z.object({
  country: z.string().min(1),
  region: z.string().min(1),
  population: z.number().finite(),
  gdpPerCapita: z.number().finite(),
  lifeExpectancy: z.number().finite(),
  internetUsers: z.number().finite(),
  co2PerCapita: z.number().finite()
});

const countriesSchema = z.array(countryStatSchema);

const fileEnvSchema = z.object({
  COUNTRY_STATS_PATH: z.string().optional()
});

export class CountryRepository {
  private cache: CountryStat[] | null = null;

  async list(): Promise<CountryStat[]> {
    if (this.cache) return this.cache;

    const env = fileEnvSchema.parse(process.env);

    if (!env.COUNTRY_STATS_PATH) {
      this.cache = COUNTRY_STATS;
      return this.cache;
    }

    const filePath = path.resolve(env.COUNTRY_STATS_PATH);
    const raw = await fs.readFile(filePath, 'utf8');
    const parsed = JSON.parse(raw) as unknown;
    this.cache = countriesSchema.parse(parsed);

    return this.cache;
  }

  clearCache() {
    this.cache = null;
  }
}

export const countryRepository = new CountryRepository();
