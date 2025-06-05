"""
helpers/gmaps_client.py
Google Places API 封裝 + SQLite 快取 + 中文科別映射 (YAML + GPT 查詢)
---------------------------------------------------------------------
依賴:
  • aiohttp
  • PyYAML
  • helpers.llm_provider.chat_completion  (可換本地 LLM)
環境變數:
  • GMPS_KEY (優先) 或 GMAPS_API_KEY ── Google Maps API Key
"""
from __future__ import annotations

# ────── 內建 / 第三方 ──────────────────────────────────────────
import os, json, time, sqlite3, pathlib, re, inspect, asyncio
from typing import List, Dict, Any
import aiohttp, yaml

# ────── 專案內工具 ────────────────────────────────────────────
from helpers.llm_provider import chat_completion  # GPT 兜底

# ────── 1. API KEY ───────────────────────────────────────────
_API_KEY = os.getenv("GMPS_KEY") or os.getenv("GMAPS_API_KEY")
if not _API_KEY:
    raise RuntimeError("請在環境變數 GMPS_KEY 或 GMAPS_API_KEY 設定 Google Maps API Key")

# ────── 2. SQLite 快取 ────────────────────────────────────────
CACHE_DIR = pathlib.Path("cache")
CACHE_DIR.mkdir(exist_ok=True)
_CACHE_DB = CACHE_DIR / "gmaps_cache.db"

def _get_db():
    """取得（若無則建立）SQLite 連線"""
    conn = sqlite3.connect(_CACHE_DB)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gmaps_cache (
               cache_key TEXT PRIMARY KEY,
               json      TEXT,
               timestamp REAL
        )"""
    )
    return conn

async def _fetch_or_cache_async(cache_key: str, fetch_coro_factory):
    """
    先查快取，無則呼叫協程取資料並寫回快取。
    fetch_coro_factory 必須回傳 coroutine，例如:  lambda: _http_get(url, params)
    """
    conn = _get_db()
    row = conn.execute(
        "SELECT json FROM gmaps_cache WHERE cache_key = ?", (cache_key,)
    ).fetchone()
    if row:
        return json.loads(row[0])

    coro = fetch_coro_factory()
    if not inspect.iscoroutine(coro):
        raise TypeError("fetch_coro_factory 必須回傳 coroutine")
    data = await coro

    conn.execute(
        "INSERT INTO gmaps_cache VALUES (?,?,?)",
        (cache_key, json.dumps(data, ensure_ascii=False), time.time()),
    )
    conn.commit()
    return data

# ────── 3. HTTP helper ───────────────────────────────────────
async def _http_get(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    async with aiohttp.ClientSession() as sess:
        async with sess.get(url, params=params, timeout=30) as resp:
            resp.raise_for_status()
            return await resp.json()

# ────── 4. Text Search ───────────────────────────────────────
async def text_search_async(
    query: str, radius: int = 2000, limit: int = 5
) -> List[Dict[str, Any]]:
    """非同步呼叫 Google Text Search，回傳前 limit 筆結果"""
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": query,
        "radius": radius,
        "language": "zh-TW",
        "key": _API_KEY,
    }
    cache_key = f"search::{query}::{radius}"
    data = await _fetch_or_cache_async(cache_key, lambda: _http_get(url, params))
    return data.get("results", [])[:limit]

# ────── 5. Place Details ─────────────────────────────────────
async def details_async(place_id: str) -> Dict[str, Any]:
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "language": "zh-TW",
        "key": _API_KEY,
    }
    cache_key = f"details::{place_id}"
    data = await _fetch_or_cache_async(cache_key, lambda: _http_get(url, params))
    return data.get("result", {})

# ────── 6. Geocoding（★ 新增）─────────────────────────────────
async def geocode_async(address: str) -> List[Dict[str, Any]]:
    """
    非同步呼叫 Google Geocoding API，回傳 results 陣列。
    """
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        "address": address,
        "language": "zh-TW",
        "key": _API_KEY,
    }
    cache_key = f"geocode::{address}"
    data = await _fetch_or_cache_async(cache_key, lambda: _http_get(url, params))
    return data.get("results", [])

def geocode(address: str) -> List[Dict[str, Any]]:
    """
    同步包裝：在一般 (非 async) 程式碼中直接呼叫 geocode。
    自動偵測是否已有 event loop，避免 nested loop crash。
    """
    try:
        loop = asyncio.get_running_loop()
        fut = asyncio.run_coroutine_threadsafe(geocode_async(address), loop)
        return fut.result()
    except RuntimeError:
        # 無 event loop
        return asyncio.run(geocode_async(address))

# ────── 7. 產生 Google Maps 連結 ─────────────────────────────
def link_from_place_id(pid: str) -> str:
    return f"https://www.google.com/maps/place/?q=place_id:{pid}"

# ────── 8. type ➜ 中文科別對映 ───────────────────────────────
_TYPE_YAML = pathlib.Path(__file__).with_name("type_map.yaml")
_TYPE_TO_CN: Dict[str, str]
if _TYPE_YAML.exists():
    _TYPE_TO_CN = yaml.safe_load(_TYPE_YAML.read_text(encoding="utf-8")) or {}
else:
    _TYPE_TO_CN = {}

def _gpt_cn_from_type(t: str) -> str | None:
    """
    若 YAML 無對照，使用 GPT 將 Google place type 翻成
    台灣健保常用科別中文（4~6 字）。若無對應，回 None。
    """
    prompt = (
        f"請將 Google Maps place type `{t}` 翻成台灣健保常用科別中文，"
        "若無對應請回『其他』或『unknown』。\n"
        "若是推測，請在最後加上（推測）。\n"
        "請只回中文科別，不要加解釋。"
    )
    try:
        cn = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o"
        ).strip()

        if not cn or cn.lower() in {"其他", "unknown", "none", "無"}:
            return None
        # 去括號註解與非中文字
        cn = re.sub(r"[（(].*?[)）]", "", cn)
        cn = "".join(ch for ch in cn if "\u4e00" <= ch <= "\u9fff")[:6]
        return cn or None
    except Exception:
        return None

def map_types(types: List[str]) -> List[str]:
    """
    傳入 Google 原生 types 陣列，回傳中文科別列表。
    優先 YAML 對照；沒找到就 GPT 查詢並落地 cache。
    """
    cn_list: List[str] = []
    for t in types:
        if t in _TYPE_TO_CN:
            cn_list.append(_TYPE_TO_CN[t])
            continue

        cn = _gpt_cn_from_type(t)
        if cn:
            cn_list.append(cn)
            _TYPE_TO_CN[t] = cn
            _TYPE_YAML.write_text(
                yaml.safe_dump(_TYPE_TO_CN, allow_unicode=True),
                encoding="utf-8"
            )
    return cn_list
