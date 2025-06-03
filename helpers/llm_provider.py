"""
統一的 LLM 介面 ── 全專案只 import 這層。
# TODO: LOCAL_LLM
若未來要換本地模型，只需改本檔的 chat_completion() 內部實作即可。
"""
from typing import List, Dict
import os, re


# === OpenAI 版本 =====================================================
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# 專案根目錄 = llm_provider.py 的父層再上一層
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")   # 顯式載入

# ---------- 初始化 OpenAI Client ----------
_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not _OPENAI_API_KEY:
    raise RuntimeError(
        "❌ 找不到 OPENAI_API_KEY！請在 `.env` 或環境變數設定。"
    )

# 全域 Singleton，用於整個專案
_openai_client = OpenAI(api_key=_OPENAI_API_KEY)

def _openai_chat(messages: List[Dict], model: str,
                 use_json_mode: bool) -> str:
    # --- 新增：若要 JSON 而且 prompt 裡沒提到 json，就先補一段 ---
    if use_json_mode and not any("json" in m["content"].lower() for m in messages):
        messages = [{"role": "system", "content": "Respond ONLY in valid JSON."}] + list(messages)
    # -----------------------------------------------------------------

    kwargs = {"model": model, "messages": messages, "temperature": 0.2}
    if use_json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = _openai_client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()

# === 對外函式 ========================================================

def chat_completion(messages: List[Dict],
                    model: str = "gpt-4o",
                    json_mode: bool = False) -> str:
    """
    一般 ChatCompletion，回傳字串。
    messages: [{"role":"system/user/assistant", "content": "..."}]
    json_mode=True 時會要求模型輸出合法 JSON。
    """
    # TODO: LOCAL_LLM —— 將此分支改為呼叫本地模型
    return _openai_chat(messages, model, json_mode)
