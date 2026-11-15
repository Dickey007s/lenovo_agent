"""Interaction prototype boards: screenshot + numbered callouts + notes (HTML, Figma-importable)."""
import json, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent
B = json.loads((ROOT / "boards/boards.json").read_text())
# manual box for the highlighted rows in b3_review (auto locator not found)
B["b3_review"]["marks"][5]["box"] = {"x": 727, "y": 930, "w": 660, "h": 46}

BOARDS = [
 ("b1_entry", "图 4", "统一入口：一个输入框承接三类协作", "Demo 1 · 新任务", [
   ("工作区切换", "Demo 1 / 2 / 3 共用一套工作台，切换不丢任务"),
   ("演示模式", "开启后离线规则代替模型，零调用即可完整演示"),
   ("共享资料库", "97 份企业文件，原件只读，可按类型检索"),
   ("任务输入", "用自然语言描述要办的事"),
   ("切换多任务", "一键转到 Demo 2 的多待办"),
   ("会议纪要入口", "粘贴纪要：一件事填入本页，多件事转多待办"),
   ("人机分工示例", "7 个预设任务，覆盖依据充分、缺事实、规则冲突"),
   ("启动", "进入 Agent Control Loop"),
 ]),
 ("b2_stop", "图 5", "Demo 1 任务详情：流程走到哪、此刻谁处理", "真实模型 · 第 1 轮 37 秒停下", [
   ("任务标题与状态", "同一任务的初始处理与后续追加都在这里"),
   ("任务概况", "已选资料、工作项进度、保留成果版本"),
   ("随时补充要求", "运行中也能改方向，不必重开任务"),
   ("任务流程", "工作流树，每个节点标出 L 等级"),
   ("黄色节点", "规则冲突，停下等人；其余分支继续"),
   ("现在要你做的事", "只列需要人处理的事项与原因"),
   ("系统已处理", "已有依据的结论直接给出"),
   ("成果栏", "分析草稿按版本保留，可随时查看"),
 ]),
 ("b3_review", "图 6", "Demo 1 问题审查页：先看事实，再看影响，最后决定", "证据由服务端逐字定位", [
   ("Agent 发现", "发生在第几轮、涉及几份资料、处理进度"),
   ("问题处置单", "系统发现 · 影响 · 你要做什么 · 会保留 · 不会做"),
   ("你的任务", "选一个处理口径，Agent 不替你决定"),
   ("证据定位", "每条证据标出文件与行号，可逐条切换"),
   ("正在核对", "当前核对的原文片段与位置说明"),
   ("原文高亮", "在真实文件预览中高亮对应行"),
 ]),
 ("b3_decide", "图 7", "Demo 1 决断区：先形成自己的判断，再对照建议", "推荐项默认隐藏，避免先入为主", [
   ("待决问题", "冲突是什么、为什么必须由人决定"),
   ("处理口径", "2–3 个选项，写明确认后 Agent 做什么、影响几个分支"),
   ("对照 Agent 建议", "先选再看推荐，系统不会替你改选"),
   ("补充反馈", "给下一轮 Agent 的额外要求"),
   ("接受并交给 Agent", "决定写入回执，启动新的只读 Control Loop"),
   ("其他出口", "暂缓、取消待决、否决这条发现"),
 ]),
 ("b4_todos", "图 10", "Demo 2 纪要拆待办：拆完先给人看", "模型拆分 · 每条附纪要原句", [
   ("拆分结果", "拆出几项、用的方法；确认后才开始"),
   ("待办卡", "每项可直接改写，指令即交给 Agent 的要求"),
   ("纪要原句", "展开可看到这条待办来自纪要哪一句"),
   ("待办示例", "4 组预设：日常、人事、自主分工、分波并行"),
   ("开始全部待办", "一次授权，各项并行推进"),
 ]),
 ("b5_tree", "图 11", "Demo 2 工作流树：一波波并行，状态一眼可见", "真实模型 · 6 项工作 · 5 + 1 个子 Agent", [
   ("第 1 波", "5 项互不依赖的工作同时开始"),
   ("第 2 波", "汇总项等前一波通过采用门后才开始"),
   ("Agent 数", "1 个主 Agent + 6 个子 Agent"),
   ("子 Agent 节点", "名称、编号、状态；悬停看摘要，点开看 8 个维度"),
   ("汇总节点", "依赖边指明它用到了哪些前序结果"),
   ("任务状态", "处理中 / 待你判断 / 已完成"),
   ("运行中补充", "新要求排队，在下一步生效"),
 ]),
 ("b6_entry", "图 14", "Demo 3 事项入口：五个等级各一个真实案例", "固定规则 · 不调用模型", [
   ("L1 案例", "整理新员工入职名单备忘，静默处理 · AL4"),
   ("L5 案例", "向候选人承诺保底薪资，受限 · AL2"),
   ("为什么是这一档", "按五因子写出等级与自主程度的由来"),
   ("更多边界案例", "12 个：同名联系人、内容变化、材料冲突、暂缓等"),
   ("启动", "约 3 秒给出判定与对应界面"),
 ]),
 ("b6_lens", "图 15", "Demo 3 Risk Lens：判定过程摊开给人看", "L4 · 向外部供应商发送配置需求", [
   ("五个判定因子", "每个因子的取值、依据与等级下限"),
   ("决定等级的因子", "高亮行即最终等级的来源"),
   ("自主程度公式", "min（等级上限，动作形态）"),
   ("此刻处理", "按介入顺序只提一件事：执行授权 · 强确认"),
   ("逐项核对", "收件对象、正文、提交范围三项都要勾"),
   ("确认按钮", "三项未勾完保持灰色，按钮写明具体动作"),
 ]),
]

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{width:1600px;font-family:"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;color:#404040;background:#fff;padding:30px 40px}
.ttl{display:flex;align-items:center;gap:14px;margin-bottom:18px}
.ttl .no{background:#124A8C;color:#fff;font-weight:700;font-size:18px;padding:4px 12px;border-radius:6px}
.ttl h1{font-size:28px;color:#12396A}.ttl .sub{font-size:17px;color:#62738A}
.wrap{display:grid;grid-template-columns:1080px 1fr;gap:22px;align-items:start}
.shot{position:relative;border:1.5px solid #CAD8E9;border-radius:12px;overflow:hidden;box-shadow:0 6px 18px rgba(18,57,106,.08)}
.shot img{display:block;width:1080px}
.hl{position:absolute;border:2.5px solid #E4702B;border-radius:6px;background:rgba(228,112,43,.06)}
.pin{position:absolute;width:30px;height:30px;border-radius:50%;background:#E4702B;color:#fff;font-weight:700;font-size:16px;display:flex;align-items:center;justify-content:center;box-shadow:0 0 0 3px #fff}
.notes{display:flex;flex-direction:column;gap:9px}
.tagline{font-size:14px;color:#124A8C;font-weight:700;background:#EAF2FB;border-radius:8px;padding:8px 12px}
.n{display:grid;grid-template-columns:30px 1fr;gap:10px;align-items:start;background:#fff;border:1.5px solid #CAD8E9;border-radius:10px;padding:9px 11px}
.n i{width:28px;height:28px;border-radius:50%;background:#E4702B;color:#fff;font-style:normal;font-weight:700;display:flex;align-items:center;justify-content:center;font-size:15px}
.n b{display:block;font-size:16px;color:#12396A}.n span{display:block;font-size:13.5px;color:#62738A;line-height:1.45;margin-top:2px}
"""


def board_html(bid, no, title, tag, notes):
    meta = B[bid]
    vw = meta["vp"]["width"]
    k = 1080 / vw
    pins = []
    for m, (t, d) in zip(meta["marks"], notes):
        b = m["box"]
        if not b:
            continue
        x, y, w, h = b["x"] * k, b["y"] * k, b["w"] * k, b["h"] * k
        w, h = min(w, 1080 - x - 2), min(h, 740 - y - 2)
        pins.append(f'<div class="hl" style="left:{x - 3:.0f}px;top:{y - 3:.0f}px;width:{w + 6:.0f}px;height:{h + 6:.0f}px"></div>')
        px, py = max(2, x - 16), max(2, y - 16)
        pins.append(f'<div class="pin" style="left:{px:.0f}px;top:{py:.0f}px">{m["n"]}</div>')
    items = "".join(f'<div class="n"><i>{i + 1}</i><div><b>{html.escape(t)}</b><span>{html.escape(d)}</span></div></div>' for i, (t, d) in enumerate(notes))
    return f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>{no} {title}</title><style>{CSS}</style></head><body>
<div class="ttl"><span class="no">{no}</span><h1>{html.escape(title)}</h1></div>
<div class="wrap"><div class="shot"><img src="boards/{bid}.png">{"".join(pins)}</div>
<div class="notes"><div class="tagline">{html.escape(tag)}</div>{items}</div></div></body></html>'''


MOBILE = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>图 17 移动端</title><style>{CSS}
.phones{{display:grid;grid-template-columns:repeat(3,330px) 1fr;gap:26px;align-items:start}}
.ph{{border:10px solid #12396A;border-radius:34px;overflow:hidden;box-shadow:0 8px 22px rgba(18,57,106,.18)}}
.ph img{{display:block;width:310px}}
.cap{{margin-top:10px;font-size:15px;font-weight:700;color:#12396A;text-align:center}}
.cap small{{display:block;font-weight:400;color:#62738A;font-size:13px;margin-top:2px}}
</style></head><body>
<div class="ttl"><span class="no">图 17</span><h1>Demo 3 移动端：手机上保留做决定所需的信息</h1><span class="sub">390 × 844 · 同一套判定与核对</span></div>
<div class="phones">
 <div><div class="ph"><img src="../screenshots/d3m-L4-a.png"></div><div class="cap">① 状态与完整内容<small>收件人地址、正文不折叠</small></div></div>
 <div><div class="ph"><img src="../screenshots/d3m-L4-b.png"></div><div class="cap">② 判定过程<small>五因子表格完整保留</small></div></div>
 <div><div class="ph"><img src="../screenshots/d3m-L4-c.png"></div><div class="cap">③ 逐项核对后确认<small>三项未勾完按钮保持灰色</small></div></div>
 <div class="notes">
  <div class="tagline">对应规则 R13 · 案例 C12</div>
  <div class="n"><i>1</i><div><b>信息不缩水</b><span>地址、金额、附件版本在手机上完整可见，不为版面省略</span></div></div>
  <div class="n"><i>2</i><div><b>判定一致</b><span>桌面与手机调用同一判定结果，等级不因设备降低</span></div></div>
  <div class="n"><i>3</i><div><b>离开不等于同意</b><span>关闭页面后事项保持待确认，可在“最近事项与暂缓记录”中继续；内容变了就重新核对</span></div></div>
  <div class="n"><i>4</i><div><b>大按钮、明确动作</b><span>“确认登记测试发件”“稍后处理”并列，修改与取消同样好找</span></div></div>
  <div class="n"><i>5</i><div><b>不探测环境</b><span>系统不检测用户所处场合，不为此开启录音或摄像</span></div></div>
 </div>
</div></body></html>'''

C06 = f'''<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>图 16 澄清后重判</title><style>{CSS}
.pair{{display:grid;grid-template-columns:1fr 80px 1fr;gap:10px;align-items:center}}
.pair .c{{border:1.5px solid #CAD8E9;border-radius:12px;padding:10px;background:#fff}}
.pair .c img{{display:block;width:100%}}
.pair h3{{font-size:18px;color:#12396A;margin-bottom:8px;display:flex;gap:8px;align-items:center}}
.chip{{display:inline-block;color:#fff;font-weight:700;border-radius:5px;padding:1px 9px;font-size:14px}}
.arr{{font-size:15px;color:#124A8C;font-weight:700;text-align:center}}
</style></head><body>
<div class="ttl"><span class="no">图 16</span><h1>Demo 3 澄清后重判：“交给王工”从 L4 降到 L3</h1><span class="sub">案例 C06 · 不明按高 → 变化即重判</span></div>
<div class="pair">
 <div class="c"><h3><span class="chip" style="background:#E4702B">L4</span>澄清前：三位“王工”，其中一位在外部</h3><img src="../screenshots/c06-1-judgement.png"></div>
 <div class="arr">选定<br>研发组王工<br>→</div>
 <div class="c"><h3><span class="chip" style="background:#D9A21B">L3</span>澄清后：内部 1 人，按事实重判</h3><img src="../screenshots/c06-2-judgement.png"></div>
</div>
<div class="notes" style="margin-top:16px;display:grid;grid-template-columns:repeat(3,1fr)">
 <div class="n"><i>1</i><div><b>不明按高</b><span>影响范围未知时按外部判定，并标出“不明按高”</span></div></div>
 <div class="n"><i>2</i><div><b>一次只问一件</b><span>先问“是哪位王工”，界面同时提示“后续还需：强确认”</span></div></div>
 <div class="n"><i>3</i><div><b>重判且旧确认失效</b><span>选定后第 2 版重新判定为 L3，只需普通确认</span></div></div>
</div></body></html>'''

if __name__ == "__main__":
    out = []
    for spec in BOARDS:
        p = ROOT / f"{spec[0]}.html"
        p.write_text(board_html(*spec), encoding="utf-8"); out.append(p.name)
    (ROOT / "b7_mobile.html").write_text(MOBILE, encoding="utf-8"); out.append("b7_mobile.html")
    (ROOT / "b8_c06.html").write_text(C06, encoding="utf-8"); out.append("b8_c06.html")
    links = "".join(f'<li><a href="{n}">{n}</a></li>' for n in out)
    (ROOT / "index.html").write_text(f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>交互原型图</title></head><body style="font-family:PingFang SC;padding:30px"><h1>交互原型图（可用 html.to.design 导入 Figma）</h1><ul>{links}</ul></body></html>', encoding="utf-8")
    print("\n".join(out))
