# cli_menu.py  ─ 病患清單顯示「姓名 (PatientID)」

from pathlib import Path
from summary_utils import load_fhir_json, load_prompt_template, build_prompt, call_gpt
from utils_menu import choose

DATA      = Path("data")
TEMPLATE  = load_prompt_template("prompts/base_prompt.txt")

# ----------------- 輔助 -----------------
def patient_name(p_json):
    if "name" in p_json and p_json["name"]:
        n0 = p_json["name"][0]
        return n0.get("text") or " ".join(n0.get("given", [])) + " " + n0.get("family", "")
    return "UnknownName"

def first_date(res):
    for k in ("effectiveDateTime", "onsetDateTime", "authoredOn", "issued"):
        if k in res:
            return res[k][:10]
    return "UnknownDate"

def patient_label(p_dir: Path):
    p_json = load_fhir_json(p_dir / "Patient.json")
    pid  = p_json.get("id", p_dir.name)
    name = patient_name(p_json).strip()
    return f"{name} ({pid})"            # ← 顯示 ID


# ----------------- 主流程 ---------------
def main():
    # ① 病患清單
    dirs   = sorted([d for d in DATA.iterdir() if d.is_dir()])
    labels = [patient_label(d) for d in dirs]
    pat_lab = choose(labels, "病患清單")
    pat_dir = dirs[labels.index(pat_lab)]

    # ② 資源類型
    files = list(pat_dir.glob("*.json"))
    types = sorted({f.stem.split("_")[0] for f in files if f.stem != "Patient"})
    rtype = choose(types, f"{pat_lab} 的資源類型")

    # ③ 日期/ID 清單（多筆時）
    res_files = [f for f in files if f.stem.startswith(rtype + "_")]
    if not res_files:
        print(f"❗ 沒有找到任何 {rtype} 檔案")
        return

    labels2, pmap = [], {}
    for f in res_files:
        res  = load_fhir_json(f)
        date = first_date(res)
        rid  = f.stem.split("_")[1]
        lab  = f"{date} ({rid})"        # e.g. 2023-05-04 (4e2af)
        labels2.append(lab)
        pmap[lab] = f

    res_lab  = choose(labels2, f"{rtype} 日期清單")
    res_data = load_fhir_json(pmap[res_lab])

    # ④ GPT 摘要
    prompt = build_prompt(TEMPLATE, res_data)
    print("\n=== GPT 回覆 ===\n")
    print(call_gpt(prompt))

if __name__ == "__main__":
    main()
