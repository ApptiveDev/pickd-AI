import os
import sys
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv

# sys.path에 app 폴더 상위 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.experience_extraction_service import extract_experiences_from_text

# .env 로드
load_dotenv()

def run_batch_extraction():
    # 타겟 파일 리스트
    target_files = [
        "국민건강.pdf",
        "한국거래소.pdf",
        "한국전력공사 합격자소서.pdf",
        "한전2.pdf"
    ]
    
    workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    results_dir = os.path.join(workspace_dir, "tests", "results")
    os.makedirs(results_dir, exist_ok=True)
    
    all_results = {}
    
    print("=== 공기업 자소서 경험 추출 배치 테스트 시작 ===\n")
    
    for filename in target_files:
        filepath = os.path.join(workspace_dir, filename)
        if not os.path.exists(filepath):
            print(f"⚠️ 파일을 찾을 수 없습니다: {filename} (경로: {filepath}) - 건너뜁니다.")
            continue
            
        print(f"🔄 분석 중: {filename}...")
        try:
            # PyMuPDF로 텍스트 추출
            doc = fitz.open(filepath)
            text_list = []
            for page in doc:
                text_list.append(page.get_text())
            full_text = "\n".join(text_list)
            
            if not full_text.strip():
                print(f"❌ {filename}에서 텍스트를 추출하지 못했습니다.")
                continue
                
            # 경험 추출 실행
            extraction_result = extract_experiences_from_text(full_text)
            
            # 결과 저장
            experiences_list = []
            for exp in extraction_result.experiences:
                experiences_list.append(exp.model_dump())
                
            all_results[filename] = {
                "status": "SUCCESS",
                "extracted_count": len(experiences_list),
                "experiences": experiences_list
            }
            
            print(f"✅ 완료: {filename} (추출된 경험 후보: {len(experiences_list)}개)")
            
        except Exception as e:
            all_results[filename] = {
                "status": "FAILED",
                "error": str(e)
            }
            print(f"❌ 실패: {filename} (오류: {e})")
            
        print("-" * 50)
        
    # 결과 JSON 저장
    output_path = os.path.join(results_dir, "experience_extraction_report.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
        
    print(f"\n🎉 모든 배치 분석이 완료되었습니다!")
    print(f"📊 결과 보고서 저장 위치: {output_path}")

if __name__ == "__main__":
    run_batch_extraction()
