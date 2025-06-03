import json, pathlib, datetime, re
from datetime import date
from helpers.llm_provider import chat_completion

_PROMPT = pathlib.Path("prompts/context_builder_prompt.txt").read_text(encoding="utf-8")

# ------ system prompts -------------------------------------------------
_SYS_ROLE = {
    "role": "system",
    "content": "You are a clinical summarizer."
}

# 明確要求輸出格式，防止欄位缺失 & 通過 OpenAI JSON gatekeeper
_SYS_FMT = {
    "role": "system",
    "content": (
        "When responding, output ONLY a valid JSON object **exactly** like:\n"
        '{"overall": "<string>", "history_tags": ["<str>", "..."]}\n'
        "No other keys, no markdown, no extra text."
    ),
}
# ----------------------------------------------------------------------
def _extract_patient_age(fhir_json_list) -> str:
    today = date.today()
    for raw in fhir_json_list:
        try:
            obj = json.loads(raw)
        except Exception:
            continue
        if obj.get("resourceType") == "Patient" and "birthDate" in obj:
            # birthDate 格式 YYYY-MM-DD 或 YYYY
            m = re.match(r"(\d{4})(?:-(\d{2})-(\d{2}))?", obj["birthDate"])
            if not m:
                continue
            y, mth, d = int(m[1]), int(m[2] or 1), int(m[3] or 1)
            yrs = today.year - y - ((today.month, today.day) < (mth, d))
            return str(yrs)
    return ""

def build_context(fhir_json_list):
    age = _extract_patient_age(fhir_json_list)  # ←提取病人年齡

    prompt = _PROMPT.replace(
        "{FHIR_LIST}", json.dumps(fhir_json_list, ensure_ascii=False)
    ).replace(
        "{AGE}", age                              
    )

    raw = chat_completion(
        messages=[_SYS_ROLE, _SYS_FMT, {"role": "user", "content": prompt}],
        model="gpt-4o",
        json_mode=True
    )
    prompt = _PROMPT.replace(
        "{FHIR_LIST}",
        json.dumps(fhir_json_list, ensure_ascii=False)
    )
    raw = chat_completion(
        messages=[_SYS_ROLE, _SYS_FMT, {"role": "user", "content": prompt}],
        model="gpt-4o",
        json_mode=True
    )

# ----------------- 容錯：欄位缺失時給預設值 -----------------
    data = json.loads(raw)
    overall      = data.get("overall", "")
    history_tags = data.get("history_tags", [])
    if not isinstance(history_tags, list):  # 若模型誤給字串
        history_tags = [str(history_tags)]
    return overall, history_tags