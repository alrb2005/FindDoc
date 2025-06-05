# -----------------------------------------------------------
# 依 tags_sorted (最多 3) + 使用者地區字串
# 1. 本地 CSV → ≤30 筆
# 2. GPT-4o 精選 ≤5 家
# 3. 只對「最後回傳」缺 lat/lng 的診所 geocode
# 4. 若仍不足 3 家 → Google TextSearch
# -----------------------------------------------------------
from __future__ import annotations
import asyncio, json, re, pandas as pd
from typing import Dict, List
from helpers import gmaps_client as gc
from helpers import tag_mapping, address_utils, nhi_index, clinic_registry
from helpers.llm_provider import chat_completion

# －－一次把 CSV 載入記憶體－－
_CSV_DF = pd.read_csv("data/clinics_standard.csv")

# ------------------ GPT × CSV 智慧挑診所 --------------------
async def smart_pick_clinics(tag: str, loc_str: str) -> list[dict]:
    kw = address_utils.extract_keywords(loc_str)
    patt = "|".join(map(re.escape, kw))
    df = (
        _CSV_DF
        .query("specialty == @tag")
        .query("address.str.contains(@patt)", engine="python")
        .head(30)
    )
    cand = df.to_dict("records")
    if not cand:
        return []

    sys_prompt = (
        "你是一位醫療推薦助理。以下是一組診所(JSON array)。\n"
        "請選出最多 5 家最符合症狀與地點的診所，"
        "並輸出 JSON array，每筆包含 name, address, need_geo。\n"
        "不得加入多餘欄位或解釋。範例："
        '[{"name":"AAA診所","address":"台北市…","need_geo":true}]'
    )

    gpt_json = chat_completion(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": json.dumps(cand, ensure_ascii=False)},
        ],
        json_mode=True
    )
    try:
        picks = json.loads(gpt_json)
    except Exception:
        return []

    if not (isinstance(picks, list) and all(isinstance(x, dict) for x in picks)):
        return []
    return picks[:5]  # 保險上限

# ------------------ Google TextSearch Fallback --------------
async def _search_one_tag(tag: str, loc_str: str,
                          lat0: float, lng0: float) -> list[dict]:
    kwd = tag_mapping.to_keyword(tag)
    
    # 加上「診所」二字，鎖定醫療場所
    kwd = f"{kwd} 診所"
    for radius in (2000, 4000, 8000):
        results = await gc.text_search_async(f"{kwd} near {loc_str}",
                                             radius, limit=5)
        if results:
            break
    clinics = []
    for r in results[:5]:
        clinics.append({
            "place_id": r["place_id"],
            "name": r["name"],
            "address": r.get("formatted_address", ""),
            "lat": r["geometry"]["location"]["lat"],
            "lng": r["geometry"]["location"]["lng"],
            "map_url": gc.link_from_place_id(r["place_id"]),
            "rating": r.get("rating"),
            "specialties": gc.map_types(r.get("types", [])),
        })
    return clinics

# ------------------ 跑一次 geocode 補缺 ----------------------
async def _enrich_final(clis: list[dict]) -> list[dict]:
    for c in clis:
        if c.get("lat") and c.get("lng"):
            continue
        geo = await gc.geocode_async(c["address"])
        if geo:
            loc = geo[0]["geometry"]["location"]
            c["lat"], c["lng"] = loc["lat"], loc["lng"]
            c["map_url"] = gc.link_from_place_id(geo[0]["place_id"])
    return clis

# ------------------ 對外主函式 ------------------------------
async def search_all_tags(tags_sorted: List[Dict], loc_str: str,
                          user_lat: float | None = None,
                          user_lng: float | None = None) -> Dict[str, List[Dict]]:

    if user_lat is None or user_lng is None:
        geo = await gc.geocode_async(loc_str)
        if geo:
            loc = geo[0]["geometry"]["location"]
            user_lat, user_lng = loc["lat"], loc["lng"]
        else:
            user_lat = user_lng = 0.0

    tag2clinics: Dict[str, List] = {}
    for tag in [d["tag"] for d in tags_sorted[:3]]:

        # 1) GPT 精選
        clis = await smart_pick_clinics(tag, loc_str)

        # 2) 若不足 3 家，用本地距離篩選補齊
        if len(clis) < 3:
            extra = clinic_registry.find_by_tag(
                tag, user_lat, user_lng,
                radius_km=8, loc_str=loc_str, with_geo=False
            )
            exist_names = {c.get("clinic_name") or c.get("name") for c in clis}
            clis += [e for e in extra if e["clinic_name"] not in exist_names]

        # 3) 仍不足 2 家 → Google TextSearch
        if len(clis) < 2:
            ts = await _search_one_tag(tag, loc_str, user_lat, user_lng)
            exist_names = {c.get("clinic_name") or c.get("name") for c in clis}
            clis += [t for t in ts if t["name"] not in exist_names]

        # 4) 最後只對要回傳的 ≤5 家補經緯度
        clis = await _enrich_final(clis[:5])
        tag2clinics[tag] = clis

    return tag2clinics
