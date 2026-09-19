import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
const require = createRequire('C:/Users/73811/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/package.json');
const sharp = require('sharp');
const root = path.dirname(fileURLToPath(import.meta.url));
const out = path.join(root, 'in-image');
await fs.mkdir(out, { recursive: true });
const esc = s => String(s).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
const color = '#BB361F';
const pages = [
  {
    id: '01', name: '任务进展',
    flow: [820, 107, 694, '看执行进展 → 处理待办 → 核对依据 → 按分支继续'],
    labels: [
      [1210, 211, 324, 44, ['1 当前运行：任务与 Run 状态'], 'M1534 233 H1554 V78 H1460 V53'],
      [584, 211, 406, 44, ['2 视图切换：进展看执行，协作看分工'], 'M584 233 H485'],
      [686, 274, 556, 24, ['3 执行阶段：读取 → 拆解 → 形成结论 → 核对 → 保留'], 'M686 286 H624 V318 H603'],
      [816, 537, 458, 38, ['4 待办入口：先选引用位置，再继续'], 'M1274 556 H1300 V492 H1320'],
      [1035, 733, 476, 38, ['5 分支：只处理选中项，其余成果保留'], 'M1035 752 H974'],
      [516, 851, 600, 47, ['6 成果与版本：查看草稿 / 历史，不覆盖旧成果'], 'M1116 875 H1150 V825 H1480 V822']
    ]
  },
  {
    id: '02', name: '执行记录',
    flow: [780, 104, 742, '选轮次 → 展开分支 → 看资料与阶段 → 处理该项 / 查版本'],
    labels: [
      [129, 422, 165, 79, ['1 轮次与历史', '按轮回看过程'], 'M212 422 V378'],
      [775, 277, 491, 39, ['2 概览：累计轮次 / 分支 / 当前待确认数'], 'M1018 277 V247 H879'],
      [568, 450, 270, 74, ['3 资料与阶段', '看本轮来源和核验位置'], 'M568 487 H536 V448 H491'],
      [1090, 431, 272, 67, ['4 只处理这一项', '核对或恢复当前分支'], 'M1362 467 H1377 V482'],
      [660, 733, 558, 35, ['5 本轮成果：保留草稿，按版本查看变化'], 'M1218 750 H1463 V771'],
      [911, 850, 471, 37, ['6 审计回执：展开查看事件与模型调用'], 'M1382 869 H1505']
    ]
  },
  {
    id: '03', name: '蜂群协作',
    flow: [790, 92, 548, '看分工与依赖 → 确认本批 → 查看贡献采用'],
    labels: [
      [795, 190, 542, 43, ['1 协作范围：单进程只读，每批最多 3 个'], 'M795 212 H750 V229 H670'],
      [545, 383, 504, 35, ['2 调用与采用分开：返回不等于进入成果'], 'M745 383 V352'],
      [520, 648, 542, 36, ['3 工作包：每个框是一项分工及其当前状态'], 'M520 666 H311'],
      [72, 711, 332, 68, ['4 连线表示前置依赖', '不是多个 Worker 正在并行'], 'M404 741 H508'],
      [1110, 382, 235, 34, ['5 看谁受阻、谁可继续'], 'M1228 416 V435'],
      [1111, 889, 230, 77, ['6 确认本批后才执行', '就绪不等于已经派发'], 'M1226 889 V861'],
      [520, 951, 520, 34, ['7 协作结果：已返回 / 已采用 / 成果版本'], 'M760 985 V1000']
    ]
  },
  {
    id: '04', name: '证据核对',
    flow: [1040, 102, 560, '读原因 → 比较原文 → 主动单选 → 确认 / 暂缓'],
    labels: [
      [158, 783, 345, 61, ['1 先读原因、影响与边界', '只选依据，不改原件、不授权外发'], 'M158 814 H51 V320 H65'],
      [1093, 209, 470, 61, ['2 待核对判断', '是候选结论，不是已验证事实'], 'M1093 236 H984 V227 H962'],
      [1070, 483, 492, 72, ['3 比较两处原文与上下文', '看清第 9 行与第 14 行为何重复'], 'M1070 517 H993 V508 H976'],
      [830, 370, 538, 47, ['4 主动单选：未选中时，确认按钮禁用'], 'M856 417 V425 H617 V416'],
      [1121, 574, 469, 38, ['5 查看原文：只是预览，不会自动选中'], 'M1450 574 H1621 V405 H1595'],
      [829, 815, 670, 44, ['6 确认 / 暂缓：记录选择；终态任务需另建 Run 续办'], 'M1499 837 H1618 V864 H1540 V882']
    ]
  }
];
const checks = [];
async function measure(line, size, bold, limit) {
  const code = `<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="100"><text x="4" y="55" fill="#111111" font-family="Microsoft YaHei" font-size="${size}" font-weight="${bold ? 700 : 400}">${esc(line)}</text></svg>`;
  const { info } = await sharp(Buffer.from(code)).trim().png().toBuffer({ resolveWithObject: true });
  if (info.width > limit) throw new Error(`Text overflow ${info.width}/${limit}: ${line}`);
  checks.push({ line, width: info.width, limit });
}
for (const page of pages) {
  const source = await fs.readFile(path.join(root, 'sources', `${page.id}-original.png`));
  const meta = await sharp(source).metadata();
  const width = meta.width, height = meta.height;
  let body = '';
  const [fx, fy, fw, flow] = page.flow;
  await measure(flow, 17, true, fw - 32);
  body += `<rect x="${fx}" y="${fy}" width="${fw}" height="65" rx="4" fill="#FFF8F0" fill-opacity="0.97" stroke="${color}" stroke-width="1.5"/>`;
  body += `<text x="${fx+16}" y="${fy+27}" font-size="17" font-weight="700" fill="${color}">${esc(flow)}</text>`;
  body += `<text x="${fx+16}" y="${fy+49}" font-size="12.5" fill="#735F57">操作流程 · 红色为后加说明 · 原系统受控测试截图</text>`;
  for (const [x, y, w, h, lines, d] of page.labels) {
    if (x < 0 || y < 0 || x + w > width || y + h > height) throw new Error('Label outside original screenshot');
    body += `<path d="${d}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" marker-end="url(#arrow)"/>`;
  }
  for (const [x, y, w, h, lines] of page.labels) {
    body += `<rect x="${x}" y="${y}" width="${w}" height="${h}" rx="4" fill="#FFF8F0" fill-opacity="0.97" stroke="${color}" stroke-width="1.5"/>`;
    for (let i = 0; i < lines.length; i++) {
      const size = i === 0 ? 17 : 15;
      await measure(lines[i], size, i === 0, w - 24);
      const baseline = lines.length === 1 ? y + h / 2 + 6 : y + h / 2 - 5 + i * 23;
      body += `<text x="${x+12}" y="${baseline}" font-size="${size}" font-weight="${i === 0 ? 700 : 400}" fill="${i === 0 ? color : '#5F4942'}">${esc(lines[i])}</text>`;
    }
  }
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width*2}" height="${height*2}" viewBox="0 0 ${width} ${height}"><defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto"><path d="M0 0 L7 3.5 L0 7 Z" fill="${color}"/></marker></defs><g font-family="Microsoft YaHei, Arial, sans-serif">${body}</g></svg>`;
  const base = await sharp(source).resize(width*2, height*2, { kernel: 'lanczos3' }).png().toBuffer();
  const overlay = await sharp(Buffer.from(svg)).png().toBuffer();
  const result = await sharp(base).composite([{ input: overlay }]).png().toBuffer();
  const file = `${page.id}-${page.name}-图内标注.png`;
  await fs.writeFile(path.join(out, file), result);
  await fs.writeFile(path.join(root, '.build', `${page.id}-in-image.svg`), svg);
  const baseRaw = await sharp(base).ensureAlpha().raw().toBuffer();
  const finalRaw = await sharp(result).ensureAlpha().raw().toBuffer();
  const mask = await sharp(overlay).ensureAlpha().raw().toBuffer();
  let changed = 0, unaffected = 0;
  for (let p = 0; p < mask.length; p += 4) {
    if (mask[p+3] !== 0) continue;
    unaffected++;
    if (baseRaw[p] !== finalRaw[p] || baseRaw[p+1] !== finalRaw[p+1] || baseRaw[p+2] !== finalRaw[p+2]) changed++;
  }
  if (changed) throw new Error(`Unexpected screenshot change: ${changed}`);
  checks.push({ file, width: width*2, height: height*2, unaffectedPixels: unaffected, unexpectedChangedPixels: changed });
  console.log(`${file}: ${width*2}x${height*2}, ${unaffected} unaffected pixels verified`);
}
await fs.writeFile(path.join(root, '.build', 'in-image-verification.json'), JSON.stringify(checks, null, 2));
