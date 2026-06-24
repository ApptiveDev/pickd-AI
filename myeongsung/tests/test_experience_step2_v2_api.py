import json
import subprocess
import sys
import unittest
from unittest.mock import patch


def _fastapi_runtime_available() -> bool:
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                "import unicodedata, fastapi, httpx",
            ],
            check=False,
            capture_output=True,
            timeout=10,
        )
        return completed.returncode == 0
    except subprocess.TimeoutExpired:
        return False


@unittest.skipUnless(
    _fastapi_runtime_available(),
    "현재 Python 런타임에서 FastAPI 네이티브 의존성을 로드할 수 없습니다.",
)
class ExperienceStep2V2ApiTest(unittest.TestCase):

    def setUp(self):
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.api.experience_extraction_v2 import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        self.client = TestClient(app)

    def test_step2_v2_parses_spring_multipart_contract_and_returns_merge_shape(self):
        from app.schemas.resume_dto import Step2V2ExtractionResponse

        captured = {}

        def fake_extract(url, selected, presets):
            captured["url"] = url
            captured["selected"] = selected
            captured["presets"] = presets
            return Step2V2ExtractionResponse(experiences=[{
                "experience_name": "캡스톤 프로젝트",
                "experience_group": "상세 서술형",
                "experience_type": "프로젝트",
                "keywords": ["실행력"],
                "basic_info": {
                    "project_name": "캡스톤 프로젝트",
                    "period": "2026.01 ~ 2026.06",
                },
                "experience_content": "추천 모델을 개발했습니다.",
            }])

        def fake_merge(experiences, existing):
            captured["existing"] = existing
            experiences[0]["needs_merge"] = True
            experiences[0]["merge_candidate_id"] = "existing-1"
            experiences[0]["merge_similarity"] = 0.92
            return experiences

        with patch(
            "app.api.experience_extraction_v2.extract_step2_v2_from_url",
            side_effect=fake_extract,
        ), patch(
            "app.api.experience_extraction_v2.apply_sequential_merge_results_to_step2",
            side_effect=fake_merge,
        ):
            response = self.client.post(
                "/api/v1/extract-experiences/step2-v2",
                data={
                    "url": "https://cdn.example.com/resume.pdf",
                    "selected_experiences": json.dumps([{
                        "experience_name": "캡스톤 프로젝트",
                        "experience_group": "상세 서술형",
                        "experience_type": "프로젝트",
                    }], ensure_ascii=False),
                    "existing_experiences": json.dumps([{
                        "id": "existing-1",
                        "title": "기존 프로젝트",
                        "experience_group": "상세 서술형",
                        "experience_type": "프로젝트",
                    }], ensure_ascii=False),
                    "preset_schemas": json.dumps([{
                        "experience_group": "상세 서술형",
                        "experience_type": "PROJECT",
                        "experience_type_name": "프로젝트",
                        "fields": [
                            {"key": "project_name", "label": "프로젝트명"},
                            {"key": "period", "label": "진행 기간"},
                        ],
                    }], ensure_ascii=False),
                },
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(
            "https://cdn.example.com/resume.pdf",
            captured["url"],
        )
        self.assertEqual(
            "캡스톤 프로젝트",
            captured["selected"][0].experience_name,
        )
        self.assertEqual(
            "PROJECT",
            captured["presets"][0].experience_type,
        )
        self.assertEqual("existing-1", captured["existing"][0].id)
        body = response.json()["experiences"][0]
        self.assertTrue(body["needs_merge"])
        self.assertEqual("existing-1", body["merge_candidate_id"])
        self.assertEqual(0.92, body["merge_similarity"])
        self.assertEqual(
            "캡스톤 프로젝트",
            body["basic_info"]["project_name"],
        )

    def test_step2_v2_rejects_invalid_preset_json(self):
        response = self.client.post(
            "/api/v1/extract-experiences/step2-v2",
            data={
                "url": "https://cdn.example.com/resume.pdf",
                "selected_experiences": "[]",
                "existing_experiences": "[]",
                "preset_schemas": "{invalid-json",
            },
        )

        self.assertEqual(400, response.status_code)
        self.assertIn(
            "Step2 V2 요청 JSON 파싱 오류",
            response.json()["detail"],
        )

    def test_step2_v2_returns_400_when_selected_experience_and_preset_mismatch(self):
        from app.services.experience_preset_service import (
            build_dynamic_step2_model,
        )

        def mismatched_extract(url, selected, presets):
            build_dynamic_step2_model(selected[0], presets[0])

        with patch(
            "app.api.experience_extraction_v2.extract_step2_v2_from_url",
            side_effect=mismatched_extract,
        ):
            response = self.client.post(
                "/api/v1/extract-experiences/step2-v2",
                data={
                    "url": "https://cdn.example.com/resume.pdf",
                    "selected_experiences": json.dumps([{
                        "experience_name": "토익",
                        "experience_group": "스펙·증빙형",
                        "experience_type": "어학",
                    }], ensure_ascii=False),
                    "existing_experiences": "[]",
                    "preset_schemas": json.dumps([{
                        "experience_group": "상세 서술형",
                        "experience_type": "LANGUAGE",
                        "experience_type_name": "어학",
                        "fields": [],
                    }], ensure_ascii=False),
                },
            )

        self.assertEqual(400, response.status_code)
        self.assertEqual(
            "선택 경험과 프리셋의 경험 그룹이 일치하지 않습니다.",
            response.json()["detail"],
        )


if __name__ == "__main__":
    unittest.main()
