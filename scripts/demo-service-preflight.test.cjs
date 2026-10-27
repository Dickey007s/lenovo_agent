const { test } = require('node:test');
const assert = require('node:assert/strict');
const { checkDemoService } = require('./demo-service-preflight.cjs');

test('current API is accepted without starting a run', async () => {
  const urls = [];
  const result = await checkDemoService('http://localhost:8000', async url => {
    urls.push(url);
    return { ok: true, json: async () => ({ components: { schemas: { HarnessRunStart: {
      properties: { execution_policy: { enum: ['manual', 'automatic_readonly'] } },
    } } } }) };
  });
  assert.equal(result.automaticReadonlySupported, true);
  assert.deepEqual(urls, ['http://localhost:8000/openapi.json']);
});

test('old API fails before paid work', async () => {
  await assert.rejects(checkDemoService('http://localhost:8000', async () => ({
    ok: true, json: async () => ({ components: { schemas: { HarnessRunStart: { properties: {} } } } }),
  })), /outdated/);
});

test('unavailable API fails explicitly', async () => {
  await assert.rejects(checkDemoService('http://localhost:8000', async () => ({
    ok: false, status: 503,
  })), /HTTP 503/);
});
