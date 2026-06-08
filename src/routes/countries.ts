import type { FastifyPluginAsync } from 'fastify';
import { z } from 'zod';
import {
  DEFAULT_STATE,
  average,
  filterAndSortCountries,
  type DashboardState,
  type SortField
} from '../core/dashboard.js';
import { countryRepository } from '../services/country-repository.js';

const sortFieldSchema = z.enum([
  'population',
  'gdpPerCapita',
  'lifeExpectancy',
  'internetUsers',
  'co2PerCapita'
]);

const querySchema = z.object({
  search: z.string().optional(),
  region: z.string().optional(),
  sortBy: sortFieldSchema.optional(),
  limit: z.coerce.number().int().positive().max(1000).optional(),
  offset: z.coerce.number().int().min(0).optional()
});

function parseQuery(query: unknown): z.infer<typeof querySchema> {
  const result = querySchema.safeParse(query);

  if (!result.success) {
    const message = result.error.issues.map((issue) => `${issue.path.join('.') || 'query'}: ${issue.message}`).join('; ');
    throw appHttpError(400, `Invalid country query parameters: ${message}`);
  }

  return result.data;
}

function appHttpError(statusCode: number, message: string): Error & { statusCode: number } {
  const error = new Error(message) as Error & { statusCode: number };
  error.statusCode = statusCode;
  return error;
}

function toState(query: z.infer<typeof querySchema>): DashboardState {
  const sortBy = (query.sortBy ?? DEFAULT_STATE.sortBy) as SortField;

  return {
    search: query.search ?? DEFAULT_STATE.search,
    region: query.region ?? DEFAULT_STATE.region,
    sortBy
  };
}

const countriesRoute: FastifyPluginAsync = async (app) => {
  app.get('/countries', async (request) => {
    const query = parseQuery(request.query);
    const state = toState(query);

    const countries = await countryRepository.list();
    const filtered = filterAndSortCountries(countries, state);
    const limit = query.limit ?? filtered.length;
    const offset = query.offset ?? 0;
    const items = filtered.slice(offset, offset + limit);

    return {
      total: filtered.length,
      limit,
      offset,
      items
    };
  });

  app.get('/countries/summary', async (request) => {
    const query = parseQuery(request.query);
    const state = toState(query);

    const countries = await countryRepository.list();
    const filtered = filterAndSortCountries(countries, state);
    const totalPopulation = filtered.reduce((sum, country) => sum + country.population, 0);

    return {
      totalCountries: filtered.length,
      totalPopulation,
      averageGdpPerCapita: average(filtered, 'gdpPerCapita'),
      averageLifeExpectancy: average(filtered, 'lifeExpectancy'),
      averageInternetUsers: average(filtered, 'internetUsers')
    };
  });
};

export default countriesRoute;
