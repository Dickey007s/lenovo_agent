// Generate local SVG markup from the repository's existing Tabler library.
const fs = require("node:fs");
const path = require("node:path");
const { createRequire } = require("node:module");
const requireWeb = createRequire(path.resolve(__dirname, "../../..", "apps/web/package.json"));
const React = requireWeb("react");
const { renderToStaticMarkup } = requireWeb("react-dom/server");
const tabler = requireWeb("@tabler/icons-react");
const names = ["IconTopologyStar3", "IconPresentation", "IconDownload", "IconX", "IconFileSearch", "IconArrowsDiff", "IconLock", "IconShieldExclamation", "IconHourglass", "IconRefresh", "IconGitBranch", "IconChecklist", "IconCircleCheck", "IconCheck", "IconCircleOff", "IconMinus", "IconFileText", "IconBulb", "IconInfoCircle", "IconClock", "IconUserCheck", "IconArrowLeft", "IconArrowRight", "IconFiles", "IconFlask", "IconRotate", "IconArrowUpRight", "IconSearch"];
const icons = Object.fromEntries(names.map(name => [name, renderToStaticMarkup(React.createElement(tabler[name], { size: 20, stroke: 1.65, "aria-hidden": true }))]));
fs.writeFileSync(path.join(__dirname, "icons.js"), `// Generated from @tabler/icons-react 3.46.0, MIT License.\nwindow.COPILOT_ICONS = ${JSON.stringify(icons)};\n`, "utf8");
console.log(`Generated ${names.length} local Tabler icons.`);
