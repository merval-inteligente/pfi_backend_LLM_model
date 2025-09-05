const mongoose = require('mongoose');
const uri = process.env.MONGODB_URI;
const timeoutMS = Number(process.env.MONGODB_TIMEOUT_MS || 10000);

async function connectMongo() {
  await mongoose.connect(uri, {
    serverSelectionTimeoutMS: timeoutMS,
    socketTimeoutMS: timeoutMS,
    maxPoolSize: 20,
    minPoolSize: 2,
    retryWrites: true,
    appName: 'jobs-orchestrator'
  });
  console.log('[api] Mongo conectado');
}
function isHealthy() { return mongoose.connection.readyState === 1; }
async function disconnectMongo() { await mongoose.connection.close(); }
module.exports = { connectMongo, disconnectMongo, isHealthy };
