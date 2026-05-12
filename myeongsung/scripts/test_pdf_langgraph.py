import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf_langgraph_service import create_pdf_extraction_graph

def main():
    target_pdf = "data/한국에너지공단.pdf"
    # log_path = "tests/results/missing_fields_log.json"
    log_path = "tests/results/mvp_missing_fields_log.json"
    
    with open(target_pdf, "rb") as f:
        file_content = f.read()

    print(f"🚀 LangGraph 기반 MVP 구조 추출 시작: {target_pdf}")
    
    initial_state = {
        "file_path": target_pdf,
        "file_content": file_content,
        "log_path": log_path,
        # 아래 값들은 노드들을 거치며 채워짐
        "upstage_result": {},
        "full_content_text": "",
        "element_map": {},
        "page_dimensions": {},
        "extracted_data": None,
        "missing_fields": []
    }
    
    graph = create_pdf_extraction_graph()
    
    # 그래프 실행
    final_state = graph.invoke(initial_state)
    
    print("\n" + "="*50)
    print("✅ 분석 및 검증 완료!")
    print("="*50)
    
    extracted = final_state["extracted_data"]
    print(f"기업명: {extracted.company_name}")
    print(f"공고명: {extracted.notice_name}")
    print(f"발견된 모집 부문 수: {len(extracted.sections)}")
    print(f"발견된 전형 절차 수: {len(extracted.processes)}")
    print(f"발견된 제출 서류 수: {len(extracted.documents)}")
    
    missing = final_state["missing_fields"]
    print("\n⚠️ 누락되거나 비어있는 필드 (Summary):")
    for m in missing:
        print(f" - {m}")
        
    print(f"\n상세 로그가 {log_path} 에 저장되었습니다.")

if __name__ == "__main__":
    main()
