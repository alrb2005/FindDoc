"""
----------------------
手動對照檔版本：僅讀 helpers/tag_map.yaml，
若無對應，回 "<tag> clinic" 備援，不寫 log、不自動更新。
"""

from __future__ import annotations
import yaml, pathlib

# YAML 檔路徑（與本檔同資料夾）
_YAML_PATH = pathlib.Path(__file__).with_name("tag_map.yaml")

# 讀 YAML；若檔案不存在，建立空 dict
if _YAML_PATH.exists():
    _TAG_TO_KEYWORD: dict[str, str] = yaml.safe_load(
        _YAML_PATH.read_text(encoding="utf-8")
    ) or {}
else:
    _TAG_TO_KEYWORD = {}
    _YAML_PATH.write_text("", encoding="utf-8")  # 建空檔避免找不到

def to_keyword(tag: str) -> str:
    """
    傳入英文 tag，回 Google Places 搜尋用的『中文科別關鍵字』。
    若 YAML 無對應，就回 "<tag> clinic" 作備援。
    """
    return _TAG_TO_KEYWORD.get(tag, f"{tag} clinic")
