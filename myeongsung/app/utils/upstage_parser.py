"""
Upstage Document AI Layout Analysis API를 호출하여 PDF를 파싱하는 공통 유틸.

pdf_analysis_service.py와 pdf_langgraph_service.py에서 중복으로 사용하던
Upstage 호출 + elements 순회 로직을 이 모듈로 통합합니다.
"""

import requests
from app.core.config import UPSTAGE_API_KEY, UPSTAGE_LAYOUT_ANALYSIS_URL


def parse_pdf_with_upstage(file_content: bytes) -> tuple[str, dict, dict]:
    """
    Upstage Layout Analysis API를 호출하여 PDF 바이너리를 파싱합니다.

    Args:
        file_content: PDF 파일의 바이너리 데이터

    Returns:
        tuple:
            - full_content_text (str): LLM에 전달할 전체 텍스트 (ID·페이지 정보 포함)
            - element_map (dict): {element_index: element_dict} — citation bbox 매핑용
            - page_dimensions (dict): {page_num: {"width": ..., "height": ...}} — 좌표 정규화용

    Raises:
        ValueError: API 키 미설정 또는 API 호출 실패 시
    """
    if not UPSTAGE_API_KEY:
        raise ValueError("UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다.")

    try:
        headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
        # 한글 파일명 등으로 인한 latin-1 인코딩 에러 방지를 위해 파일명을 고정
        files = {"document": ("document.pdf", file_content, "application/pdf")}

        response = requests.post(UPSTAGE_LAYOUT_ANALYSIS_URL, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        raise ValueError(f"Upstage API 호출 중 오류가 발생했습니다: {str(e)}")

    extracted_content: list[str] = []
    element_map: dict = {}
    page_dimensions: dict = {}

    # 페이지별 원본 크기 수집 (bbox 좌표 정규화에 사용)
    for pg in result.get("pages", []):
        page_dimensions[pg.get("page")] = {
            "width": pg.get("width"),
            "height": pg.get("height"),
        }

    # elements 순회: 표(table)는 HTML 구조 보존, 나머지는 텍스트 추출
    for idx, element in enumerate(result.get("elements", [])):
        page_num = element.get("page")
        category = element.get("category")
        content_text = element.get("content", {}).get("text", "")

        element_map[idx] = element

        # LLM이 element_id·page를 통해 citation 출처를 식별할 수 있도록 prefix 추가
        prefix = f"[ID:{idx}, Page:{page_num}] " if page_num else f"[ID:{idx}] "

        if category == "table":
            html = element.get("content", {}).get("html", "")
            if html:
                extracted_content.append(f"\n{prefix}[Table]\n{html}\n")
            else:
                extracted_content.append(f"\n{prefix}[Table Text]\n{content_text}\n")
        else:
            extracted_content.append(f"{prefix}{content_text}")

    full_content_text = "\n".join(extracted_content)

    if not full_content_text.strip():
        raise ValueError("PDF에서 유의미한 텍스트를 추출하지 못했습니다.")

    return full_content_text, element_map, page_dimensions


def enrich_citations_with_bbox(citations: list, element_map: dict, page_dimensions: dict) -> None:
    """
    LLM이 반환한 citations 리스트에 bbox 좌표와 페이지 이동 링크를 보완합니다.
    객체를 직접 수정(in-place)하므로 반환값이 없습니다.

    Args:
        citations: JobPostingCreate.citations (Citation 객체 리스트)
        element_map: parse_pdf_with_upstage()가 반환한 element_map
        page_dimensions: parse_pdf_with_upstage()가 반환한 page_dimensions
    """
    for citation in citations:
        # bbox 좌표 매핑
        if citation.element_id is not None and citation.element_id in element_map:
            el = element_map[citation.element_id]
            raw_coords = el.get("coordinates") or el.get("bounding_box") or []

            if raw_coords:
                xs, ys = [], []
                # 형식 1: [{"x": 1, "y": 2}, ...]
                if isinstance(raw_coords[0], dict):
                    xs = [p.get("x") for p in raw_coords if "x" in p]
                    ys = [p.get("y") for p in raw_coords if "y" in p]
                # 형식 2: [x1, y1, x2, y2, ...]
                elif isinstance(raw_coords[0], (int, float)):
                    xs = [v for i, v in enumerate(raw_coords) if i % 2 == 0]
                    ys = [v for i, v in enumerate(raw_coords) if i % 2 != 0]

                if xs and ys:
                    dim = page_dimensions.get(citation.page)
                    if dim and dim["width"] > 0 and dim["height"] > 0:
                        citation.bbox = [
                            float(min(xs)) / dim["width"],
                            float(min(ys)) / dim["height"],
                            float(max(xs)) / dim["width"],
                            float(max(ys)) / dim["height"],
                        ]
                        citation.page_width = dim["width"]
                        citation.page_height = dim["height"]
                    else:
                        citation.bbox = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]

        # 페이지 이동 링크
        if citation.page > 0:
            citation.source_url = f"#page={citation.page}"
