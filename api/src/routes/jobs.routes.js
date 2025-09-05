const router = require('express').Router();
const ctrl = require('../controllers/jobs.controller');

router.post('/scrape', ctrl.createScrape);
router.post('/ml/train', ctrl.createMlTrain);
router.post('/ml/infer', ctrl.createMlInfer);

router.get('/:id', ctrl.getById);
router.post('/:id/cancel', ctrl.cancel);

// opcional: callback
router.post('/callback/:id', ctrl.callbackDone);

module.exports = router;
