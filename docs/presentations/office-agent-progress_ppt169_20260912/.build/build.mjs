import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import xml from 'xml-js';
import { Presentation, PresentationFile, FileBlob } from '@oai/artifact-tool';

const BUILD = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(BUILD);
const SKILL = 'F:/CodexData/home/plugins/cache/openai-primary-runtime/presentations/26.909.11814/skills/presentations';
const PYTHON = 'C:/Users/73811/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe';
const FONT = 'Microsoft YaHei';
process.env.RUNTIME_NODE_MODULES = 'C:/Users/73811/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
process.env.RUNTIME_PYTHON = PYTHON;
const revision = process.argv[2] || '1';
const { finalizePresentation } = await import(pathToFileURL(path.join(SKILL, 'container_tools/artifact_tool_utils.mjs')).href);
const presentation = Presentation.create({ slideSize: { width: 1280, height: 720 } });

function content(node) {
  const spans = (node.elements || []).filter(e => e.name === 'tspan');
  if (spans.length) return spans.map(content).join('\n');
  return (node.elements || []).map(e => e.type === 'text' ? e.text : content(e)).join('');
}

function table(slide, node) {
  const a = node.attributes;
  const widths = a['data-widths'].split(',').map(Number);
  const heights = a['data-heights'].split(',').map(Number);
  const cells = node.elements.filter(e => e.name === 'text');
  const values = heights.map(() => widths.map(() => ''));
  for (const cell of cells) values[Number(cell.attributes['data-row'])][Number(cell.attributes['data-col'])] = content(cell);
  const t = slide.tables.add({
    rows: heights.length, columns: widths.length,
    left: Number(a['data-x']), top: Number(a['data-y']),
    width: widths.reduce((x, y) => x + y), height: heights.reduce((x, y) => x + y),
    columnWidths: widths, values,
  });
  t.styleOptions = { headerRow: false, bandedRows: false, firstColumn: false, lastColumn: false };
  t.borders.assign({ fill: '#DCE2E8', width: 1, style: 'solid' });
  heights.forEach((height, i) => { t.rows[i].height = height; });
  const range = t.cells.block({ row: 0, column: 0, rowCount: heights.length, columnCount: widths.length });
  range.assign({ fill: '#FFFFFF', margins: { left: 16, right: 16, top: 8, bottom: 8 }, anchor: 'center' });
  for (const cellNode of cells) {
    const ca = cellNode.attributes;
    const r = Number(ca['data-row']);
    const c = Number(ca['data-col']);
    const cell = t.getCell(r, c);
    cell.fill = r === 0 ? '#F4F6F8' : '#FFFFFF';
    cell.text.style = {
      typeface: FONT, fontSize: 24, color: ca.fill,
      bold: ca['font-weight'] === '700', alignment: 'left', verticalAlignment: 'middle',
      autoFit: 'none', wrap: 'none', insets: { left: 16, right: 16, top: 8, bottom: 8 },
    };
  }
}

async function visit(slide, node, sourceDir) {
  const a = node.attributes || {};
  if (a['data-native-table'] === 'true') { table(slide, node); return; }
  if (node.name === 'text') {
    const size = Number(a['font-size']);
    const shape = slide.shapes.add({
      name: content(node).slice(0, 40), geometry: 'textbox',
      position: { left: Number(a.x), top: Number(a.y) - size, width: Number(a['data-width']), height: size * 1.35 },
      fill: 'none', line: { fill: 'none', width: 0 },
    });
    shape.text = content(node);
    shape.text.style = {
      typeface: FONT, fontSize: size, bold: a['font-weight'] === '700', color: a.fill,
      autoFit: 'none', wrap: 'none', alignment: 'left', verticalAlignment: 'top',
      insets: { top: 0, bottom: 0, left: 0, right: 0 },
    };
    return;
  }
  if (node.name === 'image') {
    const filename = path.resolve(sourceDir, a.href);
    slide.images.add({
      blob: new Uint8Array(await fs.readFile(filename)), contentType: 'image/png',
      alt: path.basename(filename), fit: 'contain',
      position: { left: Number(a.x), top: Number(a.y), width: Number(a.width), height: Number(a.height) },
    });
    return;
  }
  for (const child of node.elements || []) await visit(slide, child, sourceDir);
}

const sourceDir = path.join(ROOT, 'svg_output');
const files = (await fs.readdir(sourceDir)).filter(f => f.endsWith('.svg')).sort();
if (files.length !== 6) throw new Error('Expected six SVG pages');
const notes = [];
for (const filename of files) {
  const slide = presentation.slides.add();
  slide.background.fill = '#FFFFFF';
  await visit(slide, xml.xml2js(await fs.readFile(path.join(sourceDir, filename), 'utf8'), { compact: false }), sourceDir);
  const note = await fs.readFile(path.join(ROOT, 'notes', filename.replace('.svg', '.md')), 'utf8');
  slide.speakerNotes.textFrame.setText(note);
  notes.push(`# ${filename.replace('.svg', '')}\n\n${note}`);
}
await fs.mkdir(path.join(ROOT, 'exports'), { recursive: true });
await fs.mkdir(path.join(BUILD, `render-${revision}`), { recursive: true });
const candidatePath = path.join(BUILD, `candidate-${revision}.pptx`);
await (await PresentationFile.exportPptx(presentation)).save(candidatePath);
console.log('Draft exported:', candidatePath);
for (let i = 0; i < files.length; i++) {
  const preview = await presentation.export({ slide: presentation.slides.items[i], format: 'png', scale: 1.5 });
  await fs.writeFile(path.join(BUILD, `render-${revision}`, `slide-${i + 1}.png`), new Uint8Array(await preview.arrayBuffer()));
  const layout = await presentation.slides.items[i].export({ format: 'layout' });
  await fs.writeFile(path.join(BUILD, `render-${revision}`, `slide-${i + 1}.layout.json`), await layout.text());
  console.log('Rendered draft slide', i + 1);
}
const finalPath = path.join(ROOT, 'exports', `Office-Agent-系统优化与人机共驾调研-6页${revision === '1' ? '' : `-v${revision}`}.pptx`);
const result = await finalizePresentation({
  workspaceDir: ROOT, candidatePath, finalPath, pythonExecutable: PYTHON,
  integrityValidatorPath: path.join(SKILL, 'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath: path.join(SKILL, 'container_tools/inspect_presentation_layout_geometry.py'),
  explicitTotalSlideCount: 6,
  requiredNativeTableOwnerSlides: [5], requiredNativeChartOwnerSlides: [],
  layoutArgs: ['--expected-slide-size-emu', '12192000,6858000', '--validate-bullet-geometry', '--validate-heading-fit', '--require-native-table-slide', '5'],
  fontPolicy: { basis: 'design', families: [FONT] },
  verifyArtifactToolImport: true,
  receiptPath: path.join(BUILD, `validation-${revision}.json`),
});
console.log('Finalized', JSON.stringify(result));
const final = await PresentationFile.importPptx(await FileBlob.load(finalPath));
await fs.mkdir(path.join(BUILD, `final-render-${revision}`), { recursive: true });
for (let i = 0; i < final.slides.items.length; i++) {
  const png = await final.export({ slide: final.slides.items[i], format: 'png', scale: 1.5 });
  await fs.writeFile(path.join(BUILD, `final-render-${revision}`, `slide-${i + 1}.png`), new Uint8Array(await png.arrayBuffer()));
  console.log('Rendered final slide', i + 1);
}
await fs.writeFile(path.join(ROOT, 'exports', '逐页讲稿与论文链接.md'), notes.join('\n\n'));
console.log('FINAL_PPTX', finalPath);
