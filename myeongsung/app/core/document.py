"""
Upstage Document AI 및 OpenAI 기반 문서 분석 유틸리티.

NOTE: 이 모듈은 순수 유틸 함수만 포함합니다.
    실행 스크립트 코드는 scripts/ 디렉토리 하위 별도 파일로 분리되어 있습니다.
"""

import requests
import json
from openai import OpenAI
from datetime import datetime


def get_ups_content_v2(api_key: str, filename: str) -> str:
    """
    Upstage Document Parse v2 API를 호출하여 PDF/문서에서 텍스트와 HTML 구조를 추출합니다.

    Args:
        api_key: Upstage API 키
        filename: 분석할 파일 경로

    Returns:
        추출된 전체 텍스트 (표는 HTML 구조 보존)
    """
    url = "https://api.upstage.ai/v1/document-digitization"
    headers = {"Authorization": f"Bearer {api_key}"}
    files = {"document": open(filename, "rb")}
    # 문서의 구조(표, 제목 등)를 보존하기 위해 document-parse 모델 사용
    data = {"ocr": "force", "model": "document-parse"}

    print(f"[*] Upstage API를 통해 문서 분석 중: {filename.split('/')[-1]}")
    response = requests.post(url, headers=headers, files=files, data=data)
    result = response.json()

    full_content = []

    # JSON 내 elements를 순회하며 HTML 구조와 텍스트를 모두 수집
    for el in result.get("elements", []):
        category = el.get("category", "text")
        content_html = el.get("content", {}).get("html", "")
        content_text = el.get("content", {}).get("text", "")

        # 표(table)나 제목(heading) 등 구조적 정보가 담긴 HTML을 우선 수집
        if content_html:
            full_content.append(f"<{category}>\n{content_html}\n</{category}>")
        elif content_text:
            full_content.append(content_text)

    return "\n\n".join(full_content)


def analyze_points_advanced(
    openai_key: str,
    context_data: str,
    user_certs: list[str],
    target_job: str = "IT 직무",
) -> dict:
    """
    공공기관 채용 공고문을 파싱하여 사용자 자격증에 대한 최적 가점을 산출합니다.

    Args:
        openai_key: OpenAI API 키
        context_data: Upstage로 추출한 공고문 텍스트 (HTML/Text 혼합)
        user_certs: 보유 자격증 목록 (예: ["정보처리기사", "OPic IH"])
        target_job: 지원 직무명 (기본값: "IT 직무")

    Returns:
        {
            "is_score_fixed": bool,
            "calculated_points": int,
            "applied_items": [...],
            "scoring_logic_guide": str,
            "total_summary": str,
        }
    """
    client = OpenAI(api_key=openai_key)
    current_date = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""
    당신은 대한민국 공공기관 채용 규정 분석 전문가입니다. 
    제공된 [공고문 데이터]의 복잡한 규칙을 해석하여 [사용자 자격증]에 대한 '최적 가점'을 산출하세요.

    [공고문 데이터 (HTML/Text 혼합)]
    {context_data}

    [지원자 정보]
    - 지원 분야: {target_job}
    - 보유 자격증: {", ".join(user_certs)}
    - 오늘 날짜: {current_date}

    [계산 필독 지침]
    1. **최우선 순위 (배타적 적용)**: 한 자격증이 '공통가점'과 '직무가점' 양쪽에 해당할 경우, 전체 합계가 가장 높게 나오도록 하나의 항목에만 배치하세요.
    2. **등급별 중복 배제**: 동일 분야(예: 정보처리)의 기사와 산업기사를 동시에 보유했다면, '최상위 등급 1개'만 인정하세요.
    3. **카테고리별 상한선**: 각 이미지(공고)별로 명시된 가점 상한선(예: 최대 40점 등)을 확인하여 최종 점수를 절삭하세요.
    4. **유효기간 검증**: 어학(OPic)이나 한국사 등 유효기간 규정이 있다면 오늘 날짜와 대조하세요. (취득일 정보가 없으면 '유효함'으로 가정하되 비고에 명시)
    5. **논리적 비판**: 공고문의 내용이 불분명하여 점수 확정이 어렵다면 반드시 그 이유를 'scoring_logic_guide'에 명시하고 나에게 추가 정보를 요청하세요.

    [출력 형식: JSON]
    {{
        "is_score_fixed": "true/false",
        "calculated_points": "합산된 최종 숫자",
        "applied_items": [
            {{ "name": "자격증명", "category": "적용분야(공통/직무/IT 등)", "status": "인정/제외", "score": "할당점수", "note": "제외되었다면 그 근거(예: 상위등급 중복 등)" }}
        ],
        "scoring_logic_guide": "점수 산출 과정에서의 논리적 판단 근거 및 주의사항",
        "total_summary": "결과 한 줄 요약"
    }}
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "너는 복잡한 조건문을 정확하게 처리하는 채용 규정 분석 엔진이야. 답변은 오직 JSON으로만 해."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)