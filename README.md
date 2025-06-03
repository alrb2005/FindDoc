# FindDoc
這是一個參考 Stanford LLM on FHIR 專案的 Python 版本，能夠讀取模擬 FHIR JSON 並用 GPT 模型產生中文摘要病例，協助尋找周遭相關診所。

![](https://github.com/alrb2005/FindDoc/blob/master/Someone_lost.png?raw=true)

## 使用方式

# 建立虛擬環境（可選）
python -m venv .venv
.venv\Scripts\activate

#進入虛擬環境
.\.venv\Scripts\activate.bat

# 安裝依賴套件
pip install -r requirements.txt

# 設定 OpenAI API 金鑰

OPENAI_API_KEY=你的OpenAI金鑰

GMAPS_API_KEY=你的Google map 金鑰

# 編輯 .env 檔案

#Run Demo

python run_full_demo.py 

  --patient_dir data/597072    # 模擬另一位病人
  
  --loc "大安區"               # 台北地區範例
  
  --symptom "胸悶"              # 症狀相同

#可以複製這個當作範例
python run_full_demo.py ^
  --patient_dir data\597072 ^
  --loc "大安區" ^
  --symptom "胸悶"
