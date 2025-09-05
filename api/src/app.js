// app.js
require('dotenv').config();
const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const morgan = require('morgan');
const rateLimit = require('express-rate-limit');

const { isHealthy } = require('./db/mongo');
const jobsRouter = require('./routes/jobs.routes');

const app = express();
app.use(helmet());
app.use(cors());
app.use(express.json({ limit: '1mb' }));
app.use(morgan('dev'));
app.use(rateLimit({ windowMs: 60_000, max: 120 }));

app.get('/health', (req, res) => res.json({ ok: true, dbHealthy: isHealthy(), ts: Date.now() }));
app.use('/api/jobs', jobsRouter);

module.exports = app;
