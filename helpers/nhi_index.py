"""
- 提供 get_specialties(addr_norm) → list[str]
"""
import csv, pathlib, pickle, os, re
from pathlib import Path
from dotenv import load_dotenv
from helpers.address_utils import normalize

# -------------------------------------------------------
#  改成「永遠讀本地診所清單，不再上網下載」
#   1) 讀取 data/clinics.csv
#   2) 如有環境變數 CLINIC_CSV_PATH → 覆寫
# -------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = Path(
    os.getenv("CLINIC_CSV_PATH",
              PROJECT_ROOT / "data" / "clinics.csv")
)
IDX_FILE = PROJECT_ROOT / "cache" / "nhi_index.pkl"
IDX_FILE.parent.mkdir(exist_ok=True)


def _build_index() -> dict[str, list[str]]:
    print("[NHI] 建索引…")
    index = {}
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            addr_key = normalize(row["address"])
            # specialties 欄位以 ; 或 、 分隔皆可
            divs = re.split(r"[、;；]", row["specialties"]) if row["specialties"] else []
            index[addr_key] = divs
    pickle.dump(index, open(IDX_FILE, "wb"))
    return index


if IDX_FILE.exists():
    _INDEX = pickle.load(open(IDX_FILE, "rb"))
else:
    _INDEX = _build_index()

def get_specialties(addr_norm: str) -> list[str]:
    """傳入標準化地址，回官方專精列表或空 list"""
    return _INDEX.get(addr_norm, [])
