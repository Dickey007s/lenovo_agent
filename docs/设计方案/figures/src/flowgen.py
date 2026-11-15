"""Swimlane flow figure generator (HTML + inline SVG), shares fig.css styling."""
import html, sys

LANE_W = 128
TOP = 0


def build(spec):
    W = 1512
    cols = spec["cols"]
    colw = (W - LANE_W) / cols
    rowh = spec.get("rowh", 150)
    lanes = spec["lanes"]
    H = rowh * len(lanes)
    pos = {}
    out_nodes = []
    for n in spec["nodes"]:
        lane, col = n["lane"], n["col"]
        w = n.get("w", colw - 26)
        span = n.get("span", 1)
        if span > 1:
            w = colw * span - 26
        cx = LANE_W + colw * col + colw * span / 2
        cy = rowh * lane + rowh / 2 + n.get("dy", 0)
        h = n.get("h", 74)
        pos[n["id"]] = (cx, cy, w, h)
        cls = n.get("cls", "")
        sub = f'<small>{n["sub"]}</small>' if n.get("sub") else ""
        chip = f'<span class="chip {n["lv"]}" style="position:absolute;top:-11px;left:10px;font-size:12px;padding:0 7px">{n["lv"]}</span>' if n.get("lv") else ""
        num = f'<span class="num">{n["num"]}</span>' if n.get("num") else ""
        out_nodes.append(
            f'<div class="nd {cls}" style="position:absolute;left:{cx - w / 2:.0f}px;top:{cy - h / 2:.0f}px;width:{w:.0f}px;height:{h}px;display:flex;flex-direction:column;justify-content:center">{chip}{num}{n["text"]}{sub}</div>')
    paths = []
    labels = []
    colors = {"": "#9fb4cc", "ok": "#2E9E83", "hu": "#E4702B", "wait": "#D9A21B", "bad": "#C8382E", "blue": "#124A8C", "gray": "#62738A"}
    for e in spec["edges"]:
        a, b = pos[e["from"]], pos[e["to"]]
        color = colors[e.get("c", "")]
        dash = 'stroke-dasharray="7 5"' if e.get("dash") else ""
        mk = f'url(#m{e.get("c", "") or "d"})'
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        route = e.get("route")
        if route == "loop":  # back edge under lanes
            yb = e.get("y", H - 12)
            d = f"M{ax:.0f} {ay + ah / 2:.0f} V{yb} H{bx:.0f} V{by + bh / 2 + 6:.0f}"
            lx, ly = (ax + bx) / 2, yb - 8
        elif route == "top":
            yt = e.get("y", 10)
            d = f"M{ax:.0f} {ay - ah / 2:.0f} V{yt} H{bx:.0f} V{by - bh / 2 - 6:.0f}"
            lx, ly = (ax + bx) / 2, yt - 6
        elif abs(ay - by) < 2:
            d = f"M{ax + aw / 2:.0f} {ay:.0f} H{bx - bw / 2 - 6:.0f}"
            lx, ly = (ax + aw / 2 + bx - bw / 2) / 2, ay - 9
        elif abs(ax - bx) < 2:
            if by > ay:
                d = f"M{ax:.0f} {ay + ah / 2:.0f} V{by - bh / 2 - 6:.0f}"
            else:
                d = f"M{ax:.0f} {ay - ah / 2:.0f} V{by + bh / 2 + 6:.0f}"
            lx, ly = ax + 8, (ay + by) / 2
        else:
            sx = ax + aw / 2
            ex = bx - bw / 2 - 6
            if ex <= sx:  # target left/same column: go vertical then horizontal
                sy = ay + (ah / 2 if by > ay else -ah / 2)
                d = f"M{ax:.0f} {sy:.0f} V{by:.0f} H{bx + bw / 2 + 6:.0f}"
                lx, ly = ax + 8, (ay + by) / 2
            else:
                mx = e.get("mx", (sx + ex) / 2)
                d = f"M{sx:.0f} {ay:.0f} H{mx:.0f} V{by:.0f} H{ex:.0f}"
                lx, ly = mx + 6, (ay + by) / 2
        paths.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2.4" {dash} marker-end="{mk}"/>')
        if e.get("label"):
            t = html.escape(e["label"])
            tw = 13 * len(e["label"]) + 16
            anchor = e.get("la", "middle")
            if anchor == "start":
                rx = lx
            else:
                rx = lx - tw / 2
            lx2, ly2 = e.get("lx", rx), e.get("ly", ly)
            labels.append(f'<rect x="{lx2:.0f}" y="{ly2 - 13:.0f}" width="{tw}" height="22" rx="11" fill="#fff" stroke="{color}" stroke-width="1.2"/><text x="{lx2 + tw / 2:.0f}" y="{ly2 + 3:.0f}" font-size="13" fill="{color}" text-anchor="middle" font-weight="700">{t}</text>')
    markers = "".join(
        f'<marker id="m{k or "d"}" markerWidth="10" markerHeight="10" refX="7" refY="5" orient="auto"><path d="M0 0 L10 5 L0 10 Z" fill="{v}"/></marker>'
        for k, v in colors.items())
    lane_html = []
    for i, (name, sub, color) in enumerate(lanes):
        lane_html.append(
            f'<div style="position:absolute;left:0;top:{i * rowh}px;width:{W}px;height:{rowh - 6}px;border:1.5px solid #CAD8E9;border-radius:12px;background:{"#FBFCFE" if i % 2 == 0 else "#fff"}"></div>'
            f'<div style="position:absolute;left:0;top:{i * rowh}px;width:{LANE_W - 12}px;height:{rowh - 6}px;background:{color};border-radius:12px 0 0 12px;color:#fff;font-weight:700;font-size:19px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center">{name}<small style="font-size:12.5px;font-weight:400;opacity:.85;margin-top:4px">{sub}</small></div>')
    heads = ""
    if spec.get("heads"):
        hs = []
        for i, h in enumerate(spec["heads"]):
            x = LANE_W + colw * i
            hs.append(f'<div style="position:absolute;left:{x:.0f}px;top:-30px;width:{colw:.0f}px;text-align:center;font-size:14px;font-weight:700;color:#62738A">{h}</div>')
        heads = "".join(hs)
    body_h = spec["height"]
    extra = spec.get("extra", "")
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><link rel="stylesheet" href="fig.css">
<style>body{{height:{body_h}px}} .nd{{font-size:15px;padding:6px 10px;box-shadow:0 1px 0 rgba(18,57,106,.05)}} .nd small{{font-size:12.5px}}
.num{{position:absolute;top:-10px;right:-8px;min-width:22px;padding:0 6px;height:22px;border-radius:11px;background:#12396A;color:#fff;font-size:12px;display:flex;align-items:center;justify-content:center}}
{spec.get("css", "")}</style></head><body>
<div class="ttl"><span class="no">{spec["no"]}</span><h1>{spec["title"]}</h1><span class="sub">{spec["sub"]}</span></div>
<div style="position:relative;width:{W}px;height:{H}px;margin-top:{spec.get("mt", 36 if spec.get("heads") else 0)}px">
{"".join(lane_html)}{heads}
<svg width="{W}" height="{H}" style="position:absolute;left:0;top:0;overflow:visible"><defs>{markers}</defs>{"".join(paths)}{"".join(labels)}</svg>
{"".join(out_nodes)}
</div>
{extra}
</body></html>'''


if __name__ == "__main__":
    import importlib.util, pathlib
    path = pathlib.Path(sys.argv[1])
    spec_mod = importlib.util.spec_from_file_location("s", path)
    m = importlib.util.module_from_spec(spec_mod); spec_mod.loader.exec_module(m)
    out = path.with_suffix(".html")
    out.write_text(build(m.SPEC), encoding="utf-8")
    print(out)
