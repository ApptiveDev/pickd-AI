from pydantic import BaseModel, Field
from typing import List, Optional, Union, Any
from datetime import datetime

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

# ── 2차 추출 (소분류별 맞춤 스키마) ──────────────────────────────────────

# [1] 상세 서술형
class ProjectInfo(BaseModel):
    project_name: Optional[str] = Field(None, description="프로젝트명")
    period: Optional[str] = Field(None, description="진행 기간")
    role: Optional[str] = Field(None, description="역할")
    organization: Optional[str] = Field(None, description="소속/팀")
    achievements: Optional[str] = Field(None, description="주요 성과")

class ActivityInfo(BaseModel):
    activity_name: Optional[str] = Field(None, description="활동명")
    organization: Optional[str] = Field(None, description="주관기관")
    period: Optional[str] = Field(None, description="활동 기간")
    role: Optional[str] = Field(None, description="역할")
    achievements: Optional[str] = Field(None, description="주요 성과")

class InternInfo(BaseModel):
    organization: Optional[str] = Field(None, description="회사/기관명")
    department: Optional[str] = Field(None, description="직무/부서")
    period: Optional[str] = Field(None, description="근무/참여 기간")
    task: Optional[str] = Field(None, description="담당 업무")
    achievements: Optional[str] = Field(None, description="주요 성과")

class CompetitionInfo(BaseModel):
    competition_name: Optional[str] = Field(None, description="공모전명")
    organization: Optional[str] = Field(None, description="주관기관")
    period: Optional[str] = Field(None, description="참가 기간")
    role: Optional[str] = Field(None, description="역할")
    achievements: Optional[str] = Field(None, description="수상/결과")

class VolunteerInfo(BaseModel):
    activity_name: Optional[str] = Field(None, description="활동명")
    organization: Optional[str] = Field(None, description="기관/단체")
    period: Optional[str] = Field(None, description="활동 기간")
    role: Optional[str] = Field(None, description="역할")

class ExchangeInfo(BaseModel):
    location: Optional[str] = Field(None, description="국가/도시")
    organization: Optional[str] = Field(None, description="학교명")
    period: Optional[str] = Field(None, description="파견 기간")
    major: Optional[str] = Field(None, description="전공/수강 분야")

# [2] 스펙·증빙형
class LanguageInfo(BaseModel):
    exam_name: Optional[str] = Field(None, description="시험명")
    score: Optional[str] = Field(None, description="점수/등급")
    exam_date: Optional[str] = Field(None, description="응시일")
    expiration_date: Optional[str] = Field(None, description="유효기간")

class CertificateInfo(BaseModel):
    certificate_name: Optional[str] = Field(None, description="자격증명")
    organization: Optional[str] = Field(None, description="발급기관")
    acquisition_date: Optional[str] = Field(None, description="취득일")
    expiration_date: Optional[str] = Field(None, description="유효기간")

class AwardInfo(BaseModel):
    award_name: Optional[str] = Field(None, description="수상명")
    organization: Optional[str] = Field(None, description="수여기관")
    award_date: Optional[str] = Field(None, description="수상일")
    award_grade: Optional[str] = Field(None, description="수상 구분")

class CourseInfo(BaseModel):
    course_name: Optional[str] = Field(None, description="과목명")
    semester: Optional[str] = Field(None, description="이수 학기")
    credit: Optional[str] = Field(None, description="학점")
    grade: Optional[str] = Field(None, description="성적")
    major: Optional[str] = Field(None, description="관련 분야")

class EducationInfo(BaseModel):
    education_name: Optional[str] = Field(None, description="교육명")
    organization: Optional[str] = Field(None, description="운영기관")
    period: Optional[str] = Field(None, description="교육 기간")
    completion_status: Optional[str] = Field(None, description="수료 여부")

BasicInfoUnion = Union[
    ProjectInfo, ActivityInfo, InternInfo, CompetitionInfo, VolunteerInfo, ExchangeInfo,
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
    writing_status: str = Field(default="in_progress", description="작성 종료 여부")

class Step2ExtractionResponse(BaseModel):
    experiences: List[Step2ExtractedExperience] = Field(..., description="2차 추출된 경험 상세 목록")
