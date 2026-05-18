#!/bin/bash

# 테스트용 데이터
JD_URL="https://www.wanted.co.kr/wd/208424"
USER_PERSONA="기존에 하던 것을 끈기 있게 계속 이어가며 마무리하는 책임감 있는 스타일."
EXPERIENCES='[{"id":"1","title":"미래에셋 AI Agent 개발","priority":"상","tags":["AI","RAG"],"star":{"situation":"금융 은어 검색 품질이 낮은 문제 발생","task":"은어를 공식 종목명으로 변환하는 파이프라인 구축","action":"HyperCLOVA X Reranker 및 앙상블 Retriever 도입","result":"금융 용어 변환 성공 및 검색 품질 개선"}}]'
PROMPTS='["지원 직무와 관련하여 기술적 문제 해결 과정을 서술해 주세요."]'

echo "[*] AI 서버로 분석 요청을 보냅니다 (1~2분 소요)..."

# 모든 옵션을 한 줄로 연결하여 실행
curl -s -X POST "http://127.0.0.1:8000/analyze-and-place" -F "jd_url=$JD_URL" -F "user_persona=$USER_PERSONA" -F "experiences_json=$EXPERIENCES" -F "essay_prompts_json=$PROMPTS"