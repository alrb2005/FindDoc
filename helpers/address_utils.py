"""
────────────────────────────────────────────────────────────
將 Google Maps formatted_address → 『標準化地址鍵值』
‣ 覆蓋處理：
    1. 全形英數／標點 → 半形
    2. 「台」→「臺」；「台灣省」→「臺灣」
    3. 去掉逗號、空白、郵遞區號 (3~5 碼開頭)
    4. 只保留到「號」(去除之號、樓層、Room)
    5. 巷弄段前的 0 取代英文字母  (Rd. / Road / St.  → 路 / 街)
    6. 破折號 ↦ 一般連字號
‣ 輔助：
    get_variants(addr_key) → 生成「門牌號 ±1、±2、±3」三個鍵值
"""

from __future__ import annotations
import re

# 1. 全形英數轉半形
def _to_half_width(s: str) -> str:
    return "".join(
        chr(ord(ch) - 65248) if 65281 <= ord(ch) <= 65374 else ch
        for ch in s
    )

# 2. 台/臺 & 路名英翻中
_TW_REPLACE = {
    "台灣": "臺灣",
    "台北": "臺北",
    "台中": "臺中",
    "臺灣省": "臺灣",
    # 英文路名尾碼
    " Road": "路",
    " Rd.": "路",
    " Street": "街",
    " St.": "街",
    " Avenue": "大道",
    " Ave.": "大道",
    " Boulevard": "大道",
    " Ln.": "巷",
}

# 3. 正規化主要函式
def normalize(addr: str) -> str:
    """
    傳入任何地址字串，回傳「縣市區 + 道路 + 門牌號」最小鍵值。
    若輸入為空回 ""。
    """
    if not addr:
        return ""

    # (a) 去前後空白
    addr = addr.strip()

    # (b) 郵遞區號 (3~5 碼) 開頭 → 去掉
    addr = re.sub(r"^\d{3,5}", "", addr)

    # (c) 全形→半形
    addr = _to_half_width(addr)

    # (d) 替換台/臺、英文路名
    for k, v in _TW_REPLACE.items():
        addr = addr.replace(k, v)

    # (e) 去空格、逗號、中文頓號
    addr = re.sub(r"[ ,，、]", "", addr)

    # (f) 標準化破折號
    addr = addr.replace("－", "-").replace("–", "-")

    # (g) 只保留門牌號 (例：…8號／8號-1／8號之3)，捨棄樓層房號
    m = re.search(r"(.+?[0-9]+號(?:-\d+)?(?:之\d+)?)", addr)
    if m:
        addr = m.group(1)

    # (h) 最終保險 strip
    return addr.strip()

# 4. 產生「門牌號 ±1~3」變體：用於 fuzzy 比對
def get_variants(addr_key: str, span: int = 3) -> list[str]:
    """
    給標準化後的 addr_key，若含數字門牌，產生 ±1~span 個變體。
    例如「臺北市中正區復興路100號」→ 97,98,99,100,101,102,103
    """
    m = re.search(r"(.*?)(\d+)(號.*)", addr_key)
    if not m:
        return [addr_key]  # 沒門牌號就回原字串

    pre, num_str, post = m.groups()
    num = int(num_str)
    variants = [
        f"{pre}{n}{post}" for n in range(num - span, num + span + 1)
    ]
    return variants
