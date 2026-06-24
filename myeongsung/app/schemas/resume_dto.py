from datetime import datetime
from typing import List, Optional, Union, Any, Dict

from pydantic import BaseModel, ConfigDict, Field, model_validator


PRESET_FIELDS: Dict[str, List[str]] = {
    "프로젝트": ["project_name", "period", "role", "organization", "achievements"],
    "PROJECT": ["project_name", "period", "role", "organization", "achievements"],
    "대외활동": ["activity_name", "organization", "period", "role", "achievements"],
    "ACTIVITY": ["activity_name", "organization", "period", "role", "achievements"],
    "인턴/직무경험": ["organization", "department", "period", "task", "achievements"],
    "INTERN": ["organization", "department", "period", "task", "achievements"],
    "공모전": ["competition_name", "organization", "period", "role", "achievements"],
    "CONTEST": ["competition_name", "organization", "period", "role", "achievements"],
    "봉사활동": ["activity_name", "organization", "period", "role"],
    "VOLUNTEER": ["activity_name", "organization", "period", "role"],
    "교환학생": ["location", "organization", "period", "major"],
    "EXCHANGE": ["location", "organization", "period", "major"],
    "알바": ["workplace_name", "period", "work_type", "task", "key_experience"],
    "ALBA": ["workplace_name", "period", "work_type", "task", "key_experience"],
    "학부연구생": ["lab_name", "organization", "period", "research_topic", "role", "deliverables"],
    "RESEARCH": ["lab_name", "organization", "period", "research_topic", "role", "deliverables"],
    "어학": ["exam_name", "score", "exam_date", "expiration_date", "score_report"],
    "LANGUAGE": ["exam_name", "score", "exam_date", "expiration_date", "score_report"],
    "자격증": ["certificate_name", "organization", "acquisition_date", "expiration_date", "certificate_copy"],
    "LICENSE": ["certificate_name", "organization", "acquisition_date", "expiration_date", "certificate_copy"],
    "수상": ["award_name", "organization", "award_date", "award_grade", "award_proof"],
    "AWARD": ["award_name", "organization", "award_date", "award_grade", "award_proof"],
    "수강과목": ["course_name", "semester", "credit", "grade", "major"],
    "COURSE": ["course_name", "semester", "credit", "grade", "major"],
    "교육 이수": ["education_name", "organization", "period", "completion_status", "completion_certificate"],
    "EDUCATION": ["education_name", "organization", "period", "completion_status", "completion_certificate"],
}

PRESET_LABEL_ALIASES: Dict[str, Dict[str, str]] = {
    "프로젝트": {"프로젝트명": "project_name", "진행 기간": "period", "역할": "role", "소속/팀": "organization", "주요 성과": "achievements"},
    "PROJECT": {"프로젝트명": "project_name", "진행 기간": "period", "역할": "role", "소속/팀": "organization", "주요 성과": "achievements"},
    "대외활동": {"활동명": "activity_name", "주관기관": "organization", "활동 기간": "period", "역할": "role", "주요 성과": "achievements"},
    "ACTIVITY": {"활동명": "activity_name", "주관기관": "organization", "활동 기간": "period", "역할": "role", "주요 성과": "achievements"},
    "인턴/직무경험": {"회사/기관명": "organization", "직무/부서": "department", "근무/참여 기간": "period", "담당 업무": "task", "주요 성과": "achievements"},
    "INTERN": {"회사/기관명": "organization", "직무/부서": "department", "근무/참여 기간": "period", "담당 업무": "task", "주요 성과": "achievements"},
    "공모전": {"공모전명": "competition_name", "주관기관": "organization", "참가 기간": "period", "역할": "role", "수상/결과": "achievements"},
    "CONTEST": {"공모전명": "competition_name", "주관기관": "organization", "참가 기간": "period", "역할": "role", "수상/결과": "achievements"},
    "봉사활동": {"활동명": "activity_name", "기관/단체": "organization", "활동 기간": "period", "역할": "role"},
    "VOLUNTEER": {"활동명": "activity_name", "기관/단체": "organization", "활동 기간": "period", "역할": "role"},
    "교환학생": {"국가/도시": "location", "학교명": "organization", "파견 기간": "period", "전공/수강 분야": "major"},
    "EXCHANGE": {"국가/도시": "location", "학교명": "organization", "파견 기간": "period", "전공/수강 분야": "major"},
    "알바": {"근무처명": "workplace_name", "근무 기간": "period", "업무 유형": "work_type", "담당 업무": "task", "주요 경험": "key_experience"},
    "ALBA": {"근무처명": "workplace_name", "근무 기간": "period", "업무 유형": "work_type", "담당 업무": "task", "주요 경험": "key_experience"},
    "학부연구생": {"연구실명": "lab_name", "소속 기관": "organization", "참여 기간": "period", "연구 주제": "research_topic", "담당 역할": "role", "주요 결과물": "deliverables"},
    "RESEARCH": {"연구실명": "lab_name", "소속 기관": "organization", "참여 기간": "period", "연구 주제": "research_topic", "담당 역할": "role", "주요 결과물": "deliverables"},
    "어학": {"시험명": "exam_name", "점수/등급": "score", "응시일": "exam_date", "유효기간": "expiration_date", "성적표": "score_report"},
    "LANGUAGE": {"시험명": "exam_name", "점수/등급": "score", "응시일": "exam_date", "유효기간": "expiration_date", "성적표": "score_report"},
    "자격증": {"자격증명": "certificate_name", "발급기관": "organization", "취득일": "acquisition_date", "유효기간": "expiration_date", "자격증 사본": "certificate_copy"},
    "LICENSE": {"자격증명": "certificate_name", "발급기관": "organization", "취득일": "acquisition_date", "유효기간": "expiration_date", "자격증 사본": "certificate_copy"},
    "수상": {"수상명": "award_name", "수여기관": "organization", "수상일": "award_date", "수상 구분": "award_grade", "수상 증빙": "award_proof"},
    "AWARD": {"수상명": "award_name", "수여기관": "organization", "수상일": "award_date", "수상 구분": "award_grade", "수상 증빙": "award_proof"},
    "수강과목": {"과목명": "course_name", "이수 학기": "semester", "학점": "credit", "성적": "grade", "관련 분야": "major"},
    "COURSE": {"과목명": "course_name", "이수 학기": "semester", "학점": "credit", "성적": "grade", "관련 분야": "major"},
    "교육 이수": {"교육명": "education_name", "운영기관": "organization", "교육 기간": "period", "수료 여부": "completion_status", "수료증": "completion_certificate"},
    "EDUCATION": {"교육명": "education_name", "운영기관": "organization", "교육 기간": "period", "수료 여부": "completion_status", "수료증": "completion_certificate"},
}


def _clean_preset_key(value: str) -> str:
    return value.replace(" ", "").replace("_", "").strip().lower()


def normalize_basic_info(experience_type: str, basic_info: Any) -> Dict[str, Any]:
    if isinstance(basic_info, BaseModel):
        raw_info = basic_info.model_dump()
    elif isinstance(basic_info, dict):
        raw_info = basic_info
    else:
        return {}

    allowed_keys = PRESET_FIELDS.get(experience_type)
    if not allowed_keys:
        return raw_info

    alias_map = PRESET_LABEL_ALIASES.get(experience_type, {})
    cleaned_aliases = {_clean_preset_key(key): value for key, value in alias_map.items()}
    cleaned_allowed = {_clean_preset_key(key): key for key in allowed_keys}

    normalized = {}
    for raw_key, value in raw_info.items():
        key = str(raw_key)
        normalized_key = cleaned_allowed.get(_clean_preset_key(key)) or cleaned_aliases.get(_clean_preset_key(key))
        if normalized_key in allowed_keys:
            normalized[normalized_key] = value
    return normalized

# ── STAR 경험 입력 스키마 ──────────────────────────────────────
class StarContent(BaseModel):
    situation: str = Field(..., description="[S] 상황 - 어떤 배경/맥락에서 발생한 일인지")
    task: str      = Field(..., description="[T] 과제 - 내가 맡은 구체적 역할과 목표")
    action: str    = Field(..., description="[A] 행동 - 내가 취한 구체적 행동과 방법")
    result: str    = Field(..., description="[R] 결과 - 행동으로 얻은 성과 (수치 포함 권장)")

class ExperienceInput(BaseModel):
    id: Optional[str] = Field(
        None,
        description="경험 고유 ID (미입력 시 UUID 자동 생성)"
    )
    title: str    = Field(..., description="경험 제목")
    priority: str = Field(..., pattern="^(상|중|하)$", description="경험 중요도: 상/중/하")
    tags: List[str] = Field(default=[], description="기술/역량 태그 (선택, 추후 AI 자동 태깅)")
    star: StarContent = Field(..., description="STAR 형식 경험 본문")

# ── 응답 스키마 (플랫 구조) ──
class PlacementResult(BaseModel):
    essay_question:           str            = Field(..., description="자소서 문항 원문")
    matched_experience_id:    Optional[Union[str, int]] = Field(None, description="매핑된 경험 ID (문자열 혹은 숫자)")
    matched_experience_title: str            = Field(..., description="매핑된 경험 제목")
    strategy:                 str            = Field(..., description="선택된 SWOT 전략 (SO/ST/WO/WT/N/A)")
    jd_targeting:             str            = Field(..., description="[JD 타겟팅] JD에서 설정한 O/T 근거")
    dynamic_framing:          str            = Field(..., description="[동적 프레이밍] 페르소나 기반 S/W 해석")
    strategy_derivation:      str            = Field(..., description="[전략 도출] 전략 선택 최종 논증")
    writing_guide:            str            = Field(..., description="자소서 작성 가이드라인 및 핵심 키워드")

class PlacementResponse(BaseModel):
    placements: List[PlacementResult]
    errors: List[str] = []

# ── 자소서 기반 경험 추출 스키마 ──────────────────────────────────────
class ExtractedExperience(BaseModel):
    experience_name: str = Field(..., description="경험명 (예: 경식이 AI 전화 서비스 기획)")
    experience_type: str = Field(..., description="경험 유형 (예: 프로젝트, 인턴, 동아리, 창업, 해커톤 등)")
    organization: Optional[str] = Field(None, description="기관/소속")
    period: Optional[str] = Field(None, description="기간")
    my_role: str = Field(..., description="나의 역할 (Task)")
    
    # STAR + L
    situation: str = Field(..., description="[S] 문제상황")
    action: str = Field(..., description="[A] 주요 행동")
    result: str = Field(..., description="[R] 결과/성과")
    learnings: Optional[str] = Field(None, description="배운 점")
    
    core_competencies: List[str] = Field(..., description="핵심 역량 태그 (예: 문제해결, 기획력 등)")
    applicable_questions: List[str] = Field(..., description="활용 가능 문항 (예: 문제해결 경험, 도전 경험 등)")
    source_text: str = Field(..., description="원문 출처 (추출의 근거가 된 자소서 원본 일부)")
    status: str = Field(default="미확인", description="상태 (미확인, 저장완료, 삭제 등)")

class ExperienceExtractionResponse(BaseModel):
    experiences: List[ExtractedExperience] = Field(..., description="추출된 경험 후보 목록")

# ── 1차 추출 (경험 분류) 스키마 ──────────────────────────────────────
class ExperienceSummary(BaseModel):
    experience_name: str = Field(..., description="경험명 (예: 캡스톤 디자인 프로젝트, 토익 900점 등)")
    experience_group: str = Field(..., description="경험 대분류 (상세 서술형 또는 스펙·증빙형)")
    experience_type: str = Field(..., description="경험 소분류 (프로젝트, 어학, 인턴 등)")

class Step1ExtractionResponse(BaseModel):
    experiences: List[ExperienceSummary] = Field(..., description="1차 추출된 경험 목록")

class PresetFieldDefinition(BaseModel):
    key: str = Field(..., description="Spring PresetRegistry의 필드 키")
    label: str = Field(..., description="필드 한글 라벨")


class ExperiencePresetSchema(BaseModel):
    experience_group: str = Field(..., description="경험 대분류 한글명")
    experience_type: str = Field(..., description="Spring ExperienceType enum 코드")
    experience_type_name: str = Field(..., description="경험 소분류 한글명")
    fields: List[PresetFieldDefinition] = Field(
        default_factory=list,
        description="해당 경험 유형에서 허용하는 basic_info 필드",
    )

# ── 2차 추출 (소분류별 맞춤 스키마) ──────────────────────────────────────

# [1] 상세 서술형
class PresetInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectInfo(PresetInfo):
    project_name: Optional[str] = Field(None, description="프로젝트명")
    period: Optional[str] = Field(None, description="진행 기간")
    role: Optional[str] = Field(None, description="역할")
    organization: Optional[str] = Field(None, description="소속/팀")
    achievements: Optional[str] = Field(None, description="주요 성과")

class ActivityInfo(PresetInfo):
    activity_name: Optional[str] = Field(None, description="활동명")
    organization: Optional[str] = Field(None, description="주관기관")
    period: Optional[str] = Field(None, description="활동 기간")
    role: Optional[str] = Field(None, description="역할")
    achievements: Optional[str] = Field(None, description="주요 성과")

class InternInfo(PresetInfo):
    organization: Optional[str] = Field(None, description="회사/기관명")
    department: Optional[str] = Field(None, description="직무/부서")
    period: Optional[str] = Field(None, description="근무/참여 기간")
    task: Optional[str] = Field(None, description="담당 업무")
    achievements: Optional[str] = Field(None, description="주요 성과")

class CompetitionInfo(PresetInfo):
    competition_name: Optional[str] = Field(None, description="공모전명")
    organization: Optional[str] = Field(None, description="주관기관")
    period: Optional[str] = Field(None, description="참가 기간")
    role: Optional[str] = Field(None, description="역할")
    achievements: Optional[str] = Field(None, description="수상/결과")

class VolunteerInfo(PresetInfo):
    activity_name: Optional[str] = Field(None, description="활동명")
    organization: Optional[str] = Field(None, description="기관/단체")
    period: Optional[str] = Field(None, description="활동 기간")
    role: Optional[str] = Field(None, description="역할")

class ExchangeInfo(PresetInfo):
    location: Optional[str] = Field(None, description="국가/도시")
    organization: Optional[str] = Field(None, description="학교명")
    period: Optional[str] = Field(None, description="파견 기간")
    major: Optional[str] = Field(None, description="전공/수강 분야")

class AlbaInfo(PresetInfo):
    workplace_name: Optional[str] = Field(None, description="근무처명")
    period: Optional[str] = Field(None, description="근무 기간")
    work_type: Optional[str] = Field(None, description="업무 유형")
    task: Optional[str] = Field(None, description="담당 업무")
    key_experience: Optional[str] = Field(None, description="주요 경험")

class ResearchInfo(PresetInfo):
    lab_name: Optional[str] = Field(None, description="연구실명")
    organization: Optional[str] = Field(None, description="소속 기관")
    period: Optional[str] = Field(None, description="참여 기간")
    research_topic: Optional[str] = Field(None, description="연구 주제")
    role: Optional[str] = Field(None, description="담당 역할")
    deliverables: Optional[str] = Field(None, description="주요 결과물")

# [2] 스펙·증빙형
class LanguageInfo(PresetInfo):
    exam_name: Optional[str] = Field(None, description="시험명")
    score: Optional[str] = Field(None, description="점수/등급")
    exam_date: Optional[str] = Field(None, description="응시일")
    expiration_date: Optional[str] = Field(None, description="유효기간")
    score_report: Optional[str] = Field(None, description="성적표")

class CertificateInfo(PresetInfo):
    certificate_name: Optional[str] = Field(None, description="자격증명")
    organization: Optional[str] = Field(None, description="발급기관")
    acquisition_date: Optional[str] = Field(None, description="취득일")
    expiration_date: Optional[str] = Field(None, description="유효기간")
    certificate_copy: Optional[str] = Field(None, description="자격증 사본")

class AwardInfo(PresetInfo):
    award_name: Optional[str] = Field(None, description="수상명")
    organization: Optional[str] = Field(None, description="수여기관")
    award_date: Optional[str] = Field(None, description="수상일")
    award_grade: Optional[str] = Field(None, description="수상 구분")
    award_proof: Optional[str] = Field(None, description="수상 증빙")

class CourseInfo(PresetInfo):
    course_name: Optional[str] = Field(None, description="과목명")
    semester: Optional[str] = Field(None, description="이수 학기")
    credit: Optional[str] = Field(None, description="학점")
    grade: Optional[str] = Field(None, description="성적")
    major: Optional[str] = Field(None, description="관련 분야")

class EducationInfo(PresetInfo):
    education_name: Optional[str] = Field(None, description="교육명")
    organization: Optional[str] = Field(None, description="운영기관")
    period: Optional[str] = Field(None, description="교육 기간")
    completion_status: Optional[str] = Field(None, description="수료 여부")
    completion_certificate: Optional[str] = Field(None, description="수료증")

BasicInfoUnion = Union[
    ProjectInfo, ActivityInfo, InternInfo, CompetitionInfo, VolunteerInfo, ExchangeInfo, AlbaInfo, ResearchInfo,
    LanguageInfo, CertificateInfo, AwardInfo, CourseInfo, EducationInfo
]

class TaggedSentence(BaseModel):
    tag: str = Field(..., description="문장에 부여된 유일한 태그 (나의 역할, 문제 상황, 실행 과정, 성과, 수치 성과, 배운 점, 직무 연결성, 협업 방식, 일반 문장 중 1개)")
    sentence: str = Field(..., description="경험 본문의 한 줄 (문장)")

class Step2ExtractedExperience(BaseModel):
    experience_name: str = Field(..., description="경험명")
    experience_group: str = Field(..., description="경험 대분류 (상세 서술형/스펙·증빙형)")
    experience_type: str = Field(..., description="경험 소분류 (프로젝트, 인턴, 자격증 등)")
    
    keywords: List[str] = Field(default=[], description="주요 키워드")
    is_important: bool = Field(default=False, description="중요도 (별표)")
    
    progress_status: str = Field(default="현재 진행중", description="진행 여부")
    needs_merge: bool = Field(default=False, description="병합 필요 여부")
    unanswered: bool = Field(default=False, description="미답변 여부")
    has_ai_questions: bool = Field(default=False, description="AI 질문 존재 여부")
    
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    basic_info: BasicInfoUnion = Field(..., description="유형별 기본 필드")
    
    experience_content: str = Field(default="", description="경험 본문 전체 (단, 스펙·증빙형은 전체 나열이 아닌 해당 경험 내용만 추출)")
    tagged_body_text: List[TaggedSentence] = Field(default=[], description="경험 본문을 한 줄씩 저장하고 태깅한 리스트")
    document_editor_content: str = Field(default="", description="문서형 에디터 본문")
    related_links: List[str] = Field(default=[], description="관련 링크")
    attachments: List[str] = Field(default=[], description="첨부파일")
    ai_questions: Optional[List[str]] = Field(default=None, description="AI 질문 목록")
    ai_sentence_cards: List[str] = Field(default=[], description="AI 문장 카드")
    
    merge_candidate_id: Optional[str] = Field(default=None, description="병합 후보 ID")
    merge_similarity: Optional[float] = Field(default=None, description="병합 후보와의 임베딩 유사도")
    writing_status: str = Field(default="in_progress", description="작성 종료 여부")

    @model_validator(mode="before")
    @classmethod
    def normalize_basic_info_before_validation(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        experience_type = data.get("experience_type") or data.get("experienceType")
        if experience_type and "basic_info" in data:
            normalized = dict(data)
            normalized["basic_info"] = normalize_basic_info(str(experience_type), data.get("basic_info"))
            return normalized
        return data

    @model_validator(mode="after")
    def normalize_basic_info_after_validation(self):
        self.basic_info = normalize_basic_info(self.experience_type, self.basic_info)
        return self

class Step2ExtractionResponse(BaseModel):
    experiences: List[Step2ExtractedExperience] = Field(..., description="2차 추출된 경험 상세 목록")

class Step2V2ExtractionResponse(BaseModel):
    experiences: List[Dict[str, Any]] = Field(
        ...,
        description="Spring 런타임 프리셋으로 검증된 2차 추출 결과",
    )


# ── 경험 병합 후보 검사 스키마 ──────────────────────────────────────
class MergeExperiencePayload(BaseModel):
    id: Optional[str] = Field(default=None, description="저장된 경험 ID. 신규 후보는 비워둘 수 있음")
    title: Optional[str] = Field(default=None, description="경험 제목")
    experience_name: Optional[str] = Field(default=None, description="경험명")
    experience_group: Optional[str] = Field(default=None, description="경험 대분류")
    experience_type: Optional[str] = Field(default=None, description="경험 소분류")
    keywords: List[str] = Field(default=[], description="경험 키워드")
    attributes: Dict[str, Any] = Field(default={}, description="저장 경험의 속성 JSON")
    basic_info: Dict[str, Any] = Field(default={}, description="추출 경험의 유형별 기본 정보")
    document_content: Optional[str] = Field(default=None, description="저장 경험 본문")
    experience_content: Optional[str] = Field(default=None, description="추출 경험 본문")


class MergeCheckRequest(BaseModel):
    targets: List[MergeExperiencePayload] = Field(..., description="새로 저장하려는 경험 후보")
    existing_experiences: List[MergeExperiencePayload] = Field(default=[], description="현재 사용자의 저장된 경험 전체")
    threshold: Optional[float] = Field(default=None, description="병합 필요 판정 임계값")
    top_k: int = Field(default=1, ge=1, description="target별 반환 후보 수. v1은 1 사용")


class MergeCandidate(BaseModel):
    id: Optional[str] = Field(default=None, description="병합 후보 경험 ID")
    title: Optional[str] = Field(default=None, description="병합 후보 제목")
    experience_group: Optional[str] = Field(default=None, description="병합 후보 대분류")
    experience_type: Optional[str] = Field(default=None, description="병합 후보 소분류")
    similarity: float = Field(..., description="target과 후보의 코사인 유사도")


class MergeCheckResult(BaseModel):
    target_index: int = Field(..., description="요청 targets 배열 내 index")
    target_id: Optional[str] = Field(default=None, description="target ID")
    needs_merge: bool = Field(..., description="병합 필요 여부")
    merge_candidate_id: Optional[str] = Field(default=None, description="가장 유사한 병합 후보 ID")
    similarity: Optional[float] = Field(default=None, description="가장 유사한 후보와의 유사도")
    candidate: Optional[MergeCandidate] = Field(default=None, description="가장 유사한 후보 정보")


class MergeCheckResponse(BaseModel):
    results: List[MergeCheckResult] = Field(..., description="target별 병합 검사 결과")
