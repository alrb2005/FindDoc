# ----------------------------------------------------------
# 整合理急性 tag + 診所清單 → GPT Markdown 推薦
# ----------------------------------------------------------
from __future__ import annotations
import json, pathlib
from typing import List, Dict
from helpers.llm_provider import chat_completion

# ── Prompt 模板 ──
_PROMPT_TMPL = pathlib.Path(__file__).with_name("evaluator_prompt.txt").read_text(encoding="utf-8")

def gpt_evaluate(tags_current: List[Dict],
                 tags_history: List[Dict],
                 clinics_by_tag: Dict[str, List[Dict]]) -> str:
    """
    tags_current  : GPT triage or TAGS_SORTED (急性問題)
    tags_history  : 與急性問題相關病史 (可空 list)
    clinics_by_tag: Recommender 回傳 JSON
    回傳 Markdown 字串
    """
    prompt = _PROMPT_TMPL.format(
        TAGS_CUR=json.dumps(tags_current, ensure_ascii=False, indent=2),
        TAGS_HIST=json.dumps(tags_history, ensure_ascii=False, indent=2),
        CLINICS=json.dumps(clinics_by_tag, ensure_ascii=False, indent=2)
    )
    md = chat_completion(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o",  # 使用最新的 gpt-4o 模型
    )
    return md.strip()
