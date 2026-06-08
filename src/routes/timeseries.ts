import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import { appHttpError } from '../core/http-error.js';
import { timeSeriesRepository } from '../services/timeseries-repository.js';
import { timeseriesLruCache } from '../services/timeseries-cache.js';

const querySchema = z.object({
  country: z.string().trim().min(2).max(3).optional(),
  indicator: z.string().trim().min(1).optional(),
  fromYear: z.coerce.number().int().min(1900).max(2100).optional(),
  toYear: z.coerce.number().int().min(1900).max(2100).optional()
});

const timeseriesRoute: FastifyPluginAsync = async (app) => {
  app.get('/timeseries', async (request) => {
    const parsed = querySchema.safeParse(request.query);

    if (!parsed.success) {
      throw appHttpError(
        400,
        'INVALID_TIMESERIES_QUERY',
        'Invalid timeseries query parameters',
        parsed.error.issues.map((issue) => ({
          path: issue.path.join('.'),
          message: issue.message
        }))
      );
    }

    const query = parsed.data;

    if (query.fromYear && query.toYear && query.fromYear > query.toYear) {
      throw appHttpError(400, 'INVALID_YEAR_RANGE', '`fromYear` must be <= `toYear`');
    }

    const country = query.country?.toUpperCase();
    const indicator = query.indicator?.toUpperCase();
    const cacheKey = JSON.stringify({
      country: country ?? null,
      indicator: indicator ?? null,
      fromYear: query.fromYear ?? null,
      toYear: query.toYear ?? null
    });

    const cached = timeseriesLruCache.get(cacheKey);
    if (cached) {
      return {
        total: cached.length,
        cached: true,
        cache: timeseriesLruCache.stats(),
        query: {
          country: country ?? null,
          indicator: indicator ?? null,
          fromYear: query.fromYear ?? null,
          toYear: query.toYear ?? null
        },
        items: cached
      };
    }

    const all = await timeSeriesRepository.list();

    const filtered = all
      .filter((point) => (country ? point.countryCode === country : true))
      .filter((point) => (indicator ? point.indicator.toUpperCase() === indicator : true))
      .filter((point) => (query.fromYear ? point.year >= query.fromYear : true))
      .filter((point) => (query.toYear ? point.year <= query.toYear : true))
      .sort((a, b) => a.year - b.year);

    timeseriesLruCache.set(cacheKey, filtered);

    return {
      total: filtered.length,
      cached: false,
      cache: timeseriesLruCache.stats(),
      query: {
        country: country ?? null,
        indicator: indicator ?? null,
        fromYear: query.fromYear ?? null,
        toYear: query.toYear ?? null
      },
      items: filtered
    };
  });
};

export default timeseriesRoute;
