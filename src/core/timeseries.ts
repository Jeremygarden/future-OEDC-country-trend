import { z } from 'zod';

export const timeSeriesPointSchema = z.object({
  countryCode: z.string().min(2).max(3).transform((value) => value.toUpperCase()),
  countryName: z.string().min(1),
  indicator: z.string().min(1),
  year: z.coerce.number().int().min(1900).max(2100),
  value: z.coerce.number().finite(),
  source: z.string().min(1).default('etl')
});

export const timeSeriesCollectionSchema = z.array(timeSeriesPointSchema);

export type TimeSeriesPoint = z.infer<typeof timeSeriesPointSchema>;
