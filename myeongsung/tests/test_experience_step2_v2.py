import unittest

from pydantic import ValidationError

from app.schemas.resume_dto import ExperiencePresetSchema, ExperienceSummary
from app.services.experience_preset_service import build_dynamic_step2_model


class ExperienceStep2V2Test(unittest.TestCase):

    def test_dynamic_model_allows_only_runtime_preset_fields(self):
        selected = ExperienceSummary(
            experience_name="캡스톤 프로젝트",
            experience_group="상세 서술형",
            experience_type="프로젝트",
        )
        preset = ExperiencePresetSchema(
            experience_group="상세 서술형",
            experience_type="PROJECT",
            experience_type_name="프로젝트",
            fields=[
                {"key": "project_name", "label": "프로젝트명"},
                {"key": "period", "label": "진행 기간"},
            ],
        )
        model = build_dynamic_step2_model(selected, preset)

        parsed = model.model_validate({
            "experience_name": "캡스톤 프로젝트",
            "experience_group": "상세 서술형",
            "experience_type": "프로젝트",
            "basic_info": {
                "project_name": "캡스톤 프로젝트",
                "period": "2026.01 ~ 2026.06",
            },
        })

        self.assertEqual("캡스톤 프로젝트", parsed.basic_info.project_name)
        with self.assertRaises(ValidationError):
            model.model_validate({
                "experience_name": "캡스톤 프로젝트",
                "experience_group": "상세 서술형",
                "experience_type": "프로젝트",
                "basic_info": {
                    "project_name": "캡스톤 프로젝트",
                    "unknown_field": "허용되지 않음",
                },
            })

    def test_dynamic_model_rejects_mismatched_group(self):
        selected = ExperienceSummary(
            experience_name="토익",
            experience_group="스펙·증빙형",
            experience_type="어학",
        )
        preset = ExperiencePresetSchema(
            experience_group="상세 서술형",
            experience_type="LANGUAGE",
            experience_type_name="어학",
            fields=[],
        )

        with self.assertRaises(ValueError):
            build_dynamic_step2_model(selected, preset)


if __name__ == "__main__":
    unittest.main()
