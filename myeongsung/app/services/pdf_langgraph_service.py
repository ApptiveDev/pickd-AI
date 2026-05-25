"""
LangGraph 기반 PDF 채용공고 분석 파이프라인.

3단계 노드로 구성:
  1. extract_text_upstage  — Upstage API로 PDF 파싱
  2. extract_structured_data — GPT-4o로 구조화 데이터 추출
  3. validate_and_log       — 누락 필드 검증 및 로그 저장
"""

import os
import json
import re
from typing import TypedDict, List, Any, Optional

from pydantic import BaseModel
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import GPT_MODEL
from app.schemas.job_dto import JobPostingCreate
from app.utils.upstage_parser import parse_pdf_with_upstage


# ──────────────────────────────────────────────────────────────────────────────
# State 정의
# ──────────────────────────────────────────────────────────────────────────────

class PDFAnalysisState(TypedDict):
    file_path: str
    file_content: bytes
    full_content_text: str
    element_map: dict
    page_dimensions: dict
    extracted_data: Optional[JobPostingCreate]
    missing_fields: List[str]
    log_path: str


# ──────────────────────────────────────────────────────────────────────────────
# Node 1: Upstage PDF 파싱
# ──────────────────────────────────────────────────────────────────────────────

def extract_text_upstage(state: PDFAnalysisState) -> PDFAnalysisState:
    """Upstage API를 호출하여 PDF에서 텍스트 및 표를 추출합니다."""
    print("[Node 1] Upstage Layout Analysis 호출 중...")

    full_content_text, element_map, page_dimensions = parse_pdf_with_upstage(state["file_content"])

    return {
        "full_content_text": full_content_text,
        "element_map": element_map,
        "page_dimensions": page_dimensions,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Node 2: GPT-4o 구조화 데이터 추출
# ──────────────────────────────────────────────────────────────────────────────

_EXTRACTION_SYSTEM_PROMPT = (
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
)

def extract_structured_data(state: PDFAnalysisState) -> PDFAnalysisState:
    """GPT-4o를 사용하여 구조화된 데이터를 추출합니다."""
    print("[Node 2] LLM(GPT-4o)을 이용한 데이터 추출 중...")

    llm = ChatOpenAI(model=GPT_MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _EXTRACTION_SYSTEM_PROMPT),
        ("user", "다음은 분석할 PDF 문서 데이터입니다:\n\n{content}")
    ])

    chain = prompt | llm.with_structured_output(JobPostingCreate)
    structured_result = chain.invoke(
        {"content": state["full_content_text"]},
        config={"run_name": "pdf-langgraph-extraction"}
    )

    return {"extracted_data": structured_result}


# ──────────────────────────────────────────────────────────────────────────────
# Node 3: 누락 필드 검증 및 로그 저장
# ──────────────────────────────────────────────────────────────────────────────

def _find_empty_fields(obj: Any, prefix: str = "") -> List[str]:
    """재귀적으로 빈 필드(None, "", [])를 탐색합니다."""
    empty_fields = []

    if isinstance(obj, BaseModel):
        for field_name in obj.model_fields:
            value = getattr(obj, field_name)
            new_prefix = f"{prefix}.{field_name}" if prefix else field_name

            if value is None or value == "" or value == []:
                empty_fields.append(new_prefix)
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    empty_fields.extend(_find_empty_fields(item, f"{new_prefix}[{i}]"))
            elif isinstance(value, BaseModel):
                empty_fields.extend(_find_empty_fields(value, new_prefix))

    elif isinstance(obj, dict):
        for k, v in obj.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            if v is None or v == "" or v == []:
                empty_fields.append(new_prefix)
            elif isinstance(v, (dict, list)):
                empty_fields.extend(_find_empty_fields(v, new_prefix))

    return empty_fields


def validate_and_log(state: PDFAnalysisState) -> PDFAnalysisState:
    """추출되지 않은 필드를 식별하고 로그 파일에 저장합니다."""
    print("[Node 3] 누락된 필드 검증 및 로깅 중...")

    extracted = state["extracted_data"]
    missing = _find_empty_fields(extracted)

    # 배열 인덱스 제거 후 중복 없는 필드명 목록 생성 (예: sections[0].workplace → sections.workplace)
    unique_missing = sorted(set(re.sub(r"\[\d+\]", "", m) for m in missing))

    log_data = {
        "file": state.get("file_path", "unknown"),
        "total_missing_count": len(missing),
        "missing_fields_raw": missing,
        "missing_fields_summary": unique_missing,
    }

    log_path = state.get("log_path", "missing_fields_log.json")
    all_logs = []
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            try:
                all_logs = json.load(f)
            except json.JSONDecodeError:
                all_logs = []

    all_logs.append(log_data)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(all_logs, f, ensure_ascii=False, indent=2)

    print(f"[✓] 누락된 필드 {len(missing)}개 발견. 로그 저장 완료: {log_path}")
    return {"missing_fields": unique_missing}


# ──────────────────────────────────────────────────────────────────────────────
# Graph 구성
# ──────────────────────────────────────────────────────────────────────────────

def create_pdf_extraction_graph():
    """Upstage 파싱 → LLM 추출 → 검증/로깅 순서의 LangGraph를 컴파일합니다."""
    workflow = StateGraph(PDFAnalysisState)

    workflow.add_node("extract_text_upstage", extract_text_upstage)
    workflow.add_node("extract_structured_data", extract_structured_data)
    workflow.add_node("validate_and_log", validate_and_log)

    workflow.set_entry_point("extract_text_upstage")
    workflow.add_edge("extract_text_upstage", "extract_structured_data")
    workflow.add_edge("extract_structured_data", "validate_and_log")
    workflow.add_edge("validate_and_log", END)

    return workflow.compile()
