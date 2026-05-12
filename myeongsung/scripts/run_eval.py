"""
Pickd AI — 채용 공고 추출 정확도 자동 평가 시스템 (LLM-as-a-Judge)

평가 방식:
1. 원본 소스(PDF/URL)를 분석하여 추출 결과를 생성
2. LLM 평가자(Judge)가 추출 결과의 품질을 다각도로 채점
3. 결과 리포트를 JSON + 콘솔로 출력

평가 지표:
- Completeness (완전성): 공고에 있는 정보를 빠짐없이 추출했는가?
- Accuracy (정확성): 추출된 정보가 원문과 정확히 일치하는가?
- Structure (구조화): 계층 관계(부문→자격→우대)가 올바르게 매핑되었는가?
- Hallucination (환각): 원문에 없는 내용을 지어낸 것은 없는가?
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


# ──────────────────────────────────────────────
# 1. 평가 데이터 모델
# ──────────────────────────────────────────────

class FieldScore(BaseModel):
    """개별 필드에 대한 평가 점수"""
    field_name: str = Field(..., description="평가 대상 필드명")
    score: float = Field(..., description="점수 (0.0 ~ 1.0)")
    reason: str = Field(..., description="채점 근거")

class EvalResult(BaseModel):
    """단일 테스트 케이스에 대한 평가 결과"""
    case_name: str = Field(..., description="테스트 케이스 이름")
    source_type: str = Field(..., description="소스 유형 (pdf / url)")
    
    completeness_score: float = Field(..., description="완전성 점수 (0.0~1.0)")
    accuracy_score: float = Field(..., description="정확성 점수 (0.0~1.0)")
    structure_score: float = Field(..., description="구조화 점수 (0.0~1.0)")
    hallucination_score: float = Field(..., description="환각 점수 (1.0=환각없음, 0.0=환각심각)")
    
    overall_score: float = Field(..., description="종합 점수 (가중 평균)")
    field_scores: List[FieldScore] = Field(default_factory=list, description="필드별 상세 점수")
    summary: str = Field(..., description="평가 요약")
    improvements: List[str] = Field(default_factory=list, description="개선 제안")

class EvalReport(BaseModel):
    """전체 평가 리포트"""
    timestamp: str
    total_cases: int
    avg_overall_score: float
    avg_completeness: float
    avg_accuracy: float
    avg_structure: float
    avg_hallucination: float
    results: List[EvalResult]


# ──────────────────────────────────────────────
# 2. 테스트 데이터셋 정의
# ──────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "한국전력공사_PDF",
        "type": "pdf",
        "path": "data/한국전력공사.pdf",
    },
    {
        "name": "한국도로공사_PDF",
        "type": "pdf",
        "path": "data/한국도로공사.pdf",
    },
    {
        "name": "한국에너지공단_PDF",
        "type": "pdf",
        "path": "data/한국에너지공단.pdf",
    },
    {
        "name": "사람인_URL",
        "type": "url",
        "path": "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53645367&view_type=list&t_ref=main&t_ref_content=major_company&t_category=relay_view#seq=1",
    },
]


# ──────────────────────────────────────────────
# 3. LLM-as-a-Judge 평가기
# ──────────────────────────────────────────────

def evaluate_with_llm_judge(extraction_json: str, source_text: str, case_name: str) -> EvalResult:
    """
    GPT-4o를 평가자(Judge)로 활용하여 추출 결과의 품질을 정량적으로 채점.
    """
    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import ChatPromptTemplate

    judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)

    judge_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 채용 공고 데이터 추출 품질을 평가하는 심사위원(Judge)입니다.\n"
            "원본 소스 텍스트와 AI가 추출한 JSON 결과를 비교하여 다음 4가지 지표를 0.0~1.0 점수로 채점하세요.\n\n"
            "### 평가 기준\n"
            "1. **completeness_score** (완전성): 원문에 있는 정보가 결과에 빠짐없이 포함되었는가?\n"
            "   - 1.0: 모든 정보가 추출됨 / 0.0: 대부분 누락\n"
            "2. **accuracy_score** (정확성): 추출된 정보의 내용(기업명, 날짜, 자격요건 등)이 원문과 정확히 일치하는가?\n"
            "   - 1.0: 모두 정확 / 0.0: 대부분 부정확\n"
            "3. **structure_score** (구조화): 계층 구조(부문→자격→우대)가 올바르게 매핑되었는가? 공통 사항과 부문별 사항이 혼동되지 않았는가?\n"
            "   - 1.0: 완벽한 구조화 / 0.0: 구조가 무너짐\n"
            "4. **hallucination_score** (환각 부재): 원문에 없는 정보를 AI가 지어낸 것은 없는가?\n"
            "   - 1.0: 환각 없음 / 0.0: 심각한 환각\n\n"
            "### 채점 지침\n"
            "- 원문에 명확히 존재하는 정보가 결과에 없으면 completeness 감점\n"
            "- 날짜, 숫자, 고유명사가 틀리면 accuracy 감점\n"
            "- 특정 부문의 자격요건이 다른 부문에 잘못 매핑되면 structure 감점\n"
            "- 원문에 없는 기업 소개나 자격 조건이 결과에 있으면 hallucination 감점\n"
            "- field_scores에는 company_name, sections, processes, documents, company_info 등 주요 필드별 점수를 기록\n"
            "- improvements에는 구체적인 개선 제안을 작성"
        )),
        ("user", (
            "[테스트 케이스: {case_name}]\n\n"
            "=== 원본 소스 텍스트 (상위 3000자) ===\n{source_text}\n\n"
            "=== AI 추출 결과 (JSON) ===\n{extraction_json}\n\n"
            "위 두 자료를 비교하여 평가 결과를 출력해주세요."
        ))
    ])

    chain = judge_prompt | judge_llm.with_structured_output(EvalResult)

    result = chain.invoke(
        {
            "case_name": case_name,
            "source_text": source_text[:3000],
            "extraction_json": extraction_json[:5000],
        },
        config={"run_name": f"judge-{case_name}"}
    )

    # overall_score 계산 (가중 평균)
    result.overall_score = round(
        result.completeness_score * 0.3 +
        result.accuracy_score * 0.3 +
        result.structure_score * 0.2 +
        result.hallucination_score * 0.2,
        3
    )

    return result


# ──────────────────────────────────────────────
# 4. 메인 평가 실행기
# ──────────────────────────────────────────────

def run_evaluation():
    from app.services.pdf_analysis_service import analyze_job_pdf
    from app.services.job_analysis_service import analyze_job_url

    print("=" * 60)
    print("🧪 Pickd AI — 추출 정확도 자동 평가 시작")
    print("=" * 60)

    results: List[EvalResult] = []
    os.makedirs("tests/results", exist_ok=True)

    for case in TEST_CASES:
        print(f"\n{'─'*40}")
        print(f"[{case['name']}] 평가 시작...")

        try:
            # ── 추출 실행 ──
            if case["type"] == "pdf":
                with open(case["path"], "rb") as f:
                    file_content = f.read()
                extraction = analyze_job_pdf(file_content)
                # 원본 텍스트도 함께 추출 (평가용)
                import requests
                api_key = os.getenv("UPSTAGE_API_KEY")
                url = "https://api.upstage.ai/v1/document-ai/layout-analysis"
                headers = {"Authorization": f"Bearer {api_key}"}
                files = {"document": ("document.pdf", file_content, "application/pdf")}
                resp = requests.post(url, headers=headers, files=files)
                elements = resp.json().get("elements", [])
                source_text = "\n".join([
                    el.get("content", {}).get("text", "") for el in elements
                ])
            else:
                extraction = analyze_job_url(case["path"])
                # URL 원본 텍스트는 Firecrawl에서 마크다운으로 가져옴
                import requests as req
                fc_key = os.getenv("FIRECRAWL_API_KEY")
                resp = req.post(
                    'https://api.firecrawl.dev/v2/scrape',
                    headers={'Authorization': f'Bearer {fc_key}', 'Content-Type': 'application/json'},
                    json={'url': case["path"], 'formats': ['markdown']},
                    timeout=30
                )
                source_text = resp.json().get("data", {}).get("markdown", "")

            # 추출 결과 저장
            extraction_json = extraction.model_dump_json(indent=2)
            result_path = f"tests/results/{case['name']}_extraction.json"
            with open(result_path, "w", encoding="utf-8") as f:
                f.write(extraction_json)

            # ── LLM Judge 평가 ──
            print(f"[{case['name']}] LLM Judge 채점 중...")
            eval_result = evaluate_with_llm_judge(
                extraction_json=extraction_json,
                source_text=source_text,
                case_name=case["name"]
            )
            results.append(eval_result)

            # 개별 결과 출력
            print(f"  ✅ 종합: {eval_result.overall_score:.1%}")
            print(f"     완전성: {eval_result.completeness_score:.1%} | "
                  f"정확성: {eval_result.accuracy_score:.1%} | "
                  f"구조화: {eval_result.structure_score:.1%} | "
                  f"환각부재: {eval_result.hallucination_score:.1%}")
            print(f"  📝 {eval_result.summary}")

        except Exception as e:
            print(f"  ❌ 평가 실패: {e}")
            results.append(EvalResult(
                case_name=case["name"],
                source_type=case["type"],
                completeness_score=0, accuracy_score=0,
                structure_score=0, hallucination_score=0,
                overall_score=0,
                summary=f"평가 중 오류 발생: {str(e)}",
            ))

    # ── 종합 리포트 생성 ──
    valid_results = [r for r in results if r.overall_score > 0]
    n = len(valid_results) or 1

    report = EvalReport(
        timestamp=datetime.now().isoformat(),
        total_cases=len(TEST_CASES),
        avg_overall_score=round(sum(r.overall_score for r in valid_results) / n, 3),
        avg_completeness=round(sum(r.completeness_score for r in valid_results) / n, 3),
        avg_accuracy=round(sum(r.accuracy_score for r in valid_results) / n, 3),
        avg_structure=round(sum(r.structure_score for r in valid_results) / n, 3),
        avg_hallucination=round(sum(r.hallucination_score for r in valid_results) / n, 3),
        results=results,
    )

    # 리포트 저장
    report_path = "tests/results/eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    # 최종 결과 출력
    print("\n" + "=" * 60)
    print("📊 종합 평가 리포트")
    print("=" * 60)
    print(f"📅 시각: {report.timestamp}")
    print(f"📋 총 케이스: {report.total_cases}")
    print(f"🏆 종합 점수: {report.avg_overall_score:.1%}")
    print(f"   ├ 완전성: {report.avg_completeness:.1%}")
    print(f"   ├ 정확성: {report.avg_accuracy:.1%}")
    print(f"   ├ 구조화: {report.avg_structure:.1%}")
    print(f"   └ 환각부재: {report.avg_hallucination:.1%}")
    print(f"\n💾 상세 리포트 저장: {report_path}")
    print("=" * 60)

    # 개선 제안 종합
    all_improvements = []
    for r in results:
        all_improvements.extend(r.improvements)
    if all_improvements:
        print("\n💡 개선 제안 종합:")
        for i, imp in enumerate(set(all_improvements), 1):
            print(f"  {i}. {imp}")


if __name__ == "__main__":
    run_evaluation()
