import re
from typing import Optional

from pydantic import ConfigDict, Field, create_model

from app.schemas.resume_dto import (
    ExperiencePresetSchema,
    ExperienceSummary,
    Step2ExtractedExperience,
)


def build_dynamic_step2_model(
    selected_experience: ExperienceSummary,
    preset_schema: ExperiencePresetSchema,
):
    if preset_schema.experience_type_name != selected_experience.experience_type:
        raise ValueError("선택 경험과 프리셋의 경험 유형이 일치하지 않습니다.")
    if preset_schema.experience_group != selected_experience.experience_group:
        raise ValueError("선택 경험과 프리셋의 경험 그룹이 일치하지 않습니다.")

    basic_info_fields = {
        field.key: (
            Optional[str],
            Field(default=None, description=field.label),
        )
        for field in preset_schema.fields
    }
    safe_type_name = re.sub(r"[^0-9A-Za-z_]", "_", preset_schema.experience_type)
    basic_info_model = create_model(
        f"{safe_type_name}RuntimeBasicInfo",
        __config__=ConfigDict(extra="forbid"),
        **basic_info_fields,
    )

    experience_fields = {}
    for name, field_info in Step2ExtractedExperience.model_fields.items():
        if name == "basic_info":
            experience_fields[name] = (
                basic_info_model,
                Field(..., description="Spring PresetRegistry 기반 유형별 기본 필드"),
            )
        else:
            experience_fields[name] = (field_info.annotation, field_info)

    return create_model(
        f"{safe_type_name}RuntimeStep2Experience",
        __config__=ConfigDict(extra="forbid"),
        **experience_fields,
    )
