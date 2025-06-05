import argparse, json, asyncio
from pathlib import Path
from summary_utils import load_fhir_json, gpt_summary
from agents import context_builder, symptom_triage, recommender_worker, evaluator_agent
import logging

# 開啟全域 INFO（讓你自己的 logging.info() 仍會顯示）
logging.basicConfig(level=logging.INFO)

# 把 httpx／httpcore 的等級拉高到 WARNING，靜音 200 OK 訊息
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)



def load_all_fhir(patient_dir: Path):
    return [json.loads(p.read_text()) for p in patient_dir.glob("*.json")]

def main(patient_dir: Path, location: str, symptom: str):
    # 全病史摘要
    fhir_list = load_all_fhir(patient_dir)
    overall, history_tags = context_builder.build_context(fhir_list)
    print("===== 醫師摘要（過往）=====\n", overall, "\n")

    # 臨時症狀 triage → tags_current
    tags_current = symptom_triage.triage(symptom, history_tags)

    # Recommender
    clinics_json = asyncio.run(
        recommender_worker.search_all_tags(tags_current, location)
    )

    # 評估 + 推薦
    markdown = evaluator_agent.gpt_evaluate(
        tags_current=tags_current,
        tags_history=[{"tag":t,"score":3} for t in history_tags],
        clinics_by_tag=clinics_json
    )
    print(markdown)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--patient_dir", required=True, help="data/<pid>")
    ap.add_argument("--loc", required=True, help="查詢地區，如 '樹林區'")
    ap.add_argument("--symptom", required=True, help="病人臨時症狀描述")
    args = ap.parse_args()
    main(Path(args.patient_dir), args.loc, args.symptom)
