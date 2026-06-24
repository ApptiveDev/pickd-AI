import json
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import TypeAdapter

from app.schemas.resume_dto import (
    ExperiencePresetSchema,
    ExperienceSummary,
    MergeExperiencePayload,
    Step2V2ExtractionResponse,
)


router = APIRouter()


def extract_step2_v2_from_text(text, selected_experiences, preset_schemas):
    from app.services.experience_extraction_service import (
        extract_step2_v2_from_text as implementation,
    )

    return implementation(text, selected_experiences, preset_schemas)


def extract_step2_v2_from_url(url, selected_experiences, preset_schemas):
    from app.services.experience_extraction_service import (
        extract_step2_v2_from_url as implementation,
    )

    return implementation(url, selected_experiences, preset_schemas)


def extract_step2_v2_from_pdf(file_content, selected_experiences, preset_schemas):
    from app.services.experience_extraction_service import (
        extract_step2_v2_from_pdf as implementation,
    )

    return implementation(file_content, selected_experiences, preset_schemas)


def apply_sequential_merge_results_to_step2(experiences, existing_experiences):
    from app.services.experience_merge_service import (
        apply_sequential_merge_results_to_step2 as implementation,
    )

    return implementation(experiences, existing_experiences)


@router.post(
    "/extract-experiences/step2-v2",
    response_model=Step2V2ExtractionResponse,
)
async def extract_experiences_step2_v2(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    selected_experiences: str = Form(...),
    existing_experiences: str = Form("[]"),
    preset_schemas: str = Form(...),
):
    if not file and not (url and url.strip()) and not (text and text.strip()):
        raise HTTPException(
            status_code=400,
            detail="file (업로드 파일), url, text 중 최소 하나는 제공되어야 합니다.",
        )

    try:
        selected_list = TypeAdapter(List[ExperienceSummary]).validate_python(
            json.loads(selected_experiences)
        )
        existing_list = TypeAdapter(List[MergeExperiencePayload]).validate_python(
            json.loads(existing_experiences)
        )
        preset_list = TypeAdapter(List[ExperiencePresetSchema]).validate_python(
            json.loads(preset_schemas)
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Step2 V2 요청 JSON 파싱 오류: {str(e)}",
        ) from e

    try:
        if file and file.filename:
            file_content = await file.read()
            if file.filename.lower().endswith(".pdf"):
                result = extract_step2_v2_from_pdf(
                    file_content,
                    selected_list,
                    preset_list,
                )
            else:
                result = extract_step2_v2_from_text(
                    file_content.decode("utf-8"),
                    selected_list,
                    preset_list,
                )
        elif url and url.strip():
            result = extract_step2_v2_from_url(
                url.strip(),
                selected_list,
                preset_list,
            )
        else:
            result = extract_step2_v2_from_text(
                text.strip(),
                selected_list,
                preset_list,
            )

        result.experiences = apply_sequential_merge_results_to_step2(
            result.experiences,
            existing_list,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
