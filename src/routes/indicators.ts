import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import type { TimeSeriesPoint } from '../core/timeseries.js';
import { appHttpError } from '../core/http-error.js';
import { timeSeriesRepository } from '../services/timeseries-repository.js';

const indicatorsQuerySchema = z.object({
  country: z.string().trim().min(2).max(3).optional()
});

const compareQuerySchema = z.object({
  countries: z.string().min(1),
  indicator: z.string().trim().min(1)
});

interface IndicatorIndexEntry {
  countryCode: string;
  countryName: string;
  indicators: Set<string>;
}

function validationDetails(error: z.ZodError) {
  return error.issues.map((issue) => ({
    path: issue.path.join('.'),
    message: issue.message
  }));
}

function buildIndicatorIndex(points: TimeSeriesPoint[], country?: string): IndicatorIndexEntry[] {
  const byCountry = new Map<string, IndicatorIndexEntry>();

  for (const point of points) {
    if (country && point.countryCode !== country) continue;

    let entry = byCountry.get(point.countryCode);
    if (!entry) {
      entry = {
        countryCode: point.countryCode,
        countryName: point.countryName,
        indicators: new Set<string>()
      };
      byCountry.set(point.countryCode, entry);
    }

    entry.indicators.add(point.indicator);
  }

  return [...byCountry.values()];
}

function groupPointsForComparison(points: TimeSeriesPoint[], countries: string[], indicator: string) {
  const requestedCountries = new Set(countries);
  const selectedByCountry = new Map<string, TimeSeriesPoint[]>();

  for (const point of points) {
    if (!requestedCountries.has(point.countryCode) || point.indicator.toUpperCase() !== indicator) continue;

    const countryPoints = selectedByCountry.get(point.countryCode) ?? [];
    countryPoints.push(point);
    selectedByCountry.set(point.countryCode, countryPoints);
  }

  return countries.map((countryCode) => {
    const countryPoints = (selectedByCountry.get(countryCode) ?? []).sort((a, b) => a.year - b.year);

    return {
      countryCode,
      countryName: countryPoints[0]?.countryName ?? null,
      indicator,
      latest: countryPoints.length > 0 ? countryPoints[countryPoints.length - 1] : null,
      points: countryPoints
    };
  });
}

const indicatorsRoute: FastifyPluginAsync = async (app) => {
  app.get('/indicators', async (request) => {
    const parsed = indicatorsQuerySchema.safeParse(request.query);

    if (!parsed.success) {
      throw appHttpError(
        400,
        'INVALID_INDICATORS_QUERY',
        'Invalid indicators query parameters',
        validationDetails(parsed.error)
      );
    }

    const country = parsed.data.country?.toUpperCase();
    const points = await timeSeriesRepository.list();
    const index = buildIndicatorIndex(points, country);

    const items = index
      .map((entry) => ({
        countryCode: entry.countryCode,
        countryName: entry.countryName,
        indicators: [...entry.indicators].sort()
      }))
      .sort((a, b) => a.countryCode.localeCompare(b.countryCode));

    return {
      totalCountries: items.length,
      items
    };
  });

  app.get('/compare', async (request) => {
    const parsed = compareQuerySchema.safeParse(request.query);

    if (!parsed.success) {
      throw appHttpError(
        400,
        'INVALID_COMPARE_QUERY',
        'Invalid compare query parameters',
        validationDetails(parsed.error)
      );
    }

    const countries = parsed.data.countries
      .split(',')
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);

    const indicator = parsed.data.indicator.toUpperCase();
    const points = await timeSeriesRepository.list();
    const grouped = groupPointsForComparison(points, countries, indicator);

    return {
      countries,
      indicator,
      compared: grouped.length,
      items: grouped
    };
  });
};

export default indicatorsRoute;
