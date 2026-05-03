import os
import json
import asyncio
from dotenv import load_dotenv
from app.services.pdf_analysis_service import analyze_job_pdf
from app.services.job_analysis_service import analyze_job_url

load_dotenv()

# 평가용 데이터셋 (예시)
# 실제 운영 시에는 tests/golden_set/*.json 파일로 관리하는 것이 좋습니다.
TEST_DATASET = [
    {
        "name": "KPS_PDF",
        "type": "pdf",
        "path": "data/한국전력공사.pdf",
        "ground_truth": {
            "company_name": "한국전력공사",
            # 여기에 정답 데이터를 채워넣습니다.
        }
    },
    {
        "name": "SaramIn_URL",
        "type": "url",
        "path": "https://www.saramin.co.kr/zf_user/jobs/relay/view?isMypage=no&rec_idx=47974341",
        "ground_truth": {
            # 정답 데이터
        }
    }
]

async def evaluate_accuracy():
    print("🚀 채용 공고 추출 정확도 평가 시작...")
    
    results = []
    
    for case in TEST_DATASET:
        print(f"[*] 분석 중: {case['name']} ({case['path']})")
        try:
            if case["type"] == "pdf":
                with open(case["path"], "rb") as f:
                    content = f.read()
                    prediction = analyze_job_pdf(content)
            else:
                prediction = analyze_job_url(case["path"])
            
            # 간단한 점수 계산 로직 (예: 필드 존재 여부)
            score = 0
            important_fields = ["company_name", "notice_name", "started_at", "ended_at", "sections"]
            for field in important_fields:
                val = getattr(prediction, field, None)
                if val:
                    score += 1
            
            results.append({
                "case": case["name"],
                "score": f"{score}/{len(important_fields)}",
                "status": "Success"
            })
            
            # 결과 저장 (리뷰용)
            output_path = f"tests/results/{case['name']}_result.json"
            os.makedirs("tests/results", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(prediction.model_dump_json(indent=2))
                
        except Exception as e:
            print(f"[!] 오류 발생 ({case['name']}): {e}")
            results.append({
                "case": case["name"],
                "score": "0/5",
                "status": f"Error: {str(e)}"
            })

    print("\n" + "="*30)
    print("📊 평가 결과 요약")
    print("="*30)
    for res in results:
        print(f"- {res['case']}: {res['score']} ({res['status']})")
    print("="*30)
    print("상세 결과는 tests/results/ 디렉토리를 확인하세요.")

if __name__ == "__main__":
    asyncio.run(evaluate_accuracy())
