import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from agents.summarizer_agent import summarize  # 新增 import

load_dotenv()          # 讀取 .env（含 OPENAI_API_KEY）
client = OpenAI()      # 自動抓 API key

def load_fhir_json(fp):
    with open(fp, encoding="utf-8") as f:
        return json.load(f)

def load_prompt_template(fp):
    return Path(fp).read_text(encoding="utf-8")

def build_prompt(template, fhir_json):
    return template.replace("{{fhir}}",
            json.dumps(fhir_json, indent=2, ensure_ascii=False))

def call_gpt(prompt=None, messages=None, model="gpt-4o"):
    if messages is None:
        messages = [{"role": "user", "content": prompt}]
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content.strip()

def gpt_summary(fhir_json: dict):
    """
    回傳 (TLDR:str, DETAIL:str, tags_sorted:list[dict])
    供 CLI 或其他模組呼叫。
    """
    data = summarize(fhir_json)
    return data["TLDR"], data["DETAIL"], data["TAGS_SORTED"]