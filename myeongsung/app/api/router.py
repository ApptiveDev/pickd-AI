"""
Resume Strategist API — 라우터 (Controller 레이어)

각 엔드포인트는 요청을 수신하고 서비스 레이어에 위임한 뒤 응답을 반환합니다.
비즈니스 로직은 services/ 하위 모듈에서 처리합니다.
"""

import json
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Response
from pydantic import ValidationError

from app.schemas.job_dto import JobPostingCreate, UrlAnalysisRequest
from app.schemas.resume_dto import (
    ExperienceExtractionResponse,
    MergeCheckRequest,
    MergeCheckResponse,
    MergeExperiencePayload,
    PlacementResponse,
    Step1ExtractionResponse,
    ExperienceSummary,
    Step2ExtractionResponse,
)

from app.api.experience_extraction_v2 import router as experience_extraction_v2_router
from app.services.resume_service import create_workflow, parse_and_validate_experiences
from app.services.job_analysis_service import analyze_job_url
from app.services.pdf_analysis_service import analyze_job_pdf
from app.services.image_analysis_service import analyze_job_image
from app.services.experience_extraction_service import (
    extract_experiences_from_text,
    extract_experiences_from_url,
    extract_experiences_from_pdf,
    extract_step1_from_text,
    extract_step1_from_url,
    extract_step1_from_pdf,
    extract_step2_from_text,
    extract_step2_from_url,
    extract_step2_from_pdf,
)
from app.services.experience_merge_service import (
    apply_merge_results_to_step2,
    check_merge_candidates,
)
from app.services.eval_service import log_evaluation


router = APIRouter()
router.include_router(experience_extraction_v2_router)
workflow = create_workflow()


# ──────────────────────────────────────────────────────────────────────────────
# 채용공고 분석 엔드포인트
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/analyze/url", response_model=JobPostingCreate)
async def analyze_url(request: UrlAnalysisRequest, response: Response, background_tasks: BackgroundTasks):
    """
    URL을 입력받아 채용공고를 멀티모달(텍스트 + 비전) 방식으로 분석합니다.
    분석 완료 후 백그라운드에서 정확도를 평가하고, 응답 헤더에 신뢰도 점수를 포함합니다.
    """
    try:
        result = analyze_job_url(request.url)

        # 신뢰도 점수 계산 후 헤더에 포함 (Spring 서버에서 확인 가능)
        confidence_score = sum([
            0.2 if result.company_name else 0.0,
            0.4 if result.sections else 0.0,
            0.2 if result.ended_at else 0.0,
            0.2 if result.citations else 0.0,
        ])
        response.headers["X-Analysis-Confidence"] = str(confidence_score)

        # 백그라운드 평가 로깅 (logs/evaluation_history.jsonl에 누적)
        background_tasks.add_task(log_evaluation, result, "Source Content Hidden", request.url)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/pdf", response_model=JobPostingCreate)
async def analyze_pdf(file: UploadFile = File(...)):
    """
    채용공고 PDF 파일을 업로드받아 Upstage Document AI로 파싱하고,
    LLM을 통해 11개 필드로 구성된 구조화된 데이터를 반환합니다.
    """
    try:
        file_content = await file.read()
        return analyze_job_pdf(file_content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/image", response_model=JobPostingCreate)
async def analyze_image(files: List[UploadFile] = File(...)):
    """
    여러 장의 채용공고 이미지(PNG, JPG 등)를 업로드받아 Gemini Flash로 통합 분석하고,
    구조화된 데이터를 반환합니다.
    """
    try:
        image_contents = [await file.read() for file in files]
        return analyze_job_image(image_contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────────────────────────
# 자소서 관련 엔드포인트
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/extract-experiences", response_model=ExperienceExtractionResponse)
async def extract_experiences(
    file: Optional[UploadFile] = File(None, description="자소서 원문 PDF 파일 (file, url, text 중 단 하나만 입력해도 됨)"),
    url: Optional[str] = Form(None, description="자소서 웹페이지 URL (file, url, text 중 단 하나만 입력해도 됨)"),
    text: Optional[str] = Form(None, description="자소서 텍스트 원문 (file, url, text 중 단 하나만 입력해도 됨)"),
):
    """
    자소서 원문(PDF, URL, 텍스트 중 하나)을 입력받아,
    내재된 경험들을 STAR 포맷으로 구조화하여 추출합니다.

    **입력 소스 필수 조건**:
    `file`, `url`, `text` 중 **단 하나만 입력해도 정상적으로 작동**하며, 최소 1개는 반드시 제공되어야 합니다.
    """
    if not file and not (url and url.strip()) and not (text and text.strip()):
        raise HTTPException(
            status_code=400,
            detail="file (업로드 파일), url, text 중 최소 하나는 제공되어야 합니다.",
        )

    try:
        if file and file.filename:
            file_content = await file.read()
            if file.filename.lower().endswith(".pdf"):
                return extract_experiences_from_pdf(file_content)
            return extract_experiences_from_text(file_content.decode("utf-8"))
        elif url and url.strip():
            return extract_experiences_from_url(url.strip())
        else:
            return extract_experiences_from_text(text.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-experiences/step1", response_model=Step1ExtractionResponse)
async def extract_experiences_step1(
    file: Optional[UploadFile] = File(None, description="자소서 원문 PDF 파일 (file, url, text 중 단 하나만 입력해도 됨)"),
    url: Optional[str] = Form(None, description="자소서 웹페이지 URL (file, url, text 중 단 하나만 입력해도 됨)"),
    text: Optional[str] = Form(None, description="자소서 텍스트 원문 (file, url, text 중 단 하나만 입력해도 됨)"),
):
    """
    자소서 원문을 입력받아, 1차 경험 목록(상세 서술형/스펙 증빙형 대분류 및 소분류, 경험명)만 추출합니다.

    **입력 소스 필수 조건**:
    `file`, `url`, `text` 중 **단 하나만 입력해도 정상적으로 작동**하며, 최소 1개는 반드시 제공되어야 합니다.
    """
    if not file and not (url and url.strip()) and not (text and text.strip()):
        raise HTTPException(
            status_code=400,
            detail="file (업로드 파일), url, text 중 최소 하나는 제공되어야 합니다.",
        )

    try:
        if file and file.filename:
            file_content = await file.read()
            if file.filename.lower().endswith(".pdf"):
                return extract_step1_from_pdf(file_content)
            return extract_step1_from_text(file_content.decode("utf-8"))
        elif url and url.strip():
            return extract_step1_from_url(url.strip())
        else:
            return extract_step1_from_text(text.strip())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/extract-experiences/step2", response_model=Step2ExtractionResponse)
async def extract_experiences_step2(
    file: Optional[UploadFile] = File(None, description="자소서/포트폴리오 원문 PDF 파일 (원문 중 단 하나만 입력해도 됨)"),
    url: Optional[str] = Form(None, description="자소서/포트폴리오 웹페이지 URL (원문 중 단 하나만 입력해도 됨)"),
    text: Optional[str] = Form(None, description="자소서/포트폴리오 텍스트 원문 (원문 중 단 하나만 입력해도 됨)"),
    selected_experiences: str = Form(..., description="1차 추출에서 사용자가 남긴 경험 리스트 (JSON 문자열)"),
    existing_experiences: Optional[str] = Form(None, description="현재 사용자의 저장된 경험 전체 (JSON 문자열, 병합 후보 검사 용도)"),
):
    """
    원문과 사용자가 선택한 1차 경험 목록을 받아, 각 경험의 소분류에 맞는 상세 정보(basic_info)를 추출합니다.

    **입력 소스 필수 조건**:
    `file`, `url`, `text` 중 **단 하나만 입력해도 정상적으로 작동**하며, 최소 1개는 필수로 제공되어야 합니다.
    단, `selected_experiences` 파라미터는 반드시 함께 제공되어야 합니다.
    """
    if not file and not (url and url.strip()) and not (text and text.strip()):
        raise HTTPException(
            status_code=400,
            detail="file (업로드 파일), url, text 중 최소 하나는 제공되어야 합니다.",
        )

    try:
        raw_experiences = json.loads(selected_experiences)
        from pydantic import TypeAdapter
        exp_list = TypeAdapter(List[ExperienceSummary]).validate_python(raw_experiences)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"selected_experiences JSON 파싱 오류: {str(e)}")

    existing_exp_list: List[MergeExperiencePayload] = []
    if existing_experiences and existing_experiences.strip():
        try:
            raw_existing_experiences = json.loads(existing_experiences)
            from pydantic import TypeAdapter
            existing_exp_list = TypeAdapter(List[MergeExperiencePayload]).validate_python(raw_existing_experiences)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"existing_experiences JSON 파싱 오류: {str(e)}")

    try:
        if file and file.filename:
            file_content = await file.read()
            if file.filename.lower().endswith(".pdf"):
                result = extract_step2_from_pdf(file_content, exp_list)
            else:
                result = extract_step2_from_text(file_content.decode("utf-8"), exp_list)
        elif url and url.strip():
            result = extract_step2_from_url(url.strip(), exp_list)
        else:
            result = extract_step2_from_text(text.strip(), exp_list)

        result.experiences = apply_merge_results_to_step2(result.experiences, existing_exp_list)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/experiences/merge-check", response_model=MergeCheckResponse)
async def check_experience_merge(request: MergeCheckRequest):
    """
    새 경험 후보와 사용자의 기존 경험 목록을 임베딩 유사도로 비교하여 병합 후보를 반환합니다.
    """
    try:
        return check_merge_candidates(
            targets=request.targets,
            existing_experiences=request.existing_experiences,
            threshold=request.threshold,
            top_k=request.top_k,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-and-place", response_model=PlacementResponse)
async def analyze_and_place(
    background_tasks: BackgroundTasks,
    jd_pdf: Optional[UploadFile] = File(None, description="채용공고 원문 PDF 파일 (업스테이지 파싱용)"),
    jd_url: Optional[str] = Form(None, description="채용공고 웹페이지 URL (웹 스크래핑용)"),
    experiences_json: str = Form(..., description="사용자 경험 데이터 JSON 문자열"),
    essay_prompts_json: str = Form(..., description="자소서 문항 리스트 JSON 문자열"),
    user_persona: str = Form("", description="지원자 성향/가치관. 동적 S/W 프레이밍에 사용됩니다."),
):
    """
    JD(PDF 또는 URL)와 경험 JSON, 자소서 문항 배열을 받아
    LangGraph 파이프라인을 통해 최적의 경험을 각 문항에 배치합니다.
    """
    # [유효성 검사] JD 입력 최소 하나 필수
    if not jd_pdf and not (jd_url and jd_url.strip()):
        raise HTTPException(
            status_code=400,
            detail="jd_pdf (업로드 파일) 또는 jd_url 중 최소 하나는 필수적으로 제공되어야 합니다.",
        )

    # 1. 입력 파싱 및 검증 (서비스 레이어에 위임)
    try:
        validated_experiences = parse_and_validate_experiences(experiences_json)
        raw_prompts = json.loads(essay_prompts_json)
        if not isinstance(raw_prompts, list):
            raise ValueError("essay_prompts_json 필드는 문자열 배열 형태여야 합니다.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="유효하지 않은 JSON 문자열입니다.")
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=400, detail=f"입력 데이터 검증 실패: {str(e)}")

    # 2. JD 마크다운 추출 (PDF 우선, URL 폴백)
    jd_markdown = ""
    if jd_pdf and jd_pdf.filename:
        jd_content = await jd_pdf.read()
        try:
            jd_markdown = jd_content.decode("utf-8")
        except UnicodeDecodeError:
            jd_markdown = "# JD 텍스트 파싱 처리 (더미 마크다운. 실제론 Upstage API에서 넘어왔다고 가정)"

    # 3. LangGraph 초기 State 설정
    initial_state = {
        "jd_markdown": jd_markdown,
        "jd_url": jd_url,
        "experiences": validated_experiences,
        "prompts": raw_prompts,
        "user_persona": user_persona,
        "jd_context": {},
        "placements": [],
        "remaining_indices": [],
        "errors": [],
    }

    # 4. LangGraph 워크플로우 실행
    try:
        final_state = workflow.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"내부 파이프라인 실행 중 오류 발생: {str(e)}")

    # 5. 한글 유니코드 이스케이프 방지 (ensure_ascii=False)
    final_response = PlacementResponse(
        placements=final_state.get("placements", []),
        errors=final_state.get("errors", []),
    ).model_dump()

    return Response(
        content=json.dumps(final_response, ensure_ascii=False),
        media_type="application/json",
    )
