LEGEND = '''
<div style="display:grid;grid-template-columns:1.1fr 1fr 1fr;gap:14px;margin-top:18px">
 <div class="card" style="padding:12px 16px"><div class="big">委派的三种收益</div><div class="note" style="margin-top:4px"><span class="hl">并行有深度</span>：几项工作各自要读不同资料<br><span class="hl">上下文隔离</span>：混在一起会互相干扰<br><span class="hl">独立复核</span>：需要另一个视角检查</div></div>
 <div class="card" style="padding:12px 16px"><div class="big">工作流树三种颜色</div><div class="note" style="margin-top:4px"><span style="color:#1d7a63;font-weight:700">绿</span>：已完成，可继续推进<br><span style="color:#8B6200;font-weight:700">黄</span>：等人处理，其余分支不等待<br><span style="color:#A42E25;font-weight:700">红</span>：做不了或被拒绝，转人工</div></div>
 <div class="card" style="padding:12px 16px"><div class="big">实测（真实模型）</div><div class="note" style="margin-top:4px">纪要拆 3 项待办：用户 4 步，34 秒全部完成<br>6 项工作两波执行（5 + 1 个子 Agent）：约 56 秒<br>3 个主题自主分工（1 波 3 个子 Agent）：约 36 秒</div></div>
</div>'''

SPEC = {
    "no": "图 9", "title": "Demo 2 用户流程：从会议纪要到并行交付", "sub": "工作项不等于 Agent：默认主 Agent 自办，有收益才分波委派",
    "cols": 8, "rowh": 132, "height": 790, "mt": 8,
    "lanes": [("用户", "确认 · 判断", "#E4702B"), ("主 Agent", "拆分 · 规划 · 汇总", "#124A8C"), ("子 Agent", "只读 · 分波", "#3B82C4"), ("服务端规则", "准入 · 合入", "#62738A")],
    "nodes": [
        {"id": "u1", "lane": 0, "col": 0, "text": "粘贴会议纪要", "sub": "或载入示例", "cls": "hu", "num": "1–2"},
        {"id": "a1", "lane": 1, "col": 1, "text": "拆出待办", "sub": "≤ 8 条 · 附纪要原句", "lv": "L0"},
        {"id": "u2", "lane": 0, "col": 2, "text": "逐项核对待办", "sub": "可改写 · 点开始", "cls": "hu", "num": "3–4"},
        {"id": "a2", "lane": 1, "col": 3, "text": "补资料 · 拆工作项", "sub": "找出每项要读的文件"},
        {"id": "s1", "lane": 3, "col": 4, "text": "委派判定", "sub": "独立分支 · 人工门 · 预算", "cls": "srv"},
        {"id": "a3", "lane": 1, "col": 5, "text": "主 Agent 自办", "sub": "收益不成立", "cls": "ok"},
        {"id": "w1", "lane": 2, "col": 5, "text": "第 1 波", "sub": "独立工作项并行", "lv": "L2"},
        {"id": "w2", "lane": 2, "col": 6, "text": "第 2 波", "sub": "使用前一波结果", "lv": "L2"},
        {"id": "s2", "lane": 3, "col": 7, "text": "采用门", "sub": "来源 · 依赖 · 对账", "cls": "srv"},
        {"id": "u3", "lane": 0, "col": 6, "text": "人工门", "sub": "黄色节点，其余不等", "cls": "wait", "lv": "L3"},
        {"id": "a4", "lane": 1, "col": 7, "text": "汇总交付", "sub": "逐项注明出处", "cls": "ok", "lv": "L2"},
        {"id": "u4", "lane": 0, "col": 7, "text": "查看 · 追加", "sub": "同一任务继续", "cls": "hu"},
    ],
    "edges": [
        {"from": "u1", "to": "a1"},
        {"from": "a1", "to": "u2"},
        {"from": "u2", "to": "a2"},
        {"from": "a2", "to": "s1"},
        {"from": "s1", "to": "a3", "c": "ok", "label": "收益不成立", "mx": 986, "lx": 900, "ly": 205},
        {"from": "s1", "to": "w1", "c": "blue", "label": "有收益", "mx": 996, "lx": 920, "ly": 296},
        {"from": "w1", "to": "w2", "c": "blue"},
        {"from": "w2", "to": "s2", "c": "gray", "mx": 1300},
        {"from": "s2", "to": "a4", "c": "ok", "label": "合入"},
        {"from": "a3", "to": "a4", "c": "ok"},
        {"from": "w2", "to": "u3", "c": "wait", "label": "需要判断", "lx": 1110, "ly": 150},
        {"from": "u3", "to": "a4", "c": "hu", "mx": 1346, "label": "决定后继续"},
        {"from": "a4", "to": "u4", "c": "blue"},
    ],
    "extra": LEGEND,
}
