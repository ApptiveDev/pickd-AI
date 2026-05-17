import os
import json
import requests
from typing import TypedDict, List, Dict, Any, Optional
from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.job_dto import JobPostingCreate

# 1. State 정의
class PDFAnalysisState(TypedDict):
    file_path: str
    file_content: bytes
    upstage_result: dict
    full_content_text: str
    element_map: dict
    page_dimensions: dict
    extracted_data: Optional[JobPostingCreate]
    missing_fields: List[str]
    log_path: str

# 2. Node 함수들

def extract_text_upstage(state: PDFAnalysisState) -> PDFAnalysisState:
    """Upstage API를 호출하여 PDF에서 텍스트 및 표 추출"""
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise ValueError("UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다.")

    url = "https://api.upstage.ai/v1/document-ai/layout-analysis"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"document": ("document.pdf", state["file_content"], "application/pdf")}
    
    print("[Node 1] Upstage Layout Analysis 호출 중...")
    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()
    result = response.json()
    
    extracted_content = []
    element_map = {}
    page_dimensions = {}
    
    for pg in result.get("pages", []):
        page_dimensions[pg.get("page")] = {"width": pg.get("width"), "height": pg.get("height")}

    for idx, element in enumerate(result.get("elements", [])):
        page_num = element.get("page")
        category = element.get("category")
        content = element.get("content", {}).get("text", "")
        
        element_map[idx] = element
        prefix = f"[ID:{idx}, Page:{page_num}] " if page_num else f"[ID:{idx}] "
        
        if category == "table":
            html = element.get("content", {}).get("html", "")
            if html:
                extracted_content.append(f"\n{prefix}[Table]\n{html}\n")
            else:
                extracted_content.append(f"\n{prefix}[Table Text]\n{content}\n")
        else:
            extracted_content.append(f"{prefix}{content}")

    full_content = "\n".join(extracted_content)
    
    return {
        "upstage_result": result,
        "full_content_text": full_content,
        "element_map": element_map,
        "page_dimensions": page_dimensions
    }


def extract_structured_data(state: PDFAnalysisState) -> PDFAnalysisState:
    """GPT-4o를 사용하여 구조화된 데이터 추출 (MVP 엔티티 기준)"""
    print("[Node 2] LLM(GPT-4o)을 이용한 데이터 추출 중...")
    
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 대한민국 최고의 채용 공고 분석 AI 전문가입니다.\n"
            "제공된 PDF 파싱 데이터(ID, Page 정보 포함)를 바탕으로 MVP 요구사항에 맞는 구조화된 JSON 데이터를 생성하세요.\n\n"
            "### 💎 초정밀 추출 원칙\n"
            "1. **데이터 무결성**: 정보가 절대적으로 없으면 null로 두되, 유추 가능한 문맥이 있다면 적극 활용하세요.\n"
            "2. **날짜 표준화**: 모든 날짜는 반드시 **'YYYY-MM-DDTHH:MM:SS'** 형식을 따르세요.\n"
            "3. **표(Table) 분석**: [Table] 태그 내 HTML을 분석할 때, 각 행(Row)을 하나의 독립된 모집 부문(section)으로 간주하세요.\n"
            "4. **계층적 정확성**: '공고(Notice)' → '모집 부문(sections)' → '자격요건(qualifications)' 및 '우대사항(preferences)' 관계를 정확히 매핑하세요.\n"
            "5. **전형 절차 및 제출 서류**: 전형 단계와 일정을 processes에, 제출 서류 및 방법을 documents에 매핑하세요.\n"
            "6. **직무 및 업무 내용 통합**: 세부 직무명이나 상세 업무 설명이 있다면 `job_title`과 `responsibilities`에 모두 통합하여 작성하세요.\n"
            "7. 모든 필드에 대해 element_id와 page 번호로 출처(citations)를 증명하세요."
        )),
        ("user", "다음은 분석할 PDF 문서 데이터입니다:\n\n{content}")
    ])
    
    chain = prompt | llm.with_structured_output(JobPostingCreate)
    structured_result = chain.invoke(
        {"content": state["full_content_text"]},
        config={"run_name": "pdf-langgraph-extraction"}
    )
    
    return {"extracted_data": structured_result}

def find_empty_fields(obj: Any, prefix: str = "") -> List[str]:
    """재귀적으로 빈 필드를 찾습니다."""
    empty_fields = []
    
    if isinstance(obj, BaseModel):
        for field_name, field_info in obj.model_fields.items():
            value = getattr(obj, field_name)
            new_prefix = f"{prefix}.{field_name}" if prefix else field_name
            
            if value is None or value == "" or value == []:
                empty_fields.append(new_prefix)
            elif isinstance(value, list):
                if not value:
                    empty_fields.append(new_prefix)
                else:
                    for i, item in enumerate(value):
                        empty_fields.extend(find_empty_fields(item, f"{new_prefix}[{i}]"))
            elif isinstance(value, BaseModel):
                empty_fields.extend(find_empty_fields(value, new_prefix))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if v is None or v == "" or v == []:
                empty_fields.append(new_prefix)
            elif isinstance(v, (dict, list)):
                empty_fields.extend(find_empty_fields(v, new_prefix))
                
    return empty_fields

def validate_and_log(state: PDFAnalysisState) -> PDFAnalysisState:
    """추출되지 않은 필드를 식별하고 로그를 저장"""
    print("[Node 3] 누락된 필드 검증 및 로깅 중...")
    extracted = state["extracted_data"]
    missing = find_empty_fields(extracted)
    
    import re
    # 배열 인덱스만 제거하여 구조적인 필드명만 남김 (예: sections[0].workplace -> sections.workplace)
    unique_missing_base = sorted(list(set([re.sub(r'\[\d+\]', '', m) for m in missing])))
    
    log_data = {
        "file": state.get("file_path", "unknown"),
        "total_missing_count": len(missing),
        "missing_fields_raw": missing,
        "missing_fields_summary": unique_missing_base
    }
    
    log_path = state.get("log_path", "missing_fields_log.json")
    
    # 기존 로그가 있으면 읽어서 추가
    all_logs = []
    if os.path.exists(log_path):
        with open(log_path, 'r', encoding='utf-8') as f:
            try:
                all_logs = json.load(f)
            except json.JSONDecodeError:
                all_logs = []
                
    all_logs.append(log_data)
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(all_logs, f, ensure_ascii=False, indent=2)
        
    print(f"[✓] 누락된 필드 {len(missing)}개 발견. 로그 저장 완료: {log_path}")
    
    return {"missing_fields": unique_missing_base}


# 3. Graph 구성
def create_pdf_extraction_graph():
    workflow = StateGraph(PDFAnalysisState)
    
    workflow.add_node("extract_text_upstage", extract_text_upstage)
    workflow.add_node("extract_structured_data", extract_structured_data)
    workflow.add_node("validate_and_log", validate_and_log)
    
    workflow.set_entry_point("extract_text_upstage")
    workflow.add_edge("extract_text_upstage", "extract_structured_data")
    workflow.add_edge("extract_structured_data", "validate_and_log")
    workflow.add_edge("validate_and_log", END)
    
    return workflow.compile()
