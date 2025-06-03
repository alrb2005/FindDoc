from pathlib import Path
from summary_utils import (load_fhir_json, load_prompt_template,
                           build_prompt, call_gpt)
import sys
from utils_menu import choose

DATA     = Path("data")
PROMPT_T = load_prompt_template("prompts/base_prompt.txt")

# ---------- 從 CLI 借用輔助 ----------
def patient_name(p_json):
    if "name" in p_json and p_json["name"]:
        n0 = p_json["name"][0]
        return n0.get("text") or " ".join(n0.get("given", [])) + " " + n0.get("family", "")
    return "UnknownName"

# ---------- 主程式 ----------
def main():
    # ▍Step 1 選擇病患 / 資源 / 檔案
    patients = sorted([d for d in DATA.iterdir() if d.is_dir()])
    labels   = [f"{patient_name(load_fhir_json(d/'Patient.json'))} ({d.name})" for d in patients]
    pdir     = patients[labels.index(choose(labels, "病患清單"))]

    res_types = sorted({f.stem.split("_")[0] for f in pdir.glob("*.json") if f.stem != "Patient"})
    rtype     = choose(res_types, f"{pdir.name} 資源類型")
    files     = [f for f in pdir.glob(f"{rtype}_*.json")]
    f_lab_map = {f.stem.split("_")[1]: f for f in files}
    fid       = choose(list(f_lab_map.keys()), f"{rtype} 檔案 ID")
    res_data  = load_fhir_json(f_lab_map[fid])

    # ▍Step 2 取得首回合摘要
    prompt0 = build_prompt(PROMPT_T, res_data)
    messages = [{"role": "user", "content": prompt0}]
    answer = call_gpt(prompt0)
    messages.append({"role": "assistant", "content": answer})
    print("\n=== GPT 首次摘要 ===\n" + answer)

    # ▍Step 3 聊天迴圈
    print("\n（輸入 exit 離開）")
    while True:
        user_q = input("\n你：")
        if user_q.strip().lower() == "exit":
            print("離開聊天。")
            break
        messages.append({"role": "user", "content": user_q})
        # 把對話歷史一起送出
        ans = call_gpt(prompt=None, messages=messages)  # 改寫 call_gpt 支援 messages 參數
        messages.append({"role": "assistant", "content": ans})
        print("\nGPT：" + ans)

if __name__ == "__main__":
    main()
