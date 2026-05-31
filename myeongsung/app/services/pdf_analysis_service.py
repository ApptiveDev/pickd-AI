"""
채용공고 PDF를 Upstage Document AI로 파싱하고,
GPT-4o를 통해 구조화된 JobPostingCreate 데이터로 변환하는 서비스.
"""

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import GPT_MODEL
from app.schemas.job_dto import JobPostingCreate
from app.utils.upstage_parser import parse_pdf_with_upstage, enrich_citations_with_bbox


# ──────────────────────────────────────────────────────────────────────────────
# LLM 프롬프트
# ──────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "당신은 대한민국 최고의 채용 공고 분석 AI 전문가입니다.\n"
    "제공된 PDF 파싱 데이터(ID, Page 정보 포함)를 바탕으로 구조화된 JSON 데이터를 생성하세요.\n\n"
    "### 💎 초정밀 추출 원칙 (최고 정확도 모드)\n"
    "1. **데이터 무결성**: 정보가 절대적으로 없으면 null로 두되, 유추 가능한 문맥이 있다면 이를 활용하세요.\n"
    "2. **날짜 표준화 (중요)**: 모든 날짜는 반드시 **'YYYY-MM-DDTHH:MM:SS' (ISO 8601)** 형식을 따르세요. "
    "시간 정보가 없다면 '00:00:00' 또는 '23:59:59'(마감일의 경우)로 채우세요.\n"
    "3. **표(Table) 행 단위 완전 탐색**: [Table] 태그 내 HTML을 분석할 때, "
    "**각 행(Row)을 하나의 독립된 모집 부문(section)**으로 간주하세요.\n"
    "4. **계층적 정확성**: '모집 부문(sections)' → '자격요건(qualifications)' → '우대사항(preferences)' "
    "관계를 1:N으로 정확히 매핑하세요.\n"
    "5. **전형 절차 및 제출 서류**: 전형 단계와 일정을 processes에, 제출 서류 및 방법을 documents에 매핑하세요.\n"
    "6. **직무 상세(responsibilities)**: 단순히 직무명만 적지 말고, 본문에 있는 업무 내용을 요약하여 반드시 포함.\n\n"
    "### 🧠 사고 과정(CoT) — 초정밀 모드\n"
    "Step 1: 기업명과 공고의 대주제(신입/경력/인턴)를 확정한다.\n"
    "Step 2: 전형 일정과 공통 자격 요건을 먼저 메모한다.\n"
    "Step 3: 모집 부문 표를 한 줄씩(Row by Row) 읽으며, 각 행을 개별 section으로 생성한다.\n"
    "Step 4: 각 section에 Step 2에서 메모한 공통 요건을 결합(Merge)한다.\n"
    "Step 5: 제출 서류와 유의사항을 빠짐없이 매핑한다.\n"
    "Step 6: 모든 필드에 대해 element_id와 page 번호로 출처를 증명한다."
)


# ──────────────────────────────────────────────────────────────────────────────
# 공개 함수
# ──────────────────────────────────────────────────────────────────────────────

def analyze_job_pdf(file_content: bytes) -> JobPostingCreate:
    """
    Upstage Document Parse를 이용해 PDF에서 텍스트 및 표를 추출하고,
    LLM을 통해 구조화된 채용 공고 데이터(JobPostingCreate)로 변환합니다.

    Args:
        file_content: PDF 파일의 바이너리 데이터

    Returns:
        JobPostingCreate: 구조화된 채용 공고 데이터

    Raises:
        ValueError: Upstage API 오류 또는 LLM 추출 실패 시
    """
    # 1. Upstage PDF 파싱 (공통 유틸 사용)
    full_content, element_map, page_dimensions = parse_pdf_with_upstage(file_content)

    # 2. GPT-4o로 구조화 데이터 추출
    llm = ChatOpenAI(model=GPT_MODEL, temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _SYSTEM_PROMPT),
        ("user", "다음은 분석할 PDF 문서 데이터입니다. 위 사고 과정에 따라 구조화된 채용 정보를 추출하고 출처를 명시해주세요:\n\n{content}")
    ])
    chain = prompt | llm.with_structured_output(JobPostingCreate)

    try:
        structured_result = chain.invoke(
            {"content": full_content},
            config={"run_name": "pdf-analysis-v2"}
        )
    except Exception as e:
        raise ValueError(f"LLM 데이터 추출 중 오류가 발생했습니다: {str(e)}")

    # 3. Citations에 bbox 좌표 및 페이지 링크 보완 (공통 유틸 사용)
    if structured_result.citations:
        enrich_citations_with_bbox(structured_result.citations, element_map, page_dimensions)

    return structured_result
