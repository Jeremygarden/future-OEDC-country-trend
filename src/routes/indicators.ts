import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import { timeSeriesRepository } from '../services/timeseries-repository.js';

const indicatorsQuerySchema = z.object({
  country: z.string().trim().min(2).max(3).optional()
});

const compareQuerySchema = z.object({
  countries: z.string().min(1),
  indicator: z.string().trim().min(1)
});

const indicatorsRoute: FastifyPluginAsync = async (app) => {
  app.get('/indicators', async (request, reply) => {
    const parsed = indicatorsQuerySchema.safeParse(request.query);

    if (!parsed.success) {
      return reply.badRequest(
        `Invalid indicators query parameters: ${parsed.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; ')}`
      );
    }

    const country = parsed.data.country?.toUpperCase();
    const points = await timeSeriesRepository.list();

    const byCountry = new Map<string, { countryCode: string; countryName: string; indicators: Set<string> }>();

    for (const point of points) {
      if (country && point.countryCode !== country) continue;

      if (!byCountry.has(point.countryCode)) {
        byCountry.set(point.countryCode, {
          countryCode: point.countryCode,
          countryName: point.countryName,
          indicators: new Set<string>()
        });
      }

      byCountry.get(point.countryCode)?.indicators.add(point.indicator);
    }

    const items = [...byCountry.values()]
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

  app.get('/compare', async (request, reply) => {
    const parsed = compareQuerySchema.safeParse(request.query);

    if (!parsed.success) {
      return reply.badRequest(
        `Invalid compare query parameters: ${parsed.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; ')}`
      );
    }

    const countries = parsed.data.countries
      .split(',')
      .map((value) => value.trim().toUpperCase())
      .filter(Boolean);

    const indicator = parsed.data.indicator.toUpperCase();
    const points = await timeSeriesRepository.list();

    const selected = points.filter(
      (point) => countries.includes(point.countryCode) && point.indicator.toUpperCase() === indicator
    );

    const grouped = countries.map((countryCode) => {
      const countryPoints = selected
        .filter((point) => point.countryCode === countryCode)
        .sort((a, b) => a.year - b.year);

      return {
        countryCode,
        countryName: countryPoints[0]?.countryName ?? null,
        indicator,
        latest: countryPoints.length > 0 ? countryPoints[countryPoints.length - 1] : null,
        points: countryPoints
      };
    });

    return {
      countries,
      indicator,
      compared: grouped.length,
      items: grouped
    };
  });
};

export default indicatorsRoute;
