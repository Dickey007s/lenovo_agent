async function checkDemoService(api, request = fetch) {
  const response = await request(`${api}/openapi.json`);
  if (!response.ok) throw new Error(`Demo API schema unavailable: HTTP ${response.status}`);
  const schema = await response.json();
  const policy = schema.components?.schemas?.HarnessRunStart?.properties?.execution_policy;
  if (!policy?.enum?.includes('automatic_readonly')) {
    throw new Error('Demo API is outdated: automatic_readonly is not supported. Archive inactive runs and update the backend before starting model work.');
  }
  return { api, automaticReadonlySupported: true };
}

module.exports = { checkDemoService };

if (require.main === module) {
  checkDemoService(process.argv[2] || 'http://localhost:8000')
    .then(result => console.log(JSON.stringify(result)))
    .catch(error => { console.error(error.message); process.exitCode = 1; });
}
