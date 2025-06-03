"""
下載 N 位病患：
  data/<pid>/Patient.json                     （單檔）
  data/<pid>/Condition_<cid>.json             （一筆一檔，沒抓過才寫）
  data/<pid>/Observation_<oid>.json
  data/<pid>/MedicationRequest_<mid>.json
"""

import requests, json, pathlib, time

BASE   = "https://hapi.fhir.org/baseR4"
DATA   = pathlib.Path("data")
COUNT  = 10 # 下載病患數量
CHILD_RES = ["Observation", "Condition", "MedicationRequest"]
HDRS   = {"Accept": "application/fhir+json"}

def fhir_get(url):
    r = requests.get(url, headers=HDRS, timeout=30)
    r.raise_for_status()
    return r.json()

def save_json(obj, path: pathlib.Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def main():
    print(f"=== 下載 {COUNT} 位病患 ===")
    patients = fhir_get(f"{BASE}/Patient?_count={COUNT}").get("entry", [])

    for idx, entry in enumerate(patients, 1):
        p_res = entry["resource"]
        pid   = p_res["id"]
        p_dir = DATA / pid
        p_dir.mkdir(parents=True, exist_ok=True)

        # Patient.json 如不存在才寫，避免常改動
        p_json = p_dir / "Patient.json"
        if not p_json.exists():
            save_json(p_res, p_json)

        print(f"[{idx}/{COUNT}] Patient {pid}")

        # 下載子資源，逐筆判斷是否已存在
        for rtype in CHILD_RES:
            url = f"{BASE}/{rtype}?subject=Patient/{pid}&_count=100"
            bundle = fhir_get(url)
            new_cnt = 0
            for e in bundle.get("entry", []):
                res  = e["resource"]
                rid  = res["id"]
                path = p_dir / f"{rtype}_{rid}.json"
                if path.exists():
                    continue                # 同筆紀錄已抓過
                save_json(res, path)
                new_cnt += 1
            print(f"  └─ {rtype}: +{new_cnt} new")
            time.sleep(0.2)  # 防限流

    print("✔ 完成！僅新增未抓過的單筆資源。")

if __name__ == "__main__":
    main()
