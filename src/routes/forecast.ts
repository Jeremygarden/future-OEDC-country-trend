import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import {
  computeCagrForecast,
  computeLinearForecast,
  type ForecastMethod
} from '../core/forecast.js';
import { appHttpError } from '../core/http-error.js';
import { timeSeriesRepository } from '../services/timeseries-repository.js';

const forecastQuerySchema = z.object({
  country: z.string().trim().min(2).max(3),
  indicator: z.string().trim().min(1),
  yearsAhead: z.coerce.number().int().min(1).max(20).default(5),
  method: z.enum(['linear', 'cagr']).default('linear')
});

const forecastRoute: FastifyPluginAsync = async (app) => {
  app.get('/forecast', async (request) => {
    const parsed = forecastQuerySchema.safeParse(request.query);

    if (!parsed.success) {
      throw appHttpError(
        400,
        'INVALID_FORECAST_QUERY',
        'Invalid forecast query parameters',
        parsed.error.issues.map((issue) => ({
          path: issue.path.join('.'),
          message: issue.message
        }))
      );
    }

    const query = parsed.data;
    const country = query.country.toUpperCase();
    const indicator = query.indicator.toUpperCase();

    const history = (await timeSeriesRepository.list())
      .filter((point) => point.countryCode === country)
      .filter((point) => point.indicator.toUpperCase() === indicator)
      .sort((a, b) => a.year - b.year);

    if (history.length === 0) {
      throw appHttpError(
        404,
        'TIMESERIES_NOT_FOUND',
        `No time series found for country=${country} indicator=${indicator}`
      );
    }

    const method = query.method as ForecastMethod;
    const forecast =
      method === 'cagr'
        ? computeCagrForecast(history, query.yearsAhead)
        : computeLinearForecast(history, query.yearsAhead);

    return {
      country,
      indicator,
      method,
      yearsAhead: query.yearsAhead,
      history,
      forecast
    };
  });
};

export default forecastRoute;
