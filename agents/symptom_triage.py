import json, pathlib
from helpers.llm_provider import chat_completion

_PROMPT_TPL = pathlib.Path("prompts/triage_prompt.txt").read_text(encoding="utf-8")

def triage(symptom_txt: str, history_tags):
    prompt = (_PROMPT_TPL
          .replace("{SYMPTOM_TXT}", symptom_txt)
          .replace("{HISTORY_TAGS}", ", ".join(history_tags)))

    raw = chat_completion(
        messages=[{"role":"user","content":prompt}],
        model="gpt-4o",
        json_mode=True
    )
    data = json.loads(raw)
    return data["TAGS_CURRENT"]
