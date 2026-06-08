import type { CountryMetricRecord } from './types.js';

export interface RawCountryMetricRow {
  country_code: string;
  country_name: string;
  metric: string;
  year: number | string;
  value: number | string;
}

export function normalizeRows(rows: RawCountryMetricRow[]): CountryMetricRecord[] {
  const grouped = new Map<string, CountryMetricRecord>();

  for (const row of rows) {
    const year = Number(row.year);
    const value = Number(row.value);

    if (!row.country_code || !row.country_name || !row.metric) {
      continue;
    }

    if (!Number.isFinite(year) || !Number.isFinite(value)) {
      continue;
    }

    const key = `${row.country_code}::${row.metric}`;
    const existing = grouped.get(key);

    if (!existing) {
      grouped.set(key, {
        countryCode: row.country_code,
        countryName: row.country_name,
        metric: row.metric,
        points: [{ year, value }]
      });
      continue;
    }

    existing.points.push({ year, value });
  }

  for (const record of grouped.values()) {
    record.points.sort((a, b) => a.year - b.year);
  }

  return [...grouped.values()];
}
