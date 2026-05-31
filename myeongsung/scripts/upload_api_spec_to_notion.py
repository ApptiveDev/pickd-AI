"""
Notion API 명세서 업로드 스크립트 v3
- Request/Response Body: 꼭 필요한 스키마만 간결하게
- /analyze/pdf, /analyze/image Response Body: 전체 스키마 직접 작성
- Notion rich_text 2000자 제한 자동 분할 처리
"""

import requests

TOKEN = "ntn_s55316652411tOvpoCZSJL4NhxrqFE55fL8noqJXyH4eqd"
DB_ID = "36b149b6-8359-81f2-bfa5-c3c743da79e2"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

OLD_PAGE_IDS = [
    "36b149b6-8359-817c-9647-f6d914a1581b",
    "36b149b6-8359-81c5-b1fb-eba5567fbd82",
    "36b149b6-8359-8185-9ab5-e14319813490",
    "36b149b6-8359-8117-8381-e5cebc383fa2",
    "36b149b6-8359-8171-abb7-e6140e116b58",
]

# ── 블록 헬퍼 ────────────────────────────────────────────────────────────

CHUNK_SIZE = 1900  # Notion rich_text 최대 2000자, 여유분 포함

def split_rich_text(content: str) -> list:
    """2000자 제한에 맞게 rich_text 배열로 분할"""
    chunks = []
    for i in range(0, len(content), CHUNK_SIZE):
        chunks.append({"type": "text", "text": {"content": content[i:i + CHUNK_SIZE]}})
    return chunks if chunks else [{"type": "text", "text": {"content": ""}}]

def heading2(text):
    return {
        "object": "block", "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]}
    }

def code_block(content, language="json"):
    return {
        "object": "block", "type": "code",
        "code": {
            "rich_text": split_rich_text(content),
            "language": language,
        }
    }

def divider():
    return {"object": "block", "type": "divider", "divider": {}}

def callout(text, emoji="💡"):
    return {
        "object": "block", "type": "callout",
        "callout": {
            "rich_text": [{"type": "text", "text": {"content": text}}],
            "icon": {"type": "emoji", "emoji": emoji}
        }
    }

def table_row(cells: list):
    return {
        "type": "table_row",
        "table_row": {
            "cells": [[{"type": "text", "text": {"content": cell}}] for cell in cells]
        }
    }

def param_table(rows: list):
    header = table_row(["파라미터", "타입", "필수 여부", "설명"])
    data_rows = [table_row(list(r)) for r in rows]
    return {
        "object": "block",
        "type": "table",
        "table": {
            "table_width": 4,
            "has_column_header": True,
            "has_row_header": False,
            "children": [header] + data_rows,
        },
    }


# ── 공통 Response Body (JobPostingCreate) ────────────────────────────────

JOB_POSTING_RESPONSE = """{
  "company_name": "string",
  "notice_name": "string",
  "category": "FULL_TIME | INTERN | EXPERIENTIAL_INTERN | CONTRACT | FREELANCER",
  "employment_type": "string | null",
  "started_at": "YYYY-MM-DDTHH:MM:SS",
  "ended_at": "YYYY-MM-DDTHH:MM:SS | null",
  "notice_url": "string | null",
  "headcount": "integer | null",
  "region_1depth": "string | null",
  "workplace_address": "string | null",
  "sections": [
    {
      "section_name": "string",
      "job_title": "string",
      "responsibilities": "string | null",
      "workplace": "string | null",
      "headcount": "string | null",
      "qualifications": [
        {
          "general_qualification": "string",
          "mandatory_qualification": "string | null"
        }
      ],
      "preferences": [
        {
          "general_preference": "string | null",
          "additional_points": "string | null",
          "veteran_preference": "string | null",
          "disability_preference": "string | null",
          "certificate_preference": "string | null"
        }
      ]
    }
  ],
  "processes": [
    {
      "process_name": "string",
      "document_screen_schedule": "string | null",
      "written_exam_schedule": "string | null",
      "interview_schedule": "string | null",
      "join_date": "string | null",
      "application_period": "string | null",
      "schedule_notes": "string | null"
    }
  ],
  "documents": [
    {
      "mandatory_documents": "string | null",
      "proof_documents": "string | null",
      "apply_method": "string | null",
      "apply_url_or_email": "string | null",
      "submission_notes": "string | null"
    }
  ],
  "citations": [
    {
      "field": "string",
      "page": "integer",
      "content": "string",
      "source_url": "string | null",
      "bbox": "[x1, y1, x2, y2] | null",
      "element_id": "integer | null",
      "page_width": "float | null",
      "page_height": "float | null"
    }
  ]
}"""


# ── API 명세 정의 ─────────────────────────────────────────────────────────

APIS = [
    {
        "endpoint": "POST /analyze/url",
        "method": "POST",
        "content_type": "application/json",
        "description": "URL을 입력받아 채용공고를 멀티모달(텍스트 + 비전) 방식으로 분석합니다. 분석 완료 후 백그라운드에서 정확도를 평가하고, 응답 헤더에 신뢰도 점수(X-Analysis-Confidence)를 포함합니다.",
        "param_note": "경로/쿼리 파라미터 없음",
        "param_rows": None,
        "request_body": '{\n  "url": "string"\n}',
        "response_body": JOB_POSTING_RESPONSE,
        "response_note": "Response Header: X-Analysis-Confidence: 0.0 ~ 1.0",
        "error_responses": (
            "500 Internal Server Error\n"
            '{ "detail": "에러 메시지" }'
        ),
    },
    {
        "endpoint": "POST /analyze/pdf",
        "method": "POST",
        "content_type": "multipart/form-data",
        "description": "채용공고 PDF 파일을 업로드받아 Upstage Document AI로 파싱하고, LLM을 통해 구조화된 채용공고 데이터를 반환합니다.",
        "param_note": None,
        "param_rows": [
            ("file", "UploadFile", "✅ 필수", "채용공고 PDF 파일"),
        ],
        "request_body": "file: UploadFile",
        "response_body": JOB_POSTING_RESPONSE,
        "response_note": None,
        "error_responses": (
            "500 Internal Server Error\n"
            '{ "detail": "에러 메시지" }'
        ),
    },
    {
        "endpoint": "POST /analyze/image",
        "method": "POST",
        "content_type": "multipart/form-data",
        "description": "여러 장의 채용공고 이미지(PNG, JPG 등)를 업로드받아 Gemini Flash로 통합 분석하고, 구조화된 채용공고 데이터를 반환합니다.",
        "param_note": None,
        "param_rows": [
            ("files", "List[UploadFile]", "✅ 필수", "채용공고 이미지 파일 목록 (PNG, JPG 등, 복수 가능)"),
        ],
        "request_body": "files: List[UploadFile]",
        "response_body": JOB_POSTING_RESPONSE,
        "response_note": None,
        "error_responses": (
            "500 Internal Server Error\n"
            '{ "detail": "에러 메시지" }'
        ),
    },
    {
        "endpoint": "POST /extract-experiences",
        "method": "POST",
        "content_type": "multipart/form-data",
        "description": "자소서 원문(PDF, URL, 텍스트 중 하나)을 입력받아, 내재된 경험들을 STAR 포맷으로 구조화하여 추출합니다.",
        "param_note": "⚠️ file / url / text 중 반드시 하나 이상 제공 필요",
        "param_rows": [
            ("file", "UploadFile", "셋 중 하나 필수", "자소서 PDF 또는 텍스트 파일"),
            ("url",  "string",     "셋 중 하나 필수", "자소서 웹페이지 URL"),
            ("text", "string",     "셋 중 하나 필수", "자소서 텍스트 원문"),
        ],
        "request_body": (
            "file: UploadFile\n"
            "url:  string\n"
            "text: string"
        ),
        "response_body": (
            '{\n'
            '  "experiences": [\n'
            '    {\n'
            '      "experience_name": "string",\n'
            '      "experience_type": "string",\n'
            '      "organization": "string | null",\n'
            '      "period": "string | null",\n'
            '      "my_role": "string",\n'
            '      "situation": "string",\n'
            '      "action": "string",\n'
            '      "result": "string",\n'
            '      "learnings": "string | null",\n'
            '      "core_competencies": ["string"],\n'
            '      "applicable_questions": ["string"],\n'
            '      "source_text": "string",\n'
            '      "status": "미확인 | 저장완료 | 삭제"\n'
            '    }\n'
            '  ]\n'
            '}'
        ),
        "response_note": None,
        "error_responses": (
            "400 Bad Request\n"
            '{ "detail": "file (업로드 파일), url, text 중 최소 하나는 제공되어야 합니다." }\n\n'
            "500 Internal Server Error\n"
            '{ "detail": "에러 메시지" }'
        ),
    },
    {
        "endpoint": "POST /analyze-and-place",
        "method": "POST",
        "content_type": "multipart/form-data",
        "description": "JD(PDF 또는 URL)와 경험 JSON, 자소서 문항 배열을 받아 LangGraph 파이프라인을 통해 SWOT 전략 기반으로 최적의 경험을 각 문항에 배치합니다.",
        "param_note": "⚠️ jd_pdf / jd_url 중 반드시 하나 이상 제공 필요",
        "param_rows": [
            ("jd_pdf",             "UploadFile",   "둘 중 하나 필수", "채용공고 PDF 파일"),
            ("jd_url",             "string",        "둘 중 하나 필수", "채용공고 웹페이지 URL"),
            ("experiences_json",   "string (JSON)", "✅ 필수",         "ExperienceInput 배열 JSON 문자열"),
            ("essay_prompts_json", "string (JSON)", "✅ 필수",         "자소서 문항 string 배열 JSON 문자열"),
            ("user_persona",       "string",        "선택",            "지원자 성향/가치관, 기본값: \"\""),
        ],
        "request_body": (
            "jd_pdf: UploadFile\n"
            "jd_url: string\n\n"
            "experiences_json: string\n"
            "[\n"
            "  {\n"
            '    "id": "string | null",\n'
            '    "title": "string",\n'
            '    "priority": "상 | 중 | 하",\n'
            '    "tags": ["string"],\n'
            '    "star": {\n'
            '      "situation": "string",\n'
            '      "task": "string",\n'
            '      "action": "string",\n'
            '      "result": "string"\n'
            "    }\n"
            "  }\n"
            "]\n\n"
            "essay_prompts_json: string\n"
            '["문항1", "문항2"]\n\n'
            "user_persona: string"
        ),
        "response_body": (
            '{\n'
            '  "placements": [\n'
            '    {\n'
            '      "essay_question": "string",\n'
            '      "matched_experience_id": "string | integer | null",\n'
            '      "matched_experience_title": "string",\n'
            '      "strategy": "SO | ST | WO | WT | N/A",\n'
            '      "jd_targeting": "string",\n'
            '      "dynamic_framing": "string",\n'
            '      "strategy_derivation": "string",\n'
            '      "writing_guide": "string"\n'
            '    }\n'
            '  ],\n'
            '  "errors": ["string"]\n'
            '}'
        ),
        "response_note": None,
        "error_responses": (
            "400 Bad Request — JD 미입력\n"
            '{ "detail": "jd_pdf 또는 jd_url 중 최소 하나는 필수입니다." }\n\n'
            "400 Bad Request — JSON 형식 오류\n"
            '{ "detail": "유효하지 않은 JSON 문자열입니다." }\n\n'
            "400 Bad Request — 데이터 검증 실패\n"
            '{ "detail": "입력 데이터 검증 실패: {상세 오류}" }\n\n'
            "500 Internal Server Error\n"
            '{ "detail": "내부 파이프라인 실행 중 오류 발생: {상세 오류}" }'
        ),
    },
]


# ── Step 1: 기존 페이지 아카이브 ──────────────────────────────────────────
def archive_old_pages():
    for pid in OLD_PAGE_IDS:
        res = requests.patch(
            f"https://api.notion.com/v1/pages/{pid}",
            headers=HEADERS,
            json={"archived": True}
        )
        status = "✅" if res.status_code == 200 else f"❌ {res.status_code}"
        print(f"  {status} archived {pid}")


# ── Step 2: 페이지 생성 ───────────────────────────────────────────────────
def build_children(api):
    children = []

    # Input Parameters
    children.append(heading2("📥 Input Parameters"))
    if api.get("param_note"):
        children.append(callout(api["param_note"], "⚠️"))
    if api.get("param_rows"):
        children.append(param_table(api["param_rows"]))
    else:
        children.append({
            "object": "block", "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": "경로/쿼리 파라미터 없음 — 모든 입력은 Request Body에 포함"}}]}
        })
    children.append(divider())

    # Request Body
    children.append(heading2("📦 Request Body"))
    children.append(code_block(api["request_body"]))
    children.append(divider())

    # Response Body
    children.append(heading2("📤 Response Body"))
    if api.get("response_note"):
        children.append(callout(api["response_note"], "ℹ️"))
    children.append(code_block(api["response_body"]))
    children.append(divider())

    # Error Responses
    children.append(heading2("⚠️ Error Responses"))
    children.append(code_block(api["error_responses"], language="plain text"))

    return children


def create_page(api):
    payload = {
        "parent": {"database_id": DB_ID},
        "properties": {
            "Endpoint":     {"title": [{"text": {"content": api["endpoint"]}}]},
            "Method":       {"select": {"name": api["method"]}},
            "Content-Type": {"select": {"name": api["content_type"]}},
            "Description":  {"rich_text": [{"text": {"content": api["description"]}}]},
        },
        "children": build_children(api),
    }
    res = requests.post("https://api.notion.com/v1/pages", headers=HEADERS, json=payload)
    data = res.json()
    if res.status_code == 200:
        print(f"  ✅ {api['endpoint']} → {data['id']}")
    else:
        print(f"  ❌ {api['endpoint']} → {data.get('message', data)}")


if __name__ == "__main__":
    print("=== Step 1: 기존 페이지 아카이브 ===")
    archive_old_pages()

    print("\n=== Step 2: 페이지 재생성 ===")
    for api in APIS:
        create_page(api)

    print("\n✅ 완료!")
