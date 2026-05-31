from types import SimpleNamespace
import unittest

from app.schemas.resume_dto import MergeExperiencePayload, Step2ExtractedExperience
from app.services.experience_merge_service import build_embedding_text, check_merge_candidates


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


if __name__ == "__main__":
    unittest.main()
