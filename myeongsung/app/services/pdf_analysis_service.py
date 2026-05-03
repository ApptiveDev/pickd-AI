import os
import requests
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.job_dto import JobPostingCreate

def analyze_job_pdf(file_content: bytes) -> JobPostingCreate:
    """
    Upstage Document Parse를 이용해 PDF에서 텍스트 및 표를 추출하고,
    LLM을 통해 구조화된 채용 공고 데이터(JobPostingCreate)로 변환합니다.
    """
    # 1. Upstage API 설정
    api_key = os.getenv("UPSTAGE_API_KEY")

    if not api_key:
        raise ValueError("UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다.")

    # 2. PDF 분석 실행 (Upstage Layout Analysis API 호출)
    try:
        url = "https://api.upstage.ai/v1/document-ai/layout-analysis"
        headers = {"Authorization": f"Bearer {api_key}"}
        # 한글 파일명 등으로 인한 latin-1 인코딩 에러 방지를 위해 파일명을 'document.pdf'로 고정
        files = {"document": ("document.pdf", file_content, "application/pdf")}
        
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
    except Exception as e:
        raise ValueError(f"Upstage API 호출 중 오류가 발생했습니다: {str(e)}")

    # 3. 추출된 텍스트 및 표 정보 정리 (페이지 정보 및 요소 ID 포함)
    extracted_content = []
    element_map = {} # ID로 요소 정보를 찾기 위한 맵
    
    # Upstage 응답에서 페이지별 원본 크기 추출
    page_dimensions = {}
    for pg in result.get("pages", []):
        page_dimensions[pg.get("page")] = {"width": pg.get("width"), "height": pg.get("height")}

    for idx, element in enumerate(result.get("elements", [])):
        page_num = element.get("page")

        category = element.get("category")
        content = element.get("content", {}).get("text", "")
        
        # 요소 정보 저장 (나중에 bbox 매핑용)
        element_map[idx] = element
        
        # 페이지 및 ID 표시 추가 (LLM이 출처를 식별할 수 있도록)
        prefix = f"[ID:{idx}, Page:{page_num}] " if page_num else f"[ID:{idx}] "
        
        if category == "table":
            html = element.get("content", {}).get("html", "")
            if html:
                extracted_content.append(f"\n{prefix}[Table]\n{html}\n")
            else:
                extracted_content.append(f"\n{prefix}[Table Text]\n{content}\n")
        else:
            extracted_content.append(f"{prefix}{content}")

    full_content = "\n".join(extracted_content)

    if not full_content.strip():
        raise ValueError("PDF에서 유의미한 텍스트를 추출하지 못했습니다.")

    # 4. OpenAI 기반 구조화 데이터 추출 (정확도를 위해 gpt-4o 사용 권장)
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 대한민국 최고의 채용 공고 분석 AI 전문가입니다.\n"
            "제공된 PDF 파싱 데이터(ID, Page 정보 포함)를 바탕으로 구조화된 JSON 데이터를 생성하세요.\n\n"
            "### 핵심 추출 원칙\n"
            "1. **계층적 정확성**: '모집 부문(sections)' → '자격요건(qualifications)' → '우대사항(preferences)' → '자소서 문항(questions)' 관계를 정확히 유지\n"
            "2. **데이터 무결성**: 문서에 없는 내용은 절대 추측 금지. 정보 부재 시 null\n"
            "3. **날짜 표준화**: YYYY-MM-DDTHH:MM:SS (시간 정보 없으면 00:00:00)\n"
            "4. **표(Table) 정밀 분석**: [Table] 태그 내의 HTML을 행(row) 단위로 분석하여 세부 직무 및 자격 요건을 각각 분리 추출\n"
            "5. **출처(Citations)**: 각 정보를 추출할 때 반드시 근거가 된 `element_id`, `page`, 원문 텍스트 일부(`content`)를 기록\n"
            "6. **가산점 구분**: 공통 가산점과 직무별 가산점이 있을 경우 preferences 내 additional_points에 명확히 분리 기재\n\n"
            "### ⚠️ 필수 추출 영역 (절대 누락 금지)\n"
            "A. **전형 절차(processes)**: '서류전형 → 필기시험 → 면접 → 최종합격' 같은 채용 단계와 각 단계별 일정을 반드시 추출하세요. "
            "'채용절차', '전형일정', '선발과정', '전형단계' 등의 키워드를 문서에서 찾으세요.\n"
            "B. **제출 서류(documents)**: '입사지원서', '자기소개서', '성적증명서', '자격증 사본' 등 지원자가 제출해야 하는 서류 목록을 반드시 추출하세요. "
            "'제출서류', '구비서류', '접수방법', '지원방법' 등의 키워드를 문서에서 찾으세요.\n"
            "C. **유의사항(guideline)**: '허위 기재 시 합격 취소', '중복 지원 불가' 등의 안내를 반드시 추출하세요.\n\n"
            "### 카테고리 분류\n"
            "- Category: FULL_TIME(정규직), INTERN(인턴), EXPERIENTIAL_INTERN(체험형인턴), CONTRACT(계약직), FREELANCER(프리랜서)\n"
            "- Question Type: COVER_LETTER, FREE_FORM, JOB_DESCRIPTION, ADDITIONAL\n\n"
            "### 사고 과정(Chain-of-Thought) — 반드시 이 순서를 따르세요\n"
            "Step 1: 문서 전체를 훑어 기업명과 공고명을 파악한다.\n"
            "Step 2: 접수 기간(started_at, ended_at)과 전형 일정(processes)을 정리한다.\n"
            "Step 3: 모집 부문(sections)을 식별하고, 각 부문별 직무명·인원·업무를 기입한다.\n"
            "Step 4: 각 부문에 해당하는 자격요건(qualifications)과 우대사항(preferences)을 매핑한다.\n"
            "Step 5: **제출 서류(documents)를 빠짐없이 정리한다** — 필수 서류와 선택 서류를 구분.\n"
            "Step 6: 기업 정보(company_info)와 유의사항(guideline)을 정리한다.\n"
            "Step 7: 모든 정보에 대해 출처(citations)를 element_id와 page 번호로 기록한다."
        )),
        ("user", "다음은 분석할 PDF 문서 데이터입니다. 위 사고 과정에 따라 구조화된 채용 정보를 추출하고 출처를 명시해주세요:\n\n{content}")
    ])
    
    chain = prompt | llm.with_structured_output(JobPostingCreate)
    
    try:
        # LangSmith에 'pdf-analysis-v2'이라는 이름으로 추적되도록 config 추가
        structured_result = chain.invoke(
            {"content": full_content},
            config={"run_name": "pdf-analysis-v2"}
        )
        
        # 5. 출처(Citations) 보완 (bbox 매핑 및 페이지 이동 링크 추가)
        if structured_result.citations:
            for citation in structured_result.citations:
                # bbox 매핑
                if citation.element_id is not None and citation.element_id in element_map:
                    el = element_map[citation.element_id]
                    
                    # Upstage 좌표 필드는 'coordinates' 또는 'bounding_box'일 수 있음
                    raw_coords = el.get("coordinates") or el.get("bounding_box") or []
                    
                    if raw_coords:
                        xs, ys = [], []
                        # 1. [{"x": 1, "y": 2}, ...] 형식인 경우
                        if isinstance(raw_coords[0], dict):
                            xs = [p.get("x") for p in raw_coords if "x" in p]
                            ys = [p.get("y") for p in raw_coords if "y" in p]
                        # 2. [x1, y1, x2, y2, ...] 단순 리스트인 경우
                        elif isinstance(raw_coords[0], (int, float)):
                            xs = [v for i, v in enumerate(raw_coords) if i % 2 == 0]
                            ys = [v for i, v in enumerate(raw_coords) if i % 2 != 0]
                        
                        if xs and ys:
                            # 페이지 원본 크기 정보 가져오기
                            dim = page_dimensions.get(citation.page)
                            if dim and dim["width"] > 0 and dim["height"] > 0:
                                # [x1, y1, x2, y2]를 0~1 사이의 비율로 정규화하여 반환
                                citation.bbox = [
                                    float(min(xs)) / dim["width"],
                                    float(min(ys)) / dim["height"],
                                    float(max(xs)) / dim["width"],
                                    float(max(ys)) / dim["height"]
                                ]
                                citation.page_width = dim["width"]
                                citation.page_height = dim["height"]
                            else:
                                # 크기 정보가 없으면 절대 좌표 유지
                                citation.bbox = [float(min(xs)), float(min(ys)), float(max(xs)), float(max(ys))]


                
                # 페이지 이동 링크
                if citation.page > 0:
                    citation.source_url = f"#page={citation.page}"

        
        return structured_result
    except Exception as e:
        raise ValueError(f"LLM 데이터 추출 중 오류가 발생했습니다: {str(e)}")


