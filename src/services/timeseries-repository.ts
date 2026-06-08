import { promises as fs } from 'node:fs';
import path from 'node:path';
import { z } from 'zod';
import {
  timeSeriesCollectionSchema,
  type TimeSeriesPoint
} from '../core/timeseries.js';

const envSchema = z.object({
  TIMESERIES_DATA_PATH: z.string().optional()
});

const fallbackFixtures: TimeSeriesPoint[] = [
  { countryCode: 'US', countryName: 'United States', indicator: 'GDP', year: 2020, value: 20.89, source: 'fixture' },
  { countryCode: 'US', countryName: 'United States', indicator: 'GDP', year: 2021, value: 23.32, source: 'fixture' },
  { countryCode: 'US', countryName: 'United States', indicator: 'GDP', year: 2022, value: 25.44, source: 'fixture' },
  { countryCode: 'CN', countryName: 'China', indicator: 'GDP', year: 2020, value: 14.69, source: 'fixture' },
  { countryCode: 'CN', countryName: 'China', indicator: 'GDP', year: 2021, value: 17.82, source: 'fixture' },
  { countryCode: 'CN', countryName: 'China', indicator: 'GDP', year: 2022, value: 17.96, source: 'fixture' },
  { countryCode: 'JP', countryName: 'Japan', indicator: 'GDP', year: 2020, value: 5.06, source: 'fixture' },
  { countryCode: 'JP', countryName: 'Japan', indicator: 'GDP', year: 2021, value: 4.94, source: 'fixture' },
  { countryCode: 'JP', countryName: 'Japan', indicator: 'GDP', year: 2022, value: 4.23, source: 'fixture' },
  { countryCode: 'AU', countryName: 'Australia', indicator: 'GDP', year: 2020, value: 1.33, source: 'fixture' },
  { countryCode: 'AU', countryName: 'Australia', indicator: 'GDP', year: 2021, value: 1.55, source: 'fixture' },
  { countryCode: 'AU', countryName: 'Australia', indicator: 'GDP', year: 2022, value: 1.68, source: 'fixture' },
  { countryCode: 'CA', countryName: 'Canada', indicator: 'GDP', year: 2020, value: 1.64, source: 'fixture' },
  { countryCode: 'CA', countryName: 'Canada', indicator: 'GDP', year: 2021, value: 1.99, source: 'fixture' },
  { countryCode: 'CA', countryName: 'Canada', indicator: 'GDP', year: 2022, value: 2.14, source: 'fixture' },
  { countryCode: 'US', countryName: 'United States', indicator: 'POPULATION', year: 2020, value: 331.5, source: 'fixture' },
  { countryCode: 'CN', countryName: 'China', indicator: 'POPULATION', year: 2020, value: 1412.0, source: 'fixture' }
];

const csvRawSchema = z.object({
  countryCode: z.string(),
  countryName: z.string(),
  indicator: z.string(),
  year: z.string(),
  value: z.string(),
  source: z.string().optional()
});

function parseCsv(content: string): TimeSeriesPoint[] {
  const lines = content
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length <= 1) {
    return [];
  }

  const headers = lines[0].split(',').map((header) => header.trim());
  const rows = lines.slice(1).map((line) => {
    const values = line.split(',').map((value) => value.trim());
    const record = Object.fromEntries(headers.map((key, idx) => [key, values[idx] ?? '']));
    return csvRawSchema.parse(record);
  });

  const normalized = rows.map((row) => ({
    countryCode: row.countryCode,
    countryName: row.countryName,
    indicator: row.indicator,
    year: row.year,
    value: row.value,
    source: row.source ?? 'etl-csv'
  }));

  return timeSeriesCollectionSchema.parse(normalized);
}

export class TimeSeriesRepository {
  private cache: TimeSeriesPoint[] | null = null;

  async list(): Promise<TimeSeriesPoint[]> {
    if (this.cache) return this.cache;

    const env = envSchema.parse(process.env);
    const candidatePaths = [
      env.TIMESERIES_DATA_PATH,
      'fixtures/timeseries.sample.json',
      'fixtures/timeseries.sample.csv',
      'db/timeseries.json',
      'db/timeseries.csv',
      'scripts/timeseries.json'
    ].filter((value): value is string => Boolean(value));

    for (const candidate of candidatePaths) {
      const resolved = path.resolve(candidate);

      try {
        const stat = await fs.stat(resolved);
        if (!stat.isFile()) continue;

        const content = await fs.readFile(resolved, 'utf8');

        if (resolved.endsWith('.json')) {
          const parsed = JSON.parse(content) as unknown;
          this.cache = timeSeriesCollectionSchema.parse(parsed);
          return this.cache;
        }

        if (resolved.endsWith('.csv')) {
          this.cache = parseCsv(content);
          return this.cache;
        }
      } catch {
        // Try next candidate path
      }
    }

    this.cache = fallbackFixtures;
    return this.cache;
  }

  clearCache() {
    this.cache = null;
  }
}

export const timeSeriesRepository = new TimeSeriesRepository();
