import os
import sys
import glob
import json
from collections import defaultdict
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pdf_langgraph_service import create_pdf_extraction_graph

def extract_fields_and_check_empty(obj: BaseModel, table_name: str, stats: dict):
    """
    재귀적으로 Pydantic 모델을 순회하며 테이블(Entity)별로 필드의 None/Empty 여부를 점수화하기 위한 통계를 수집합니다.
    """
    if table_name not in stats:
        stats[table_name] = {"total_records": 0, "fields": defaultdict(lambda: {"total": 0, "empty": 0})}
    
    stats[table_name]["total_records"] += 1
    
    for field_name, field_info in obj.model_fields.items():
        # citations 필드는 백엔드 엔티티 매핑에 포함되지 않으므로 통계에서 제외 (선택적)
        if field_name == "citations":
            continue
            
        value = getattr(obj, field_name)
        
        # 하위 리스트나 모델인 경우 재귀 호출
        if isinstance(value, list) and value and isinstance(value[0], BaseModel):
            for item in value:
                # 필드명을 이용해 테이블명 추론 (예: sections -> NoticeSection)
                child_table = field_name.capitalize()
                extract_fields_and_check_empty(item, child_table, stats)
            continue
        elif isinstance(value, BaseModel):
            extract_fields_and_check_empty(value, field_name.capitalize(), stats)
            continue
            
        # 단일 필드 통계
        stats[table_name]["fields"][field_name]["total"] += 1
        if value is None or value == "" or value == []:
            stats[table_name]["fields"][field_name]["empty"] += 1

def main():
    data_dir = "data"
    pdf_files = glob.glob(os.path.join(data_dir, "*.pdf"))
    
    if not pdf_files:
        print("분석할 PDF 파일이 없습니다.")
        return
        
    print(f"🚀 총 {len(pdf_files)}개의 PDF 파일에 대해 분석 및 평가를 시작합니다.")
    
    graph = create_pdf_extraction_graph()
    stats = {}
    file_results = []
    
    for pdf_path in pdf_files:
        print(f"\n▶ 분석 진행 중: {os.path.basename(pdf_path)}")
        try:
            with open(pdf_path, "rb") as f:
                file_content = f.read()
                
            initial_state = {
                "file_path": pdf_path,
                "file_content": file_content,
                "log_path": "tests/results/temp_log.json", # 임시 로그
                "upstage_result": {},
                "full_content_text": "",
                "element_map": {},
                "page_dimensions": {},
                "extracted_data": None,
                "missing_fields": []
            }
            
            final_state = graph.invoke(initial_state)
            extracted = final_state["extracted_data"]
            
            # 엔티티 계층 스캔 (Root: JobPostingBase -> Notice)
            extract_fields_and_check_empty(extracted, "Notice", stats)
            
            file_results.append({
                "file": os.path.basename(pdf_path),
                "status": "SUCCESS"
            })
            
        except Exception as e:
            print(f"[!] {os.path.basename(pdf_path)} 분석 실패: {e}")
            file_results.append({
                "file": os.path.basename(pdf_path),
                "status": "FAILED",
                "error": str(e)
            })

    # 통계를 기반으로 점수화
    report = {
        "files_processed": len(pdf_files),
        "file_results": file_results,
        "table_scores": {}
    }
    
    print("\n" + "="*60)
    print("📊 테이블(Entity) 별 필드 채움(Fill Rate) 평가 결과")
    print("="*60)
    
    for table, stat in stats.items():
        print(f"\n[ 📑 {table} ] - 추출된 레코드 수: {stat['total_records']}")
        table_total_fields = 0
        table_empty_fields = 0
        
        field_scores = {}
        for field, counts in stat["fields"].items():
            total = counts["total"]
            empty = counts["empty"]
            filled = total - empty
            fill_rate = (filled / total * 100) if total > 0 else 0
            
            table_total_fields += total
            table_empty_fields += empty
            
            field_scores[field] = {
                "total": total,
                "empty": empty,
                "fill_rate_percent": round(fill_rate, 1)
            }
            
            # 콘솔 출력 포맷팅
            bar_len = int(fill_rate / 10)
            bar = "█" * bar_len + "░" * (10 - bar_len)
            print(f"  - {field:25s} [{bar}] {fill_rate:5.1f}% (None: {empty}/{total})")
            
        table_fill_rate = ((table_total_fields - table_empty_fields) / table_total_fields * 100) if table_total_fields > 0 else 0
        report["table_scores"][table] = {
            "record_count": stat["total_records"],
            "overall_fill_rate": round(table_fill_rate, 1),
            "fields": field_scores
        }
        
    # 결과 저장
    output_path = "tests/results/pdf_batch_evaluation_report.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print(f"\n💾 전체 평가 리포트가 {output_path} 에 저장되었습니다.")

if __name__ == "__main__":
    main()
