const { Schema, model } = require('mongoose');

const JobSchema = new Schema({
  type: { type: String, required: true, enum: ['scrape','ml-train','ml-infer'] },
  payload: { type: Schema.Types.Mixed, default: {} },
  priority: { type: Number, default: 0 },
  status: { type: String, default: 'queued', enum: ['queued','running','succeeded','failed','cancelled'] },
  attempts: { type: Number, default: 0 },
  maxAttempts: { type: Number, default: 3 },
  leaseUntil: { type: Date, default: null },
  result: { type: Schema.Types.Mixed, default: null },
  error:  { type: Schema.Types.Mixed, default: null },
  createdBy: { type: String, default: 'api' }
}, { timestamps: true });

JobSchema.index({ status: 1, priority: -1, createdAt: 1 });
JobSchema.index({ leaseUntil: 1 });

module.exports = model('Job', JobSchema);
