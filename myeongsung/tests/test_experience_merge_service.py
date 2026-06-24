from types import SimpleNamespace
import unittest

from app.schemas.resume_dto import MergeExperiencePayload, Step2ExtractedExperience
from app.services.experience_merge_service import (
    apply_sequential_merge_results_to_step2,
    build_embedding_text,
    check_merge_candidates,
)


class FakeEmbeddings:
    def create(self, model, input):
        vectors = []
        for text in input:
            if "캡스톤 AI 프로젝트" in text or "AI 프로젝트 개선" in text:
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return SimpleNamespace(data=[SimpleNamespace(embedding=vector) for vector in vectors])


class FakeOpenAI:
    embeddings = FakeEmbeddings()


class LowSimilarityEmbeddings:
    def create(self, model, input):
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[1.0, 0.0]),
                SimpleNamespace(embedding=[0.76, 0.649923]),
            ]
        )


class LowSimilarityOpenAI:
    embeddings = LowSimilarityEmbeddings()


class SameEmbeddings:
    def create(self, model, input):
        return SimpleNamespace(
            data=[
                SimpleNamespace(embedding=[1.0, 0.0])
                for _ in input
            ]
        )


class SameOpenAI:
    embeddings = SameEmbeddings()


class ExperienceMergeServiceTest(unittest.TestCase):

    def test_check_merge_candidates_marks_similar_target(self):
        targets = [
            MergeExperiencePayload(
                title="AI 프로젝트 개선",
                experience_group="상세 서술형",
                experience_type="프로젝트",
                document_content="추천 모델을 개선했습니다.",
            ),
            MergeExperiencePayload(
                title="토익 900점",
                experience_group="스펙·증빙형",
                experience_type="어학",
                document_content="토익 점수를 취득했습니다.",
            ),
        ]
        existing = [
            MergeExperiencePayload(
                id="exp-1",
                title="캡스톤 AI 프로젝트",
                experience_group="상세 서술형",
                experience_type="프로젝트",
                document_content="AI 추천 모델 프로젝트입니다.",
            )
        ]

        response = check_merge_candidates(targets, existing, threshold=0.86, embedding_client=FakeOpenAI())

        self.assertTrue(response.results[0].needs_merge)
        self.assertEqual("exp-1", response.results[0].merge_candidate_id)
        self.assertEqual(1.0, response.results[0].similarity)
        self.assertFalse(response.results[1].needs_merge)
        self.assertIsNone(response.results[1].merge_candidate_id)

    def test_build_embedding_text_supports_step2_shape(self):
        experience = Step2ExtractedExperience(
            experience_name="공모전 수상",
            experience_group="상세 서술형",
            experience_type="공모전",
            keywords=["기획력"],
            basic_info={"organization": "테스트 기관"},
            experience_content="공모전에서 서비스를 기획했습니다.",
        )

        text = build_embedding_text(experience)

        self.assertIn("공모전 수상", text)
        self.assertIn("기획력", text)
        self.assertIn("테스트 기관", text)
        self.assertIn("공모전에서 서비스를 기획했습니다.", text)

    def test_spec_embedding_text_prefers_structured_fields(self):
        experience = MergeExperiencePayload(
            title="토익 900점",
            experience_group="스펙·증빙형",
            experience_type="어학",
            basic_info={
                "exam_name": "TOEIC",
                "score": "900",
                "exam_date": "2025-03-01",
            },
            document_content="여러 스펙이 함께 적힌 긴 본문입니다.",
        )

        text = build_embedding_text(experience)

        self.assertIn("TOEIC", text)
        self.assertIn("score: 900", text)
        self.assertNotIn("여러 스펙이 함께 적힌 긴 본문입니다.", text)

    def test_spec_experiences_with_different_types_are_not_compared(self):
        target = MergeExperiencePayload(
            title="토익 900점",
            experience_group="스펙·증빙형",
            experience_type="어학",
            basic_info={"exam_name": "TOEIC", "score": "900"},
        )
        existing = MergeExperiencePayload(
            id="license-1",
            title="정보처리기사",
            experience_group="스펙·증빙형",
            experience_type="자격증",
            basic_info={"certificate_name": "정보처리기사"},
        )

        response = check_merge_candidates([target], [existing], threshold=0.86, embedding_client=FakeOpenAI())

        self.assertFalse(response.results[0].needs_merge)
        self.assertIsNone(response.results[0].similarity)

    def test_same_url_marks_merge_even_with_short_content(self):
        target = MergeExperiencePayload(
            title="FIn-agent",
            experience_group="상세 서술형",
            experience_type="프로젝트",
            experience_content="https://github.com/tomchaccom/Fin_AI_Agent",
        )
        existing = MergeExperiencePayload(
            id="exp-1",
            title="Fin-agent",
            experience_group="상세 서술형",
            experience_type="공모전",
            experience_content="프로젝트 링크: https://github.com/tomchaccom/Fin_AI_Agent",
        )

        response = check_merge_candidates([target], [existing], threshold=0.86, embedding_client=LowSimilarityOpenAI())

        self.assertTrue(response.results[0].needs_merge)
        self.assertEqual("exp-1", response.results[0].merge_candidate_id)

    def test_similar_name_and_organization_marks_merge(self):
        target = MergeExperiencePayload(
            title="FIn-agent",
            experience_group="상세 서술형",
            experience_type="프로젝트",
            basic_info={"organization": "미래에셋"},
        )
        existing = MergeExperiencePayload(
            id="exp-1",
            title="Fin agent",
            experience_group="상세 서술형",
            experience_type="공모전",
            basic_info={"organization": "미래에셋"},
        )

        response = check_merge_candidates([target], [existing], threshold=0.86, embedding_client=LowSimilarityOpenAI())

        self.assertTrue(response.results[0].needs_merge)
        self.assertEqual("exp-1", response.results[0].merge_candidate_id)

    def test_low_embedding_with_two_key_field_matches_marks_merge(self):
        target = MergeExperiencePayload(
            title="금융 AI Agent",
            experience_group="상세 서술형",
            experience_type="프로젝트",
            basic_info={"organization": "미래에셋", "period": "2025.06.28 ~ 07.31"},
        )
        existing = MergeExperiencePayload(
            id="exp-1",
            title="Fin-agent",
            experience_group="상세 서술형",
            experience_type="공모전",
            basic_info={"organization": "미래에셋", "period": "2025.06.28~07.31"},
        )

        response = check_merge_candidates([target], [existing], threshold=0.86, embedding_client=LowSimilarityOpenAI())

        self.assertTrue(response.results[0].needs_merge)
        self.assertEqual("exp-1", response.results[0].merge_candidate_id)

    def test_sequential_merge_uses_first_non_duplicate_as_batch_candidate(self):
        experiences = [
            {
                "experience_name": "캡스톤 프로젝트",
                "experience_group": "상세 서술형",
                "experience_type": "프로젝트",
                "basic_info": {"project_name": "캡스톤 프로젝트"},
                "experience_content": "추천 모델을 개발했습니다.",
            },
            {
                "experience_name": "캡스톤 프로젝트",
                "experience_group": "상세 서술형",
                "experience_type": "프로젝트",
                "basic_info": {"project_name": "캡스톤 프로젝트"},
                "experience_content": "추천 모델을 개발했습니다.",
            },
        ]

        result = apply_sequential_merge_results_to_step2(
            experiences,
            [],
            threshold=0.86,
            embedding_client=SameOpenAI(),
        )

        self.assertFalse(result[0]["needs_merge"])
        self.assertTrue(result[1]["needs_merge"])
        self.assertEqual("batch:0", result[1]["merge_candidate_id"])


if __name__ == "__main__":
    unittest.main()
