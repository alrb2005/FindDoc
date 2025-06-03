import asyncio, json, argparse
from pathlib import Path
from summary_utils import load_fhir_json, gpt_summary
from agents.recommender_worker import search_all_tags
from agents.evaluator_agent import gpt_evaluate

def main(patient_path: Path, location: str):
    fhir_json = load_fhir_json(patient_path)
    tldr, detail, tags_sorted = gpt_summary(fhir_json)

    print("TL;DR:", tldr, "\n")
    print("詳細說明:", detail, "\n")

    clinics_json = asyncio.run(
        search_all_tags(tags_sorted, location)
    )

    markdown = gpt_evaluate(
        tags_current=tags_sorted,
        tags_history=[],                 # 先無歷史交集，可後續補
        clinics_by_tag=clinics_json
    )
    print(markdown)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fhir", required=True,
                        help="FHIR JSON 檔路徑，如 data/597083/Condition_a1.json")
    parser.add_argument("--loc", required=True,
                        help="欲查詢診所地區，如 '樹林區'")
    args = parser.parse_args()
    main(Path(args.fhir), args.loc)
