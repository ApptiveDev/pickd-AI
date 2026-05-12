import os
import requests
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.job_dto import JobPostingCreate


# ──────────────────────────────────────────────
# 1. 스크래핑 계층
# ──────────────────────────────────────────────

def _scrape_url_multimodal(url: str, firecrawl_api_key: str) -> dict:
    """Firecrawl v2: 마크다운 + 스크린샷 + 메타데이터를 한번에 획득"""
    try:
        response = requests.post(
            'https://api.firecrawl.dev/v2/scrape',
            headers={
                'Authorization': f'Bearer {firecrawl_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'url': url,
                'formats': ['markdown', 'screenshot'],
                'waitFor': 3000,   # SPA / lazy-load 대기
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        return {
            "markdown": data.get("markdown", ""),
            "screenshot_url": data.get("screenshot", ""),
            "metadata": data.get("metadata", {}),
        }
    except Exception as e:
        print(f"[!] 스크래핑 실패 ({url}): {e}")
        return {"markdown": "", "screenshot_url": "", "metadata": {}}


# ──────────────────────────────────────────────
# 2. 비전(Vision) 엔진 — Gemini 2.0 Flash
# ──────────────────────────────────────────────

_VISION_SYSTEM_PROMPT = (
    "당신은 대한민국 채용 공고 이미지 분석 전문가입니다.\n"
    "제공된 스크린샷에서 모든 텍스트(표, 이미지 공고, Iframe 포함)를 시각적으로 읽어 구조화된 데이터를 추출하세요.\n\n"
    "### 💎 초정밀 비전 추출 원칙\n"
    "1. **이미지 속 표 분석**: 공고가 통이미지로 되어 있는 경우, 표 형태의 모집 부문을 행(Row) 단위로 쪼개어 각각의 `sections`로 생성하세요.\n"
    "2. **글로벌 정보 파악**: 공고 상/하단에 적힌 공통 자격요건, 우대사항, 복리후생을 모든 직무 부문에 공통적으로 적용(Inheritance)하세요.\n"
    "3. **누락 방지**: 마크다운 텍스트에서 빠지기 쉬운 '이미지 내부의 작은 글씨'나 '아이콘 옆의 텍스트'를 정밀하게 읽어내세요.\n\n"
    "### 규칙\n"
    "- 정보가 이미지에 절대 없으면 null로 두되, 유추 가능한 문맥이 있다면 적극 활용할 것.\n"
    "- Category: FULL_TIME, INTERN, EXPERIENTIAL_INTERN, CONTRACT, FREELANCER"
)

def _analyze_with_vision(image_url: str, google_api_key: str) -> Optional[JobPostingCreate]:
    """Gemini 2.0 Flash로 공고 스크린샷을 시각적으로 분석"""
    from google import genai
    from google.genai import types
    import PIL.Image
    import io

    client = genai.Client(api_key=google_api_key)

    try:
        img_response = requests.get(image_url, timeout=30)
        img_response.raise_for_status()
        image = PIL.Image.open(io.BytesIO(img_response.content))

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[image, _VISION_SYSTEM_PROMPT],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=JobPostingCreate.model_json_schema(),
                temperature=0,
            )
        )
        return JobPostingCreate(**json.loads(response.text))
    except Exception as e:
        print(f"[!] 비전 분석 실패: {e}")
        return None


# ──────────────────────────────────────────────
# 3. 텍스트 엔진 — GPT-4o (고도화 프롬프트)
# ──────────────────────────────────────────────

_TEXT_SYSTEM_PROMPT = (
    "당신은 대한민국 최고의 채용 공고 분석 AI 전문가입니다.\n"
    "제공된 마크다운 텍스트를 바탕으로 구조화된 채용 정보를 추출하세요.\n\n"
    "### 💎 초정밀 텍스트 추출 원칙\n"
    "1. **웹 그리드/표 행 단위 분리**: 모집 부문이 나열된 마크다운 테이블이나 리스트를 분석하여, 각 직무를 독립된 `sections`로 분리하세요.\n"
    "2. **공통 문맥 상속 (Context Inheritance)**: 페이지 상단의 공통 자격요건, 전형단계, 유의사항은 하위 모든 모집 부문(`sections`)에 자동으로 포함시키세요.\n"
    "3. **데이터 무결성 및 복원**: 누락된 필드가 있더라도 문서 내 다른 위치에서 정보를 찾아낼 수 있다면 이를 반영하여 `None`을 최소화하세요.\n"
    "4. **날짜 표준화 (중요)**: 모든 날짜는 반드시 **'YYYY-MM-DDTHH:MM:SS' (ISO 8601)** 형식을 따르세요. 마감일의 경우 시간 정보가 없다면 '23:59:59'로 채워 DB 필터링이 가능하게 하세요.\n\n"
    "### 사고 과정(Chain-of-Thought) — 초정밀 모드\n"
    "Step 1: 페이지 전체에서 기업명과 접수 마감일을 먼저 확정한다.\n"
    "Step 2: 모든 직무에 공통으로 적용되는 자격/우대/복지 정보를 따로 메모한다.\n"
    "Step 3: 각 직무별 모집 요강을 개별 섹션으로 생성하고, Step 2의 공통 정보를 병합(Merge)한다.\n"
    "Step 4: 전형 절차와 제출 서류를 정리한다.\n"
    "Step 5: 모든 정보에 대한 원문 출처(Citations)를 기록한다."
)

def _analyze_with_text(markdown: str) -> Optional[JobPostingCreate]:
    """GPT-4o로 마크다운 텍스트를 분석"""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", _TEXT_SYSTEM_PROMPT),
        ("user", "다음 채용 공고 마크다운을 분석하여 구조화된 데이터를 추출해주세요:\n\n{markdown}")
    ])
    chain = prompt | llm.with_structured_output(JobPostingCreate)
    try:
        return chain.invoke(
            {"markdown": markdown},
            config={"run_name": "url-text-engine"}
        )
    except Exception as e:
        print(f"[!] 텍스트 분석 실패: {e}")
        return None


# ──────────────────────────────────────────────
# 4. 지능적 병합 엔진
# ──────────────────────────────────────────────

def _smart_merge(text_result: Optional[JobPostingCreate],
                 vision_result: Optional[JobPostingCreate]) -> JobPostingCreate:
    """
    텍스트 엔진과 비전 엔진의 결과를 지능적으로 병합.
    원칙: 텍스트 결과를 기본으로 하되, 비전 결과가 더 풍부한 필드는 비전 결과를 채택.
    """
    # 둘 다 없으면 에러
    if not text_result and not vision_result:
        raise ValueError("텍스트 분석과 비전 분석 모두 실패했습니다.")

    # 하나만 있으면 그것을 사용
    if not text_result:
        return vision_result
    if not vision_result:
        return text_result

    merged = text_result.model_copy(deep=True)

    # sections: 비전이 더 많은 부문을 발견했으면 비전 결과 채택
    if len(vision_result.sections) > len(merged.sections):
        merged.sections = vision_result.sections

    # processes: 비어있으면 비전에서 가져옴
    if not merged.processes and vision_result.processes:
        merged.processes = vision_result.processes

    # documents
    if not merged.documents and vision_result.documents:
        merged.documents = vision_result.documents

    # company_info: 비전이 더 풍부하면 채택
    if vision_result.company_info:
        if not merged.company_info:
            merged.company_info = vision_result.company_info
        else:
            # 개별 필드 단위로 보완
            for field_name in vision_result.company_info.model_fields:
                vision_val = getattr(vision_result.company_info, field_name, None)
                merged_val = getattr(merged.company_info, field_name, None)
                if vision_val and not merged_val:
                    setattr(merged.company_info, field_name, vision_val)

    # guideline
    if vision_result.guideline:
        if not merged.guideline:
            merged.guideline = vision_result.guideline
        else:
            for field_name in vision_result.guideline.model_fields:
                vision_val = getattr(vision_result.guideline, field_name, None)
                merged_val = getattr(merged.guideline, field_name, None)
                if vision_val and not merged_val:
                    setattr(merged.guideline, field_name, vision_val)

    # 단순 필드 보완 (비어있으면 비전에서 가져옴)
    for field_name in ["employment_type", "headcount", "region_1depth", "workplace_address", "notice_url"]:
        merged_val = getattr(merged, field_name, None)
        vision_val = getattr(vision_result, field_name, None)
        if not merged_val and vision_val:
            setattr(merged, field_name, vision_val)

    # citations 합치기 (중복 제거)
    existing_contents = {c.content[:50] for c in merged.citations}
    for cit in vision_result.citations:
        if cit.content[:50] not in existing_contents:
            merged.citations.append(cit)

    return merged


# ──────────────────────────────────────────────
# 5. 메인 엔트리포인트
# ──────────────────────────────────────────────

def analyze_job_url(url: str) -> JobPostingCreate:
    """
    멀티모달 하이브리드 분석:
    1) Firecrawl로 마크다운 + 스크린샷 획득
    2) GPT-4o(텍스트) + Gemini(비전) 병렬 분석
    3) 지능적 병합으로 최고 정확도 달성
    """
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")

    if not firecrawl_api_key:
        raise ValueError("FIRECRAWL_API_KEY가 설정되지 않았습니다.")

    # 1. 멀티모달 데이터 획득
    print(f"[*] 멀티모달 스크래핑 시작: {url}")
    scrape_data = _scrape_url_multimodal(url, firecrawl_api_key)
    markdown = scrape_data["markdown"]
    screenshot_url = scrape_data["screenshot_url"]

    if not markdown and not screenshot_url:
        raise ValueError("URL에서 마크다운과 스크린샷 모두 획득에 실패했습니다.")

    # 2. 텍스트 엔진 실행
    text_result = None
    if markdown:
        print("[*] 텍스트 엔진(GPT-4o) 분석 중...")
        text_result = _analyze_with_text(markdown)

    # 3. 비전 엔진 실행 (항상 실행하여 보완)
    vision_result = None
    if screenshot_url and google_api_key:
        print("[*] 비전 엔진(Gemini 2.0 Flash) 분석 중...")
        vision_result = _analyze_with_vision(screenshot_url, google_api_key)

    # 4. 지능적 병합
    print("[*] 텍스트 + 비전 결과 병합 중...")
    merged_result = _smart_merge(text_result, vision_result)

    # 5. 출처 링크 보완
    from urllib.parse import quote
    if merged_result.citations:
        for citation in merged_result.citations:
            safe_text = quote(citation.content.replace("\n", " ").strip()[:50])
            citation.source_url = f"{url}#:~:text={safe_text}"

    print(f"[✓] 분석 완료: {len(merged_result.sections)}개 부문, "
          f"{len(merged_result.citations)}개 출처")
    return merged_result
