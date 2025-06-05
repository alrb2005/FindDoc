# helpers/clinic_registry.py 內

from __future__ import annotations
from pathlib import Path
import pandas as pd, yaml, re
from typing import List
from helpers import gmaps_client as gc
from helpers.address_utils import extract_keywords

ROOT      = Path(__file__).parent.parent
CSV_PATH  = ROOT / "data" / "clinics_standard.csv"
MAP_PATH  = ROOT / "data" / "zh2en.yaml"

# ---------- 讀 YAML (中文→英文專科) ----------
try:
    ZH2EN: dict[str, str] = yaml.safe_load(MAP_PATH.read_text("utf-8")) or {}
except FileNotFoundError:
    ZH2EN = {}

# ---------- 主要函式 ----------
def load_registry() -> pd.DataFrame:
    df = pd.read_csv(CSV_PATH)
    if "specialties" in df.columns and "specialty" not in df.columns:
        df = df.rename(columns={"specialties": "specialty"})

    if "specialty" in df.columns:
        df["specialty"] = df["specialty"].fillna("").apply(
            lambda x: ZH2EN.get(str(x).strip(), str(x).strip())
        )
    return df

def ensure_latlng(df: pd.DataFrame) -> pd.DataFrame:
    """對缺 lat/lng 的列逐筆 geocode，並把結果寫回 DataFrame（就地修改）。"""
    needs = df[df["lat"].isna() | df["lng"].isna()]
    for idx, row in needs.iterrows():
        geo = gc.geocode(row["address"])
        if geo:
            loc = geo[0]["geometry"]["location"]
            df.at[idx, "lat"] = loc["lat"]
            df.at[idx, "lng"] = loc["lng"]
    return df

def find_by_tag(tag: str,
                center_lat: float,
                center_lng: float,
                radius_km: float = 8,
                loc_str: str | None = None,
                with_geo: bool = False) -> List[dict]:
    """
    依英文科別 tag + 位置，回傳 radius 內最近 5 家診所 (list of dict)
    • loc_str 若給定：用市/區關鍵字過濾
    • with_geo=True 時才會批次 geocode 補 lat/lng
    """
    from math import radians, sin, cos, sqrt, atan2

    def _dist_km(lat1, lon1, lat2, lon2):
        R = 6371
        dlat, dlon = radians(lat2 - lat1), radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1-a))

    df = load_registry()
    df = df[df["specialty"] == tag]

    # 地區關鍵字 (市 / 區) 過濾
    if loc_str:
        kw = extract_keywords(loc_str)              # e.g. ['新北市', '樹林區']
        patt = "|".join(map(re.escape, kw))
        df = df[df["address"].str.contains(patt, na=False)]

    if df.empty:
        return []

    if with_geo:
        df = ensure_latlng(df)

    # 若 lat/lng 仍缺，先予以過濾避免 _dist_km 錯誤
    df = df.dropna(subset=["lat", "lng"])
    if df.empty:
        return []

    df["dist_m"] = df.apply(
        lambda r: round(_dist_km(center_lat, center_lng, r["lat"], r["lng"]) * 1000),
        axis=1
    )
    df = df[df["dist_m"] <= radius_km * 1000].sort_values("dist_m")
    return df.head(5).to_dict("records")
