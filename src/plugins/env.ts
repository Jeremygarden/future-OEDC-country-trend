import { z } from 'zod';

const EnvSchema = z.object({
  NODE_ENV: z.enum(['development', 'test', 'production']).default('development'),
  PORT: z.coerce.number().int().positive().default(3000),
  HOST: z.string().default('0.0.0.0')
});

export type AppEnv = z.infer<typeof EnvSchema>;

export function loadEnv(env: NodeJS.ProcessEnv): AppEnv {
  return EnvSchema.parse(env);
}
