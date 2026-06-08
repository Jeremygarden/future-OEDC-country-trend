import { createApp } from './app.js';
import { loadEnv } from './plugins/env.js';

const env = loadEnv(process.env);
const app = createApp();

const start = async () => {
  try {
    await app.listen({
      port: env.PORT,
      host: env.HOST
    });
  } catch (error) {
    app.log.error(error);
    process.exit(1);
  }
};

void start();
