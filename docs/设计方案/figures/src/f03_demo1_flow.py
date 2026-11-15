LEGEND = '''
<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:18px">
 <div class="card" style="padding:14px 16px;border-left:7px solid #2E9E83"><div class="big" style="color:#1d7a63">依据充分 → 直接给结论</div><div class="note">规则明确、原文能逐字定位。例：吴嘉木现规则允许的通用软件清单</div></div>
 <div class="card" style="padding:14px 16px;border-left:7px solid #D9A21B"><div class="big" style="color:#8B6200">缺关键事实 → 停下补资料</div><div class="note">资料库里找不到所需凭证，不用相近材料代替。例：有余额，不等于已收款（缺到账回单）</div></div>
 <div class="card" style="padding:14px 16px;border-left:7px solid #E4702B"><div class="big" style="color:#b4531d">规则冲突 / 业务取舍 → 交人决定</div><div class="note">给出 2–3 个口径和影响，推荐默认隐藏。例：备注"不开通研发权限"与 GitHub 申请冲突</div></div>
</div>'''

SPEC = {
    "no": "图 3", "title": "Demo 1 用户流程：有依据才往下做", "sub": "用户 5 步：选任务 → 启动 → 打开问题 → 选口径 → 交给 Agent",
    "cols": 8, "rowh": 156, "height": 710,
    "mt": 40,
    "lanes": [("用户", "提出 · 判断 · 追问", "#E4702B"), ("Agent", "规划 · 分析", "#124A8C"), ("服务端规则", "定位 · 校验 · 拦截", "#62738A")],
    "nodes": [
        {"id": "u1", "lane": 0, "col": 0, "text": "输入任务", "sub": "或选一个示例", "cls": "hu", "num": "1"},
        {"id": "s1", "lane": 2, "col": 1, "text": "冻结资料范围", "sub": "整库索引 · 原件只读"},
        {"id": "a1", "lane": 1, "col": 2, "text": "理解任务 · 拆工作项", "sub": "规划模型", "lv": "L0"},
        {"id": "s2", "lane": 2, "col": 3, "text": "计划校验", "sub": "文件 · 工具 · 依赖 · 只读", "cls": "srv"},
        {"id": "a2", "lane": 1, "col": 4, "text": "读资料 · 写结论", "sub": "每条附原文引用", "lv": "L2"},
        {"id": "s3", "lane": 2, "col": 5, "text": "逐字定位 · 证据门", "sub": "行号 / 单元格 / 页码", "cls": "srv"},
        {"id": "a3", "lane": 1, "col": 6, "text": "依据充分", "sub": "其余分支继续推进", "cls": "ok"},
        {"id": "u2", "lane": 0, "col": 6, "text": "核对证据 · 选口径", "sub": "缺事实就补资料", "cls": "wait", "lv": "L3", "num": "3–5"},
        {"id": "a4", "lane": 1, "col": 7, "text": "汇总交付", "sub": "成果按版本保留", "cls": "ok", "lv": "L2"},
        {"id": "u3", "lane": 0, "col": 7, "text": "追问 / 补充要求", "sub": "长在同一棵任务树", "cls": "hu"},
        {"id": "u0", "lane": 0, "col": 1, "text": "启动", "sub": "Control Loop", "cls": "hu", "num": "2", "w": 110},
    ],
    "edges": [
        {"from": "u1", "to": "u0"},
        {"from": "u0", "to": "s1", "mx": 330},
        {"from": "s1", "to": "a1"},
        {"from": "a1", "to": "s2"},
        {"from": "s2", "to": "a2"},
        {"from": "a2", "to": "s3"},
        {"from": "s3", "to": "a3", "c": "ok", "label": "通过"},
        {"from": "s3", "to": "u2", "c": "wait", "label": "缺口 / 冲突", "mx": 1078},
        {"from": "a3", "to": "a4", "c": "ok"},
        {"from": "u2", "to": "a4", "c": "hu", "label": "决定写入回执", "mx": 1270},
        {"from": "a4", "to": "u3", "c": "blue"},
        {"from": "u3", "to": "a1", "c": "blue", "dash": True, "route": "top", "y": -20, "label": "同一任务追加分支，不新建任务"},
    ],
    "extra": LEGEND,
}
