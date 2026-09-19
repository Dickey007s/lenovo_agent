import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const require = createRequire('C:/Users/73811/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/package.json');
const sharp = require('sharp');
const ROOT = path.dirname(fileURLToPath(import.meta.url));
const WORKSPACE = path.resolve(ROOT, '../../..');
const pages = JSON.parse(await fs.readFile(path.join(ROOT, 'annotations.json'), 'utf8'));
const OUT = path.join(ROOT, 'images');
await fs.mkdir(OUT, { recursive: true });
await fs.mkdir(path.join(ROOT, 'sources'), { recursive: true });
await fs.mkdir(path.join(ROOT, '.build'), { recursive: true });

const W = 3840, H = 2160;
const C = { blue: '#1557D2', text: '#182230', gray: '#526174', rule: '#DCE3EC', green: '#008260' };
const escape = (s) => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;');
const text = (x, y, value, size = 36, color = C.text, weight = 400) => `<text x="${x}" y="${y}" font-size="${size}" fill="${color}" font-weight="${weight}">${escape(value)}</text>`;
const svg = (body) => `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}"><g font-family="Microsoft YaHei, Arial, sans-serif">${body}</g></svg>`;
const badge = (x, y, letter, r = 30) => `<circle cx="${x}" cy="${y}" r="${r}" fill="${C.blue}" stroke="#FFFFFF" stroke-width="4"/>${text(x, y + 14, letter, 40, '#FFFFFF', 700).replace('<text ', '<text text-anchor="middle" ')}`;
const geometry = [];
const textChecks = [];

async function assertTextFits(value, size, availableWidth, weight = 400) {
  const single = `<svg xmlns="http://www.w3.org/2000/svg" width="3840" height="150"><g font-family="Microsoft YaHei, Arial, sans-serif">${text(10, 100, value, size, '#182230', weight)}</g></svg>`;
  const measured = await sharp(Buffer.from(single)).trim().png().toBuffer({ resolveWithObject: true });
  const actualWidth = measured.info.width;
  if (actualWidth > availableWidth) throw new Error(`Text overflow: ${actualWidth} > ${availableWidth}: ${value}`);
  textChecks.push({ text: value, actualWidth, availableWidth });
}

for (const page of pages) {
  if (page.modules.map(m => m.key).join('') !== 'ABCDEF') throw new Error(`${page.id}: incorrect module mapping`);
  for (const step of page.steps) await assertTextFits(step, 34, 675);
  for (const mod of page.modules) {
    await assertTextFits(mod.title, 42, 874, 700);
    for (const line of mod.lines) await assertTextFits(line, 35, 959);
  }
  await assertTextFits(page.entry, 34, 3648);
  await assertTextFits(page.takeaway, 34, 3648, 700);
  await assertTextFits(page.provenance, 28, 3370);
  const source = path.join(WORKSPACE, page.source);
  const sourceBytes = await fs.readFile(source);
  const metadata = await sharp(sourceBytes).metadata();
  const scale = Math.min(2508 / metadata.width, 1410 / metadata.height);
  const width = Math.round(metadata.width * scale), height = Math.round(metadata.height * scale);
  const left = Math.round(150 + (2508 - width) / 2), top = 390;
  const resized = await sharp(sourceBytes).resize(width, height, { kernel: 'lanczos3' }).png().toBuffer();
  await fs.copyFile(source, path.join(ROOT, 'sources', `${page.id}-original.png`));

  let body = `<rect width="${W}" height="${H}" fill="#FFFFFF"/>`;
  body += text(96, 116, `${page.id}  ${page.name}`, 68, C.text, 700);
  body += text(96, 184, page.subtitle, 36, C.gray);
  body += text(3744, 117, 'OFFICE AGENT', 32, C.blue, 700).replace('<text ', '<text text-anchor="end" ');
  body += `<rect x="96" y="235" width="3648" height="86" fill="#F0F5FD"/>`;
  body += text(127, 291, '操作流程', 36, C.blue, 700);
  page.steps.forEach((step, i) => {
    const x = 430 + i * 818;
    body += badge(x, 278, String(i + 1), 24);
    body += text(x + 46, 292, step, 34);
    if (i < 3) body += text(x + 731, 292, '→', 40, '#8A99AD');
  });
  body += text(150, 367, '页面截图 · 蓝色字母对应右侧说明', 28, C.gray);
  body += text(2785, 367, '模块含义', 32, C.blue, 700);
  body += `<rect x="${left - 2}" y="${top - 2}" width="${width + 4}" height="${height + 4}" fill="#FFFFFF" stroke="${C.rule}" stroke-width="2"/>`;
  page.modules.forEach((mod, i) => {
    const y = 447 + i * 219;
    body += badge(2815, y - 15, mod.key);
    body += text(2870, y, mod.title, 42, C.text, 700);
    mod.lines.forEach((line, lineIndex) => { body += text(2785, y + 71 + lineIndex * 55, line, 35, C.gray); });
    if (i < 5) body += `<line x1="2785" y1="${y + 163}" x2="3744" y2="${y + 163}" stroke="${C.rule}" stroke-width="2"/>`;
  });
  body += `<line x1="96" y1="1870" x2="3744" y2="1870" stroke="${C.rule}" stroke-width="2"/>`;
  body += text(96, 1930, page.entry, 34, C.text);
  body += text(96, 1993, page.takeaway, 34, C.green, 700);
  body += text(96, 2080, page.provenance, 28, C.gray);
  body += text(3744, 2080, `${page.id} / 04`, 28, C.gray).replace('<text ', '<text text-anchor="end" ');

  let overlay = '';
  const overlayRects = [];
  const exclusionBounds = [];
  for (const mod of page.modules) {
    for (const [x, y, w, h] of mod.rects) {
      const box = { x: left + x * scale, y: top + y * scale, w: w * scale, h: h * scale };
      // Sparse corners identify modules without tinting or covering their content.
      const n = 20, d = `M ${box.x} ${box.y+n} V ${box.y} H ${box.x+n} M ${box.x+box.w-n} ${box.y} H ${box.x+box.w} V ${box.y+n} M ${box.x+box.w} ${box.y+box.h-n} V ${box.y+box.h} H ${box.x+box.w-n} M ${box.x+n} ${box.y+box.h} H ${box.x} V ${box.y+box.h-n}`;
      overlay += `<path d="${d}" fill="none" stroke="${C.blue}" stroke-width="3" opacity="0.82"/>`;
      overlayRects.push({ key: mod.key, ...box });
      for (const [cx, cy] of [[box.x,box.y],[box.x+box.w,box.y],[box.x,box.y+box.h],[box.x+box.w,box.y+box.h]]) exclusionBounds.push([cx - 25, cy - 25, 50, 50]);
    }
    const bx = left + mod.marker[0] * scale, by = top + mod.marker[1] * scale;
    overlay += badge(bx, by, mod.key, 29);
    exclusionBounds.push([bx - 34, by - 34, 68, 68]);
  }
  const base = await sharp(Buffer.from(svg(body))).png().toBuffer();
  const composite = await sharp(base).composite([{ input: resized, left, top }]).png().toBuffer();
  const output = await sharp(composite).composite([{ input: Buffer.from(svg(overlay)), left: 0, top: 0 }]).png().toBuffer();
  const filename = `${page.id}-${page.name}-操作与模块标注.png`;
  await fs.writeFile(path.join(OUT, filename), output);
  await fs.writeFile(path.join(ROOT, '.build', `${page.id}-layout.svg`), svg(body));

  // Compare the screenshot region outside the explicitly declared annotation marks.
  const expected = await sharp(resized).ensureAlpha().raw().toBuffer();
  const actual = await sharp(output).extract({ left, top, width, height }).ensureAlpha().raw().toBuffer();
  let checked = 0, changed = 0;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const px = left + x, py = top + y;
    if (exclusionBounds.some(([ex, ey, ew, eh]) => px >= ex && px <= ex + ew && py >= ey && py <= ey + eh)) continue;
    const p = (y * width + x) * 4;
    checked++;
    if (expected[p] !== actual[p] || expected[p+1] !== actual[p+1] || expected[p+2] !== actual[p+2] || expected[p+3] !== actual[p+3]) changed++;
  }
  if (changed !== 0) throw new Error(`${page.id}: ${changed} unexpected screenshot pixel changes`);
  geometry.push({ id: page.id, filename, source: page.source, width: W, height: H, screenshot: { left, top, width, height }, checkedScreenshotPixels: checked, unexpectedChangedPixels: changed, overlayRects });
  console.log(`${filename}: ${W}x${H}; ${checked} screenshot pixels checked, ${changed} unexpected changes`);
}
await fs.writeFile(path.join(ROOT, '.build', 'verification.json'), JSON.stringify({ date: '2026-09-13', images: geometry, textChecks }, null, 2));

const items = pages.map(page => `<section><h2>${page.id} ${page.name}</h2><a href="images/${page.id}-${page.name}-操作与模块标注.png"><img src="images/${page.id}-${page.name}-操作与模块标注.png" alt="${page.name}：操作流程与模块标注"/></a></section>`).join('\n');
await fs.writeFile(path.join(ROOT, 'index.html'), `<!doctype html><html lang="zh-CN"><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Office Agent 系统演示图片</title><style>*{box-sizing:border-box}body{margin:0;background:#f4f6f9;color:#182230;font:16px "Microsoft YaHei",Arial,sans-serif}header{background:white;border-bottom:1px solid #dce3ec;padding:28px 4%}h1{font-size:26px;margin:0 0 12px}p{color:#526174;margin:0;line-height:1.7}main{max-width:1680px;margin:24px auto;padding:0 24px}section{margin-bottom:32px}h2{font-size:20px}img{display:block;width:100%;height:auto;border:1px solid #dce3ec}a{color:#1557d2}footer{padding:24px 4%;color:#526174}</style><header><h1>Office Agent 系统演示图片</h1><p>原系统四个视图的操作与模块说明，3840 × 2160 PNG。<a href="系统演示图片-4张.zip">下载四图压缩包</a></p></header><main>${items}</main><footer>原截图为 2026-09-11 / 12 受控测试状态，未用生成模型重绘。四个视图不是四个独立系统，也不组成同一次模型运行。</footer></html>`);
