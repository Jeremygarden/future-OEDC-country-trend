import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import { timeSeriesRepository } from '../services/timeseries-repository.js';

const querySchema = z.object({
  country: z.string().trim().min(2).max(3).optional(),
  indicator: z.string().trim().min(1).optional(),
  fromYear: z.coerce.number().int().min(1900).max(2100).optional(),
  toYear: z.coerce.number().int().min(1900).max(2100).optional()
});

const timeseriesRoute: FastifyPluginAsync = async (app) => {
  app.get('/timeseries', async (request, reply) => {
    const parsed = querySchema.safeParse(request.query);

    if (!parsed.success) {
      return reply.badRequest(
        `Invalid timeseries query parameters: ${parsed.error.issues.map((issue) => `${issue.path.join('.')}: ${issue.message}`).join('; ')}`
      );
    }

    const query = parsed.data;
    const country = query.country?.toUpperCase();
    const indicator = query.indicator?.toUpperCase();

    const all = await timeSeriesRepository.list();

    const filtered = all
      .filter((point) => (country ? point.countryCode === country : true))
      .filter((point) => (indicator ? point.indicator.toUpperCase() === indicator : true))
      .filter((point) => (query.fromYear ? point.year >= query.fromYear : true))
      .filter((point) => (query.toYear ? point.year <= query.toYear : true))
      .sort((a, b) => a.year - b.year);

    return {
      total: filtered.length,
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
