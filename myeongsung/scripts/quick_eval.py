"""빠른 검증용: 한국에너지공단 PDF 1건만 평가
Upstage API는 1회만 호출하여 Rate Limit 방지
"""

import os
import sys
import json
import time
import requests
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_eval import evaluate_with_llm_judge
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.job_dto import JobPostingCreate

CASE = {"name": "한국에너지공단_PDF", "type": "pdf", "path": "data/한국에너지공단.pdf"}

print(f"🧪 빠른 검증: {CASE['name']}")

with open(CASE["path"], "rb") as f:
    file_content = f.read()

# ── 1. Upstage API 1회만 호출 (원본 + 분석용 동시 사용) ──
print("[1/3] Upstage Layout Analysis 호출 중...")
api_key = os.getenv("UPSTAGE_API_KEY")
url = "https://api.upstage.ai/v1/document-ai/layout-analysis"
headers = {"Authorization": f"Bearer {api_key}"}
files = {"document": ("document.pdf", file_content, "application/pdf")}
resp = requests.post(url, headers=headers, files=files)
resp.raise_for_status()
upstage_result = resp.json()

# 원본 텍스트 조합 (평가자에게 전달할 원문)
source_parts = []
# LLM에게 전달할 포맷팅된 텍스트 (분석용)
extracted_content = []
element_map = {}
page_dimensions = {}

for pg in upstage_result.get("pages", []):
    page_dimensions[pg.get("page")] = {"width": pg.get("width"), "height": pg.get("height")}

for idx, el in enumerate(upstage_result.get("elements", [])):
    page_num = el.get("page")
    category = el.get("category", "")
    text = el.get("content", {}).get("text", "")
    html = el.get("content", {}).get("html", "")
    
    element_map[idx] = el
    prefix = f"[ID:{idx}, Page:{page_num}] " if page_num else f"[ID:{idx}] "
    
    if category == "table" and html:
        source_parts.append(f"[Table]\n{html}")
        extracted_content.append(f"\n{prefix}[Table]\n{html}\n")
    elif text:
        source_parts.append(text)
        extracted_content.append(f"{prefix}{text}")

source_text = "\n".join(source_parts)
full_content = "\n".join(extracted_content)

print(f"   원본 텍스트 길이: {len(source_text)}자 / 요소 수: {len(element_map)}개")

# ── 2. LLM 분석 (GPT-4o) ──
print("[2/3] GPT-4o 추출 중...")
llm = ChatOpenAI(model="gpt-4o", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", (
        "당신은 대한민국 최고의 채용 공고 분석 AI 전문가입니다.\n"
        "제공된 PDF 파싱 데이터(ID, Page 정보 포함)를 바탕으로 구조화된 JSON 데이터를 생성하세요.\n\n"
        "### 사고 과정(Chain-of-Thought)\n"
        "Step 1: 기업명과 공고명을 파악한다.\n"
        "Step 2: 접수 기간과 전형 일정을 정리한다.\n"
        "Step 3: 모집 부문별 직무명, 인원, 자격요건, 우대사항을 분류한다.\n"
        "Step 4: 제출 서류, 기업 정보, 유의사항을 정리한다.\n"
        "Step 5: 모든 정보의 출처(citations)를 element_id와 page로 기록한다.\n\n"
        "### 규칙\n"
        "- 문서에 없는 내용은 절대 추측 금지 (null)\n"
        "- 날짜: YYYY-MM-DDTHH:MM:SS\n"
        "- Category: FULL_TIME, INTERN, EXPERIENTIAL_INTERN, CONTRACT, FREELANCER\n"
        "- 표(Table)의 HTML을 행 단위로 정밀 분석할 것"
    )),
    ("user", "다음 PDF 데이터를 분석하여 구조화된 채용 정보를 추출해주세요:\n\n{content}")
])
chain = prompt | llm.with_structured_output(JobPostingCreate)
extraction = chain.invoke({"content": full_content}, config={"run_name": "eval-pdf-analysis"})
extraction_json = extraction.model_dump_json(indent=2)

print(f"   기업명: {extraction.company_name}")
print(f"   공고명: {extraction.notice_name}")
print(f"   부문수: {len(extraction.sections)}개")
print(f"   출처수: {len(extraction.citations)}개")

# ── 3. LLM Judge 평가 ──
print("[3/3] LLM Judge 채점 중...")
eval_result = evaluate_with_llm_judge(
    extraction_json=extraction_json,
    source_text=source_text,
    case_name=CASE["name"]
)

print(f"\n{'='*50}")
print(f"✅ 종합 점수: {eval_result.overall_score:.1%}")
print(f"   ├ 완전성: {eval_result.completeness_score:.1%}")
print(f"   ├ 정확성: {eval_result.accuracy_score:.1%}")
print(f"   ├ 구조화: {eval_result.structure_score:.1%}")
print(f"   └ 환각부재: {eval_result.hallucination_score:.1%}")
print(f"\n📝 평가 요약: {eval_result.summary}")

if eval_result.field_scores:
    print("\n📋 필드별 상세 점수:")
    for fs in eval_result.field_scores:
        bar = "█" * int(fs.score * 10) + "░" * (10 - int(fs.score * 10))
        print(f"   {fs.field_name:25s} [{bar}] {fs.score:.0%} — {fs.reason}")

if eval_result.improvements:
    print("\n💡 개선 제안:")
    for i, imp in enumerate(eval_result.improvements, 1):
        print(f"  {i}. {imp}")

# 결과 저장
os.makedirs("tests/results", exist_ok=True)
with open("tests/results/quick_eval_result.json", "w", encoding="utf-8") as f:
    f.write(eval_result.model_dump_json(indent=2))
with open("tests/results/quick_eval_extraction.json", "w", encoding="utf-8") as f:
    f.write(extraction_json)

print(f"\n💾 저장 완료: tests/results/")
