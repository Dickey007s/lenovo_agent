const fs = require('node:fs');
const path = require('node:path');
const { createRequire } = require('node:module');
const requireWeb = createRequire(path.resolve(__dirname, '../../../apps/web/package.json'));
const React = requireWeb('react');
const { renderToStaticMarkup } = requireWeb('react-dom/server');
const tabler = requireWeb('@tabler/icons-react');
const names = [...new Set([...['index.html','model.js','presenter.js','app.js'].map(name => fs.readFileSync(path.join(__dirname,name),'utf8')).join('\n').matchAll(/Icon[A-Z][A-Za-z]+/g)].map(match => match[0]))];
const icons = Object.fromEntries(names.map(name => {
  if (!tabler[name]) throw new Error(`Unknown icon ${name}`);
  return [name, renderToStaticMarkup(React.createElement(tabler[name], {size:20,stroke:1.65,'aria-hidden':true}))];
}));
fs.writeFileSync(path.join(__dirname,'icons.js'), '// Generated local Tabler icons. MIT; see TABLER-LICENSE.\nwindow.BOUNDARY_ICONS = '+JSON.stringify(icons)+';\n');
fs.copyFileSync(path.join(path.dirname(requireWeb.resolve('@tabler/icons-react/package.json')),'LICENSE'),path.join(__dirname,'TABLER-LICENSE'));
const researchFile = path.join(__dirname,'research','presentation.json');
if (fs.existsSync(researchFile)) {
  const presentation = JSON.parse(fs.readFileSync(researchFile,'utf8'));
  const ledger = JSON.parse(fs.readFileSync(path.join(__dirname,'research','sources.json'),'utf8'));
  const data = { sources: presentation.sources.map(item => {
    const source = ledger.sources.find(source => source.id === item.id);
    if (!source) throw new Error(`Unknown source ${item.id}`);
    return {...item,title:source.title,url:source.url,date:source.date || `访问 ${source.verified_at}`};
  }) };
  for (const s of data.sources) {
    if (!/^https:\/\//.test(s.url)) throw new Error(`Invalid source URL ${s.id}`);
    for (const key of ['id','title','date','type','observation','implication','limitation']) if (!s[key]) throw new Error(`Missing ${key} on ${s.id}`);
  }
  fs.writeFileSync(path.join(__dirname,'research-data.js'),'// Generated from research/presentation.json.\nwindow.BOUNDARY_RESEARCH = '+JSON.stringify(data).replace(/</g,'\\u003c')+';\n');
}
const followupRoot = path.join(__dirname,'research','followup-20260912');
const followup = ['papers.json','engineering.json'].flatMap(file=>JSON.parse(fs.readFileSync(path.join(followupRoot,file),'utf8')).sources);
const ids = new Set();
for(const s of followup) {
  if(ids.has(s.id)) throw new Error(`Duplicate follow-up ID: ${s.id}`);
  ids.add(s.id);
  if(new URL(s.url).protocol !== 'https:') throw new Error(`Invalid follow-up URL: ${s.id}`);
  for(const key of ['id','title','date','type','source_claim','read_scope','design_inference','testable_counterexample']) if(!s[key]) throw new Error(`Missing ${key}: ${s.id}`);
  if(![1,2,3].includes(s.priority) || !Array.isArray(s.limitations) || !s.limitations.length) throw new Error(`Missing priority/limits: ${s.id}`);
}
fs.writeFileSync(path.join(__dirname,'followup-data.js'),'// Generated from research/followup-20260912 canonical ledgers.\nwindow.BOUNDARY_FOLLOWUP = '+JSON.stringify({sources:followup}).replace(/</g,'\\u003c')+';\n');
console.log(`Built ${names.length} local icons, initial research and ${followup.length} follow-up sources.`);
