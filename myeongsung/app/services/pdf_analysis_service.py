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
            "### 💎 초정밀 추출 원칙 (최고 정확도 모드)\n"
            "2. **데이터 무결성**: 정보가 절대적으로 없으면 null로 두되, 유추 가능한 문맥이 있다면 이를 활용하세요.\n"
            "3. **날짜 표준화 (중요)**: 모든 날짜는 반드시 **'YYYY-MM-DDTHH:MM:SS' (ISO 8601)** 형식을 따르세요. 시간 정보가 없다면 '00:00:00' 또는 '23:59:59'(마감일의 경우)로 채우세요. DB 필터링에 즉시 사용 가능한 형식이어야 합니다.\n"
            "4. **표(Table) 행 단위 완전 탐색**: [Table] 태그 내 HTML을 분석할 때, **각 행(Row)을 하나의 독립된 모집 부문(section)**으로 간주하세요.\n"
            "4. **계층적 정확성**: '모집 부문(sections)' → '자격요건(qualifications)' → '우대사항(preferences)' 관계를 1:N으로 정확히 매핑하세요.\n"
            "5. **데이터 무결성**: 정보가 절대적으로 없으면 null로 두되, 유추 가능한 문맥이 있다면(예: 표의 상단 제목이 자격요건인 경우) 이를 활용하세요.\n\n"
            "### ⚠️ 필수 추출 체크리스트\n"
            "- **전형 절차(processes)**: 일정(시작/종료 시각 포함)을 정확히 기입.\n"
            "- **제출 서류(documents)**: 지원 시점/필기 시점/면접 시점별 제출 서류를 구분하여 기입.\n"
            "- **직무 상세(responsibilities)**: 단순히 직무명만 적지 말고, 본문에 있는 업무 내용을 요약하여 반드시 포함.\n\n"
            "### 🧠 사고 과정(CoT) — 초정밀 모드\n"
            "Step 1: 기업명과 공고의 대주제(신입/경력/인턴)를 확정한다.\n"
            "Step 2: 전형 일정과 공통 자격 요건을 먼저 메모한다.\n"
            "Step 3: 모집 부문 표를 한 줄씩(Row by Row) 읽으며, 각 행을 개별 section으로 생성한다.\n"
            "Step 4: 각 section에 Step 2에서 메모한 공통 요건을 결합(Merge)한다.\n"
            "Step 5: 제출 서류와 유의사항을 빠짐없이 매핑한다.\n"
            "Step 6: 모든 필드에 대해 element_id와 page 번호로 출처를 증명한다."
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


