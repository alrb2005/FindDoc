import json, pathlib,yaml
from helpers.llm_provider import chat_completion

# 讀 en2zh.yaml（或改成 helpers/tag_map.yaml，看你要用哪一份）
_ALLOWED_TAGS = list(
    yaml.safe_load(pathlib.Path("data/en2zh.yaml").read_text(encoding="utf-8")).keys()
)

_PROMPT_TPL = pathlib.Path("prompts/triage_prompt.txt").read_text(encoding="utf-8")

def triage(symptom_txt: str, history_tags):
    prompt = (
        _PROMPT_TPL
        .replace("{SYMPTOM_TXT}", symptom_txt)
        .replace("{HISTORY_TAGS}", ", ".join(history_tags))
        + "\n\n⚠️【只能從下列 TAG 中挑選（最多 3 個）】\n"
        + ", ".join(_ALLOWED_TAGS)
    )

    raw = chat_completion(
        messages=[{"role":"user","content":prompt}],
        model="gpt-4o",
        json_mode=True
    )
    data = json.loads(raw)
    return data["TAGS_CURRENT"]
