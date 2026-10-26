"""Conservative recognition of explicit no-file instructions, not general NLU."""

import re
import unicodedata
from typing import Literal


OutputPolicy = Literal["workspace_files_allowed", "analysis_only"]
OutputPreference = Literal["auto", "workspace_files_allowed", "analysis_only"]


def compile_output_policy(instruction: str, preference: OutputPreference = "auto") -> OutputPolicy:
    text = unicodedata.normalize("NFKC", instruction).lower()
    prohibitions = (
        r"(?:不要|禁止|不允许|不需要|无需|勿|不)\s*(?:生成|创建|导出|保存|写入|写出)"
        r"[^，,。；;!?！？\n]{0,16}(?:文件|报告|文档|附件|csv|docx|xlsx|pdf|zip|excel|word)",
        r"(?:只|仅)(?:在)?\s*(?:页面|界面|屏幕|网页)(?:上)?\s*(?:展示|显示|呈现)",
        r"\b(?:do not|don't|never|without)\s+(?:generat\w*|creat\w*|export\w*|sav\w*|writ\w*)"
        r"[^,.;!?\n]{0,35}\b(?:files?|reports?|documents?|attachments?|csv|docx|xlsx|pdf|zip)\b",
    )
    prohibited = any(re.search(pattern, text) for pattern in prohibitions)
    if prohibited and preference == "workspace_files_allowed":
        raise ValueError("输出选择与任务中的禁文件要求冲突，请选择仅页面分析或修改任务要求。")
    return "analysis_only" if prohibited or preference == "analysis_only" else "workspace_files_allowed"
