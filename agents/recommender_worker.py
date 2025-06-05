# -----------------------------------------------------------
# 依 tags_sorted (最多 3) + 使用者地區字串
# → Google TextSearch (動態半徑 2→4→8 km)
# → 補 map_url / specialties / lat/lng
# -----------------------------------------------------------

from __future__ import annotations
import asyncio, math
from typing import Dict, List
from helpers import gmaps_client as gc
from helpers import tag_mapping, address_utils, nhi_index
# ↓ 新增：本地診所表
from helpers import clinic_registry

# 工具：計算距離（Haversine）
def _haversine_km(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

async def _search_one_tag(tag: str, loc_str: str, lat0: float, lng0: float) -> List[Dict]:
    """對單一 tag 動態擴半徑搜尋並回 clinic dict list"""
    kwd   = tag_mapping.to_keyword(tag)
    radius = 2000
    clinics: List[Dict] = []

    while len(clinics) < 2 and radius <= 8000:
        results = await gc.text_search_async(f"{kwd} near {loc_str}", radius, limit=5)
        for r in results:
            pid = r["place_id"]
            addr = r.get("formatted_address", "")
            # 避免重複 place_id
            if any(c["place_id"] == pid for c in clinics):
                continue

            lat = r["geometry"]["location"]["lat"]
            lng = r["geometry"]["location"]["lng"]
            dist_km = _haversine_km(lat0, lng0, lat, lng)

            clinic = {
                "place_id": pid,
                "name": r["name"],
                "formatted_address": addr,
                "lat": lat,
                "lng": lng,
                "dist_m": round(dist_km * 1000),
                "rating": r.get("rating"),
                "map_url": gc.link_from_place_id(pid),
                # 先映射 Google types
                "specialties": gc.map_types(r.get("types", [])),
            }

            # 用 NHI 名冊補專精
            addr_norm = address_utils.normalize(addr)
            off_specs = nhi_index.get_specialties(addr_norm)
            if off_specs:
                clinic["specialties"] = list(set(clinic["specialties"]) | set(off_specs))

            clinics.append(clinic)

        radius *= 2  # 擴半徑

    return clinics[:5]  # 最多 5 間

async def search_all_tags(tags_sorted: List[Dict], loc_str: str,
                          user_lat: float | None = None,
                          user_lng: float | None = None) -> Dict[str, List[Dict]]:
    """
    tags_sorted 來自 GPT；loc_str 為使用者輸入（樹林區…）
    若有 user_lat/lng，會用來計算距離；否則先抓第一家診所座標當基準。
    """
    tag_list = [d["tag"] for d in tags_sorted[:3]]
    if user_lat is None or user_lng is None:
        user_lat = user_lng = 0.0  # 占位，第一次搜尋後更新

    tag2clinics: Dict[str, List] = {}

    # 先取得 geocode 作為距離計算中心
    if user_lat is None or user_lng is None:
        geo = await gc.geocode_async(loc_str)
        user_lat = geo["lat"]
        user_lng = geo["lng"]

    for i, tag in enumerate(tag_list):

        # ---------- ❶ 嘗試用本地 clinics.csv 直接抓 ----------
        local_hits = clinic_registry.find_by_tag(tag, user_lat, user_lng, radius_km=8)
        if local_hits:
            # ------------ enrich：補 place_id / rating / map_url ------------
            def _enrich(c: dict) -> dict:
                # 已有 map_url 就略過
                if c.get("map_url"):
                    return c

                # 保底：經緯度連結
                c["map_url"] = f"https://www.google.com/maps/search/?api=1&query={c['lat']},{c['lng']}"

                # 用「名稱 + 地址」找 Google Place
                fp = gc.find_place(f"{c['clinic_name']} {c['address']}")
                if fp:
                    pid = fp["place_id"]
                    c.update({
                        "place_id": pid,
                        "rating": fp.get("rating"),
                        "map_url": gc.link_from_place_id(pid)
                    })
                time.sleep(0.25)   # 避免 QPS 過高（可調或移除）
                return c

            local_hits = [_enrich(c) for c in local_hits]
            tag2clinics[tag] = local_hits
            continue
        # -----------------------------------------------------

        # 第一次若沒經緯度，先查第一家診所抓 lat/lng 當中心
        if i == 0 and (user_lat == user_lng == 0.0):
            tmp = await gc.text_search_async(f"{tag_mapping.to_keyword(tag)} near {loc_str}",
                                             radius=2000, limit=1)
            if tmp:
                user_lat = tmp[0]["geometry"]["location"]["lat"]
                user_lng = tmp[0]["geometry"]["location"]["lng"]

        # fallback：Google TextSearch
        clinics = await _search_one_tag(tag, loc_str, user_lat, user_lng)
        tag2clinics[tag] = clinics

    return tag2clinics
