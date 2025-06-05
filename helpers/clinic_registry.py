# helpers/clinic_registry.py
# ==============================================================
# 讀取本地診所名冊 (clinics.csv) ＋ 中文→英文專科映射 (tag_map.yaml)
# 提供：load_registry()  / ensure_latlng()  / find_by_tag()
# ==============================================================

from __future__ import annotations
from pathlib import Path
import time
import pandas as pd
import yaml
from helpers import gmaps_client as gc

# ---------- 檔案路徑 ----------
ROOT = Path(__file__).parent.parent           # 專案根目錄
CSV_PATH  = ROOT / "data" / "clinics_standard.csv"
MAP_PATH  = ROOT / "data" / "zh2en.yaml"

# ---------- 讀 YAML（僅執行一次） ----------
try:
    with MAP_PATH.open(encoding="utf-8") as f:
        ZH2EN: dict[str, str] = yaml.safe_load(f) or {}
except FileNotFoundError:
    # 沒找到 YAML 就用空字典；保留原 CSV 專科
    ZH2EN = {}

# ---------- 主要函式 ----------
def load_registry() -> pd.DataFrame:
    """
    讀 clinics.csv 並把中文專科轉成英文標籤
    回傳 DataFrame，欄位至少包含
        clinic_name / specialty / address / lat / lng / phone
    """
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"{CSV_PATH} 不存在，請先準備 clinics.csv")

    df = pd.read_csv(CSV_PATH)

    # 允許舊欄位名 'specialties'
    if "specialty" not in df.columns and "specialties" in df.columns:
        df = df.rename(columns={"specialties": "specialty"})

    # 中文 → 英文
    if "specialty" in df.columns:
        df["specialty"] = (
            df["specialty"]
              .fillna("")
              .apply(lambda x: ZH2EN.get(str(x).strip(), str(x).strip()))
        )

    # 確保必要欄位存在
    for col in ["lat", "lng", "phone"]:
        if col not in df.columns:
            df[col] = ""

    return df

def ensure_latlng(df: pd.DataFrame) -> pd.DataFrame:
    """
    對 DataFrame 中 lat/lng 缺值的診所
    → 呼叫 Google Geocoding 取得座標
    → 寫回 DataFrame & 原 CSV（快取）
    """
    needs_geo = df["lat"].isna() | df["lng"].isna() | (df["lat"] == "") | (df["lng"] == "")
    if not needs_geo.any():
        return df

    for idx, row in df[needs_geo].iterrows():
        geo = gc.geocode(row["address"])
        if not geo:
            continue
        loc = geo[0]["geometry"]["location"]
        df.at[idx, "lat"] = loc["lat"]
        df.at[idx, "lng"] = loc["lng"]
        time.sleep(0.25)       # 避免 QPS 過高

    # 將補完的經緯度寫回 CSV
    df.to_csv(CSV_PATH, index=False)
    return df

def find_by_tag(tag: str,
                center_lat: float,
                center_lng: float,
                radius_km: float = 8) -> list[dict]:
    """
    依英文專科 tag + 中心座標，回傳 radius 內最近 5 家診所 (dict list)
    """
    from math import radians, sin, cos, sqrt, atan2

    def _hav(lat1, lng1, lat2, lng2):
        R = 6371
        dlat, dlng = radians(lat2 - lat1), radians(lng2 - lng1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlng/2)**2
        return R * 2 * atan2(sqrt(a), sqrt(1-a))

    df = load_registry()
    df = df[df["specialty"] == tag]
    if df.empty:
        return []

    df = ensure_latlng(df)

    df["dist_m"] = df.apply(
        lambda r: round(_hav(center_lat, center_lng, r["lat"], r["lng"]) * 1000),
        axis=1
    )
    df = df[df["dist_m"] <= radius_km * 1000].sort_values("dist_m")
    return df.head(5).to_dict("records")
