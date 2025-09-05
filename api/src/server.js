// server.js
const app = require('./app');
const { connectMongo, disconnectMongo } = require('./db/mongo');

const PORT = process.env.PORT || 3000;
(async () => {
  try {
    await connectMongo();
    const server = app.listen(PORT, () => console.log(`API en http://localhost:${PORT}`));
    const shutdown = (sig) => {
      console.log(`[${sig}] cerrando...`);
      server.close(async () => { await disconnectMongo(); process.exit(0); });
      setTimeout(() => process.exit(1), 5000).unref();
    };
    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));
  } catch (e) { console.error('No se pudo iniciar API', e); process.exit(1); }
})();
