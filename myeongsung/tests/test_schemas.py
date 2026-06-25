"""
tests/test_schemas.py

Pydantic 스키마 파싱 단위 테스트.
외부 API 호출 없이 스키마 검증만 수행합니다.
"""

import pytest
from pydantic import ValidationError

from app.schemas.job_dto import JobPostingBase, NoticeSectionDTO
from app.schemas.resume_dto import (
    ExperienceSummary,
    Step2ExtractedExperience,
    ProjectInfo,
)


# ──────────────────────────────────────────────────────────────────────────────
# 작업 1: JobPostingBase.headcount 타입 검증
# ──────────────────────────────────────────────────────────────────────────────

def _base_job_posting_dict(**overrides):
    """JobPostingBase 필수 필드 포함 기본 dict."""
    data = {
        "company_name": "테스트기업",
        "notice_name": "2024 하반기 공채",
        "category": "FULL_TIME",
        "started_at": "2024-09-01T00:00:00",
    }
    data.update(overrides)
    return data


class TestHeadcountType:
    def test_headcount_string_00명_내외(self):
        data = _base_job_posting_dict(headcount="00명 내외")
        job = JobPostingBase(**data)
        assert job.headcount == "00명 내외"

    def test_headcount_string_5명(self):
        data = _base_job_posting_dict(headcount="5명")
        job = JobPostingBase(**data)
        assert job.headcount == "5명"

    def test_headcount_none(self):
        data = _base_job_posting_dict(headcount=None)
        job = JobPostingBase(**data)
        assert job.headcount is None

    def test_headcount_default_is_none(self):
        data = _base_job_posting_dict()
        job = JobPostingBase(**data)
        assert job.headcount is None

    def test_headcount_int_raises_validation_error(self):
        """Pydantic v2는 str 필드에 int를 넣으면 ValidationError를 발생시킨다 (묵시적 coercion 없음)."""
        data = _base_job_posting_dict(headcount=5)
        with pytest.raises(ValidationError):
            JobPostingBase(**data)

    def test_headcount_string_0명_이상(self):
        data = _base_job_posting_dict(headcount="0명 이상")
        job = JobPostingBase(**data)
        assert job.headcount == "0명 이상"


# ──────────────────────────────────────────────────────────────────────────────
# 작업 2: ExperienceSummary 파싱
# ──────────────────────────────────────────────────────────────────────────────

class TestExperienceSummary:
    def test_experience_group_상세_서술형(self):
        exp = ExperienceSummary(
            experience_name="캡스톤 디자인 프로젝트",
            experience_group="상세 서술형",
            experience_type="프로젝트",
        )
        assert exp.experience_group == "상세 서술형"

    def test_experience_group_스펙증빙형(self):
        exp = ExperienceSummary(
            experience_name="토익 930점",
            experience_group="스펙·증빙형",
            experience_type="어학",
        )
        assert exp.experience_group == "스펙·증빙형"

    def test_experience_type_프로젝트(self):
        exp = ExperienceSummary(
            experience_name="AI 챗봇 개발",
            experience_group="상세 서술형",
            experience_type="프로젝트",
        )
        assert exp.experience_type == "프로젝트"

    def test_experience_type_어학(self):
        exp = ExperienceSummary(
            experience_name="TOEIC 900",
            experience_group="스펙·증빙형",
            experience_type="어학",
        )
        assert exp.experience_type == "어학"

    def test_experience_type_인턴(self):
        exp = ExperienceSummary(
            experience_name="네이버 인턴십",
            experience_group="상세 서술형",
            experience_type="인턴/직무경험",
        )
        assert exp.experience_type == "인턴/직무경험"

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            ExperienceSummary(
                experience_name="missing group and type",
            )


# ──────────────────────────────────────────────────────────────────────────────
# 작업 3: Step2ExtractedExperience 파싱
# ──────────────────────────────────────────────────────────────────────────────

def _project_basic_info_dict():
    return {
        "project_name": "AI 추천 시스템",
        "period": "2023.03 - 2023.08",
        "role": "백엔드 개발",
        "organization": "부산대학교 캡스톤팀",
        "achievements": "추천 정확도 15% 향상",
    }


class TestStep2ExtractedExperience:
    def _base_step2_dict(self, **overrides):
        data = {
            "experience_name": "AI 추천 시스템 개발",
            "experience_group": "상세 서술형",
            "experience_type": "프로젝트",
            "basic_info": _project_basic_info_dict(),
        }
        data.update(overrides)
        return data

    def test_needs_merge_true_includes_merge_fields(self):
        data = self._base_step2_dict(
            needs_merge=True,
            merge_candidate_id="exp-001",
            merge_similarity=0.91,
        )
        exp = Step2ExtractedExperience(**data)
        assert exp.needs_merge is True
        assert exp.merge_candidate_id == "exp-001"
        assert exp.merge_similarity == pytest.approx(0.91)

    def test_needs_merge_false_merge_fields_default_none(self):
        data = self._base_step2_dict(needs_merge=False)
        exp = Step2ExtractedExperience(**data)
        assert exp.needs_merge is False
        assert exp.merge_candidate_id is None
        assert exp.merge_similarity is None

    def test_basic_info_project_info_parsed(self):
        """normalize_basic_info_after_validation이 dict를 반환하므로 basic_info는 dict 타입이다."""
        data = self._base_step2_dict()
        exp = Step2ExtractedExperience(**data)
        assert isinstance(exp.basic_info, dict)
        assert exp.basic_info["project_name"] == "AI 추천 시스템"
        assert exp.basic_info["role"] == "백엔드 개발"

    def test_basic_info_project_info_from_dict(self):
        """basic_info를 dict로 넘겨도 정규화 후 dict로 파싱된다."""
        data = self._base_step2_dict(
            basic_info={
                "project_name": "딥러닝 모델 최적화",
                "period": "2024.01 - 2024.06",
                "role": "ML 엔지니어",
                "organization": "연구실",
                "achievements": "추론 속도 30% 개선",
            }
        )
        exp = Step2ExtractedExperience(**data)
        assert isinstance(exp.basic_info, dict)
        assert exp.basic_info["project_name"] == "딥러닝 모델 최적화"

    def test_keywords_defaults_to_empty_list(self):
        data = self._base_step2_dict()
        exp = Step2ExtractedExperience(**data)
        assert exp.keywords == []

    def test_is_important_defaults_false(self):
        data = self._base_step2_dict()
        exp = Step2ExtractedExperience(**data)
        assert exp.is_important is False


# ──────────────────────────────────────────────────────────────────────────────
# 작업 4: JobPostingBase 전체 구조 파싱
# ──────────────────────────────────────────────────────────────────────────────

class TestJobPostingBaseFull:
    def test_full_structure_with_sections_processes_documents(self):
        data = {
            "company_name": "카카오",
            "notice_name": "2024 하반기 신입공채",
            "category": "FULL_TIME",
            "employment_type": "정규직",
            "started_at": "2024-09-01T09:00:00",
            "ended_at": "2024-09-30T23:59:59",
            "notice_url": "https://kakao.com/careers/notice/1",
            "headcount": "00명",
            "region_1depth": "경기",
            "workplace_address": "경기도 성남시 분당구",
            "sections": [
                {
                    "section_name": "개발 부문",
                    "job_title": "백엔드 개발자",
                    "responsibilities": "서버 개발 및 유지보수",
                    "workplace": "판교",
                    "headcount": "10명",
                    "qualifications": [
                        {
                            "general_qualification": "컴퓨터공학 학사 이상",
                            "mandatory_qualification": None,
                        }
                    ],
                    "preferences": [
                        {
                            "general_preference": "Python 유경험자",
                        }
                    ],
                }
            ],
            "processes": [
                {
                    "process_name": "공통 전형",
                    "document_screen_schedule": "2024-10-01",
                    "application_period": "2024-09-01 ~ 2024-09-30",
                }
            ],
            "documents": [
                {
                    "mandatory_documents": "이력서, 자소서",
                    "apply_method": "온라인",
                    "apply_url_or_email": "https://kakao.com/apply",
                }
            ],
            "citations": [],
        }
        job = JobPostingBase(**data)
        assert job.company_name == "카카오"
        assert job.headcount == "00명"
        assert len(job.sections) == 1
        assert job.sections[0].section_name == "개발 부문"
        assert job.sections[0].headcount == "10명"
        assert len(job.sections[0].qualifications) == 1
        assert len(job.processes) == 1
        assert job.processes[0].process_name == "공통 전형"
        assert len(job.documents) == 1
        assert job.documents[0].apply_method == "온라인"

    def test_sections_defaults_to_empty_list(self):
        data = _base_job_posting_dict()
        job = JobPostingBase(**data)
        assert job.sections == []
        assert job.processes == []
        assert job.documents == []
        assert job.citations == []

    def test_missing_required_company_name_raises(self):
        data = {
            "notice_name": "공채",
            "category": "FULL_TIME",
            "started_at": "2024-09-01T00:00:00",
        }
        with pytest.raises(ValidationError):
            JobPostingBase(**data)
