# utils_menu.py  ← 建議放根目錄，供多檔 import
def choose(options, title):
    """
    在終端機列出選單並回傳選定項的內容。
    ‧ options: list[str]  要顯示的選項
    ‧ title:   str        標題
    """
    if not options:
        raise ValueError("選單沒有任何項目！")

    while True:
        print(f"\n=== {title} ===")
        for idx, label in enumerate(options, 1):
            print(f"[{idx}] {label}")
        usr = input("請輸入編號 › ").strip()

        if not usr.isdigit():
            print("⚠ 請輸入數字編號。")
            continue

        idx = int(usr)
        if 1 <= idx <= len(options):
            return options[idx - 1]

        print(f"⚠ 超出範圍（1–{len(options)}），請重新輸入。")
