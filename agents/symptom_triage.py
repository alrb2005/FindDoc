import json, pathlib,yaml, logging
from helpers.llm_provider import chat_completion

logging.basicConfig(level=logging.INFO) # 設定 logging 等級為 INFO # 如果不想看到tag可以移除

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
        .replace("{ALLOWED_TAGS}", ", ".join(_ALLOWED_TAGS))
    )

    raw = chat_completion(
        messages=[{"role":"user","content":prompt}],
        model="gpt-4o",
        json_mode=True
    )
    data = json.loads(raw)

    # 把 LLM 回來的 tag print 出來 # 如果不想看到tag可以移除
    logging.info("[triage] GPT TAGS_CURRENT = %s", data.get("TAGS_CURRENT"))

    return data["TAGS_CURRENT"]
