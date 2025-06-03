"""
Summarizer Agent
讀入 FHIR 單筆 JSON → 回傳 {TLDR, DETAIL, TAGS_SORTED}
"""
import json, time, pathlib
from helpers.llm_provider import chat_completion

# 讀 Prompt
_PROMPT_TMPL = pathlib.Path("prompts/base_prompt.txt").read_text(encoding="utf-8")
_SYSTEM_MSG  = {"role": "system", "content": "你是一位臨床醫師。"}

def summarize(fhir_json: dict, retries: int = 2) -> dict:
    """呼叫 GPT，返回 dict；若失敗回 {"TLDR":"", "DETAIL":"", "TAGS_SORTED":[]}"""
    user_prompt = _PROMPT_TMPL.replace("{{FHIR}}",
                                       json.dumps(fhir_json, ensure_ascii=False))
    for _ in range(retries + 1):
        raw = chat_completion(
            messages=[_SYSTEM_MSG, {"role": "user", "content": user_prompt}],
            model="gpt-4o",          # TODO: LOCAL_LLM — 替換模型名稱
            json_mode=True                # 要求模型輸出 JSON
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            time.sleep(1)
    # 仍失敗
    return {"TLDR": "", "DETAIL": "", "TAGS_SORTED": []}
