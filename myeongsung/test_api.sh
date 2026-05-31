#!/bin/bash
# =============================================================================
# Resume Strategist API — 전체 엔드포인트 검증 스크립트
# =============================================================================
# 사용법:
#   chmod +x test_api.sh
#   ./test_api.sh              # 전체 테스트
#   ./test_api.sh health       # 특정 테스트만 실행
#   ./test_api.sh url          # ex) URL 분석만
#
# 지원 테스트 ID: health / url / pdf / image / extract / place
# =============================================================================

BASE_URL="http://127.0.0.1:8000/api/v1"
PASS=0
FAIL=0

# ── 색상 출력 ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── 결과 판정 헬퍼 ─────────────────────────────────────────────────────────────
assert_status() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    local body="$4"

    if [ "$actual" -eq "$expected" ]; then
        echo -e "  ${GREEN}✅ PASS${NC} [$test_name] — HTTP $actual"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}❌ FAIL${NC} [$test_name] — 예상: HTTP $expected / 실제: HTTP $actual"
        echo -e "  ${YELLOW}   응답 미리보기:${NC} $(echo "$body" | head -c 300)"
        FAIL=$((FAIL + 1))
    fi
}

run_test() {
    local id="$1"          # 테스트 ID
    local filter="$2"      # 필터 인자 (없으면 전체 실행)
    [ -n "$filter" ] && [ "$filter" != "$id" ] && return
}

# =============================================================================
# 테스트 데이터
# =============================================================================
JD_URL="https://www.wanted.co.kr/wd/208424"

EXPERIENCES_JSON='[
  {
    "id": "exp-001",
    "title": "미래에셋 AI Agent 개발",
    "priority": "상",
    "tags": ["AI", "RAG", "LangGraph"],
    "star": {
      "situation": "금융 은어 검색 품질이 낮아 사용자 이탈이 발생하는 문제가 있었습니다.",
      "task": "금융 은어를 공식 종목명으로 자동 변환하는 검색 파이프라인을 구축해야 했습니다.",
      "action": "HyperCLOVA X Reranker 및 Sparse/Dense 앙상블 Retriever를 도입하였습니다.",
      "result": "금융 용어 변환 성공률 92% 달성 및 검색 품질 지표 30% 개선하였습니다."
    }
  }
]'

ESSAY_PROMPTS_JSON='["지원 직무와 관련하여 기술적 문제 해결 과정을 서술해 주세요."]'

USER_PERSONA="기존에 하던 것을 끈기 있게 계속 이어가며 마무리하는 책임감 있는 스타일."

COVER_LETTER_TEXT="저는 미래에셋증권 공모전에서 금융 특화 AI 에이전트를 개발한 경험이 있습니다. 당시 금융 은어 검색 품질이 낮아 사용자 이탈이 발생하는 문제를 발견하였고, HyperCLOVA X Reranker 및 앙상블 Retriever를 도입하여 검색 정확도를 92%까지 끌어올렸습니다. 이 과정에서 문제를 정의하고 데이터 기반으로 솔루션을 검증하는 역량을 키울 수 있었습니다."

FILTER="${1:-}"

echo ""
echo -e "${BOLD}${CYAN}================================================================${NC}"
echo -e "${BOLD}${CYAN}   Resume Strategist API — 전체 엔드포인트 검증${NC}"
echo -e "${BOLD}${CYAN}   BASE_URL: $BASE_URL${NC}"
echo -e "${BOLD}${CYAN}================================================================${NC}"
echo ""

# =============================================================================
# [1] GET /health — 서버 상태 확인
# =============================================================================
run_test "health" "$FILTER"
if [ $? -eq 0 ]; then
    echo -e "${BOLD}[1/6] GET /health — 서버 헬스 체크${NC}"
    RESP=$(curl -s -w "\n%{http_code}" "http://127.0.0.1:8000/health")
    STATUS=$(echo "$RESP" | tail -n1)
    BODY=$(echo "$RESP" | head -n-1)
    assert_status "health" 200 "$STATUS" "$BODY"
    echo "  응답: $BODY"
    echo ""
fi

# =============================================================================
# [2] POST /api/v1/analyze/url — URL 채용공고 분석
# =============================================================================
run_test "url" "$FILTER"
if [ $? -eq 0 ]; then
    echo -e "${BOLD}[2/6] POST /api/v1/analyze/url — URL 채용공고 분석${NC}"
    echo -e "  ${YELLOW}⚠  외부 API(Firecrawl, Gemini) 호출 포함 — 시간이 걸릴 수 있습니다${NC}"
    RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/analyze/url" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$JD_URL\"}")
    STATUS=$(echo "$RESP" | tail -n1)
    BODY=$(echo "$RESP" | head -n-1)
    assert_status "analyze/url" 200 "$STATUS" "$BODY"
    echo "  응답 미리보기: $(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"company={d.get('company_name','?')}, sections={len(d.get('sections',[]))}개\")" 2>/dev/null || echo "$BODY" | head -c 200)"
    echo ""
fi

# =============================================================================
# [3] POST /api/v1/analyze/pdf — PDF 채용공고 분석
# =============================================================================
run_test "pdf" "$FILTER"
if [ $? -eq 0 ]; then
    echo -e "${BOLD}[3/6] POST /api/v1/analyze/pdf — PDF 채용공고 분석${NC}"
    PDF_FILE=""
    for f in *.pdf 국민건강.pdf 한국거래소.pdf 한국전력공사\ 합격자소서.pdf 한전2.pdf; do
        [ -f "$f" ] && PDF_FILE="$f" && break
    done

    if [ -z "$PDF_FILE" ]; then
        echo -e "  ${YELLOW}⚠  테스트 PDF 파일이 없습니다. 현재 디렉토리에 .pdf 파일을 넣고 다시 실행하세요.${NC}"
        echo -e "  ${YELLOW}   예: cp 한국전력공사\ 합격자소서.pdf ./${NC}"
        FAIL=$((FAIL + 1))
    else
        echo -e "  사용 파일: $PDF_FILE"
        echo -e "  ${YELLOW}⚠  Upstage API + GPT-4o 호출 포함 — 30초~2분 소요될 수 있습니다${NC}"
        RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/analyze/pdf" \
            -F "file=@$PDF_FILE;type=application/pdf")
        STATUS=$(echo "$RESP" | tail -n1)
        BODY=$(echo "$RESP" | head -n-1)
        assert_status "analyze/pdf" 200 "$STATUS" "$BODY"
        echo "  응답 미리보기: $(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"company={d.get('company_name','?')}, sections={len(d.get('sections',[]))}개\")" 2>/dev/null || echo "$BODY" | head -c 200)"
    fi
    echo ""
fi

# =============================================================================
# [4] POST /api/v1/analyze/image — 이미지 채용공고 분석
# =============================================================================
run_test "image" "$FILTER"
if [ $? -eq 0 ]; then
    echo -e "${BOLD}[4/6] POST /api/v1/analyze/image — 이미지 채용공고 분석${NC}"
    IMG_FILE=""
    for f in *.png *.jpg *.jpeg; do
        [ -f "$f" ] && IMG_FILE="$f" && break
    done

    if [ -z "$IMG_FILE" ]; then
        echo -e "  ${YELLOW}⚠  테스트 이미지 파일이 없습니다. 현재 디렉토리에 PNG/JPG 파일을 넣고 다시 실행하세요.${NC}"
        FAIL=$((FAIL + 1))
    else
        echo -e "  사용 파일: $IMG_FILE"
        echo -e "  ${YELLOW}⚠  Gemini Flash API 호출 포함${NC}"
        RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/analyze/image" \
            -F "files=@$IMG_FILE")
        STATUS=$(echo "$RESP" | tail -n1)
        BODY=$(echo "$RESP" | head -n-1)
        assert_status "analyze/image" 200 "$STATUS" "$BODY"
        echo "  응답 미리보기: $(echo "$BODY" | head -c 200)"
    fi
    echo ""
fi

# =============================================================================
# [5] POST /api/v1/extract-experiences — 자소서 경험 추출 (텍스트)
# =============================================================================
run_test "extract" "$FILTER"
if [ $? -eq 0 ]; then
    echo -e "${BOLD}[5/6] POST /api/v1/extract-experiences — 자소서 경험 추출 (텍스트 입력)${NC}"
    echo -e "  ${YELLOW}⚠  GPT-4o 호출 포함${NC}"
    RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/extract-experiences" \
        -F "text=$COVER_LETTER_TEXT")
    STATUS=$(echo "$RESP" | tail -n1)
    BODY=$(echo "$RESP" | head -n-1)
    assert_status "extract-experiences (text)" 200 "$STATUS" "$BODY"
    echo "  응답 미리보기: $(echo "$BODY" | python3 -c "import sys,json; d=json.load(sys.stdin); exps=d.get('experiences',[]); print(f\"추출된 경험 {len(exps)}개: \" + ', '.join([e['experience_name'] for e in exps[:3]]))" 2>/dev/null || echo "$BODY" | head -c 300)"
    echo ""
fi

# =============================================================================
# [6] POST /api/v1/analyze-and-place — JD + 경험 → 자소서 배치 (URL 기반)
# =============================================================================
run_test "place" "$FILTER"
if [ $? -eq 0 ]; then
    echo -e "${BOLD}[6/6] POST /api/v1/analyze-and-place — JD 분석 + 경험 배치 (URL 기반)${NC}"
    echo -e "  ${YELLOW}⚠  LangGraph 파이프라인 전체 실행 — 1~3분 소요될 수 있습니다${NC}"
    RESP=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/analyze-and-place" \
        -F "jd_url=$JD_URL" \
        -F "experiences_json=$EXPERIENCES_JSON" \
        -F "essay_prompts_json=$ESSAY_PROMPTS_JSON" \
        -F "user_persona=$USER_PERSONA")
    STATUS=$(echo "$RESP" | tail -n1)
    BODY=$(echo "$RESP" | head -n-1)
    assert_status "analyze-and-place (url)" 200 "$STATUS" "$BODY"
    echo "  응답 미리보기: $(echo "$BODY" | python3 -c "
import sys, json
d = json.load(sys.stdin)
placements = d.get('placements', [])
errors = d.get('errors', [])
print(f'배치 결과 {len(placements)}개, 오류 {len(errors)}개')
for p in placements[:2]:
    print(f\"  - [{p.get('strategy','?')}] {p.get('matched_experience_title','?')} → {p.get('essay_question','?')[:30]}...\")
" 2>/dev/null || echo "$BODY" | head -c 300)"
    echo ""
fi

# =============================================================================
# [결과 요약]
# =============================================================================
TOTAL=$((PASS + FAIL))
echo -e "${BOLD}${CYAN}================================================================${NC}"
echo -e "${BOLD}  테스트 결과: ${GREEN}$PASS PASS${NC} / ${RED}$FAIL FAIL${NC} (총 $TOTAL개)${NC}"
echo -e "${BOLD}${CYAN}================================================================${NC}"
echo ""
[ $FAIL -gt 0 ] && exit 1 || exit 0