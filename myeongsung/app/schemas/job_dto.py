from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any

# ── 온보딩 데이터 DTO ──────────────────────────────────────
class UserBase(BaseModel):
    nickname: str = Field(..., description="닉네임")
    email: EmailStr = Field(..., description="이메일")
    region_code: str = Field(..., description="지역 (코드화)")
    
    school: str = Field(..., description="학교")
    major: str = Field(..., description="전공")
    education_status: str = Field(..., description="학력 상태")
    
    interested_job_groups: List[str] = Field(..., description="관심 직군")
    interested_industries: List[str] = Field(..., description="관심 산업")
    
    certificates: List[str] = Field(..., description="자격증 (코드 기반)")
    languages: List[str] = Field(..., description="어학 (코드 기반)")

class UserCreate(UserBase):
    id: str = Field(..., description="Google OAuth ID (PK)")

class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True

class Citation(BaseModel):
    field: str = Field(..., description="근거가 되는 필드명")
    page: int = Field(..., description="근거가 발견된 PDF 페이지 번호 (URL일 경우 0)")
    content: str = Field(..., description="근거가 된 원문 텍스트 일부")
    source_url: Optional[str] = Field(None, description="원본 위치로 이동하는 하이퍼링크 (웹일 경우 Text Fragment 포함)")
    bbox: Optional[List[float]] = Field(None, description="선택 영역 좌표 [x1, y1, x2, y2]")
    element_id: Optional[int] = Field(None, description="내부 매핑용 요소 ID")
    page_width: Optional[float] = Field(None, description="원본 페이지 너비")
    page_height: Optional[float] = Field(None, description="원본 페이지 높이")




# ── 공고 분석 데이터 DTO (계층형 통합 구조) ──────────────────

class NoticeGuidelineDTO(BaseModel):
    general_notes: Optional[str] = Field(None, description="일반 유의사항")
    duplicate_apply_restriction: Optional[str] = Field(None, description="중복 지원 제한")
    false_info_warning: Optional[str] = Field(None, description="허위 기재 경고")
    cancellation_conditions: Optional[str] = Field(None, description="합격 취소 조건")
    recruitment_cancel_possibility: Optional[str] = Field(None, description="채용 취소 가능성 안내")
    reserve_candidate_guide: Optional[str] = Field(None, description="예비 합격자 안내")
    contact_info: Optional[str] = Field(None, description="문의처")
    other_guides: Optional[str] = Field(None, description="기타 안내사항")

class NoticeCompanyInfoDTO(BaseModel):
    company_introduction: Optional[str] = Field(None, description="기업 소개")
    mission: Optional[str] = Field(None, description="미션")
    vision: Optional[str] = Field(None, description="비전")
    ideal_candidate: Optional[str] = Field(None, description="인재상")
    business_overview: Optional[str] = Field(None, description="사업 개요")
    working_conditions: Optional[str] = Field(None, description="근무 조건")
    compensation: Optional[str] = Field(None, description="급여 / 보상 체계")
    benefits: Optional[str] = Field(None, description="복리후생")

class ApplicationDocumentDTO(BaseModel):
    target_type: Optional[str] = Field(None, description="대상 구분 (예: COMMON, EXPERIENCED 등)")
    apply_method: Optional[str] = Field(None, description="지원 방법 (예: 온라인, 이메일 등)")
    apply_url_or_email: Optional[str] = Field(None, description="지원 URL 또는 이메일 주소")
    mandatory_documents: Optional[str] = Field(None, description="필수 제출 서류")
    optional_documents: Optional[str] = Field(None, description="선택 제출 서류")
    proof_documents: Optional[str] = Field(None, description="증빙 서류")
    online_form_items: Optional[str] = Field(None, description="온라인 입력 항목 (예: 자소서 문항 등)")
    attachment_guide: Optional[str] = Field(None, description="파일 첨부 안내")
    submission_format: Optional[str] = Field(None, description="제출 형식 (예: PDF, HWP 등)")
    submission_notes: Optional[str] = Field(None, description="제출 관련 유의사항")

class NoticeProcessDTO(BaseModel):
    process_name: str = Field(..., description="전형 트랙 구분명 (예: 공통 전형, 개발자 전형)")
    application_period: Optional[str] = Field(None, description="접수 기간")
    document_screen_schedule: Optional[str] = Field(None, description="서류전형 일정")
    coding_test_schedule: Optional[str] = Field(None, description="코딩테스트 일정")
    written_exam_schedule: Optional[str] = Field(None, description="필기전형 일정")
    interview_schedule: Optional[str] = Field(None, description="면접전형 일정")
    announcement_date: Optional[str] = Field(None, description="합격자 발표일")
    join_date: Optional[str] = Field(None, description="입사 예정일")
    other_schedules: Optional[str] = Field(None, description="기타 일정")
    schedule_notes: Optional[str] = Field(None, description="일정 유의사항")

class ApplicationQuestionDTO(BaseModel):
    question_type: str = Field(..., description="문항 유형 (COVER_LETTER, FREE_FORM, JOB_DESCRIPTION, ADDITIONAL)")
    question_number: Optional[int] = Field(None, description="문항 번호")
    question_content: str = Field(..., description="문항 내용")
    character_limit: Optional[str] = Field(None, description="글자 수 제한")
    question_notes: Optional[str] = Field(None, description="문항 관련 유의사항")

class SectionPreferenceDTO(BaseModel):
    general_preference: Optional[str] = Field(None, description="일반 우대사항")
    additional_points: Optional[str] = Field(None, description="가산점 부여 항목")
    veteran_preference: Optional[str] = Field(None, description="보훈 대상자 우대")
    disability_preference: Optional[str] = Field(None, description="장애인 우대")
    local_talent_preference: Optional[str] = Field(None, description="지역 인재 우대")
    certificate_preference: Optional[str] = Field(None, description="자격증 우대")
    experience_preference: Optional[str] = Field(None, description="경력 우대")
    other_preferences: Optional[str] = Field(None, description="기타 우대사항")

class SectionQualificationDTO(BaseModel):
    general_qualification: Optional[str] = Field(None, description="지원 자격 (일반)")
    mandatory_qualification: Optional[str] = Field(None, description="필수 자격")
    eligibility_requirement: Optional[str] = Field(None, description="응시 자격")
    education_requirement: Optional[str] = Field(None, description="학력 요건")
    major_requirement: Optional[str] = Field(None, description="전공 요건")
    certificate_requirement: Optional[str] = Field(None, description="자격증 요건")
    language_requirement: Optional[str] = Field(None, description="어학 요건")
    experience_requirement: Optional[str] = Field(None, description="경력 요건")
    age_requirement: Optional[str] = Field(None, description="연령 요건")
    military_requirement: Optional[str] = Field(None, description="병역 요건")
    other_requirements: Optional[str] = Field(None, description="기타 필수 조건")

class NoticeSectionDTO(BaseModel):
    section_name: str = Field(..., description="모집 부문명 (예: IT 본부, 공통 부문)")
    job_title: str = Field(..., description="직무명 (예: 백엔드 개발자)")
    sub_job_title: Optional[str] = Field(None, description="세부 직무명 (예: Java/Spring)")
    responsibilities: Optional[str] = Field(None, description="담당 업무 (핵심 요약)")
    detailed_description: Optional[str] = Field(None, description="세부 업무 설명")
    workplace: Optional[str] = Field(None, description="부문별 근무지")
    headcount: Optional[str] = Field(None, description="부문별 채용 인원")
    
    qualifications: List[SectionQualificationDTO] = Field(default_factory=list, description="지원 자격 목록")
    preferences: List[SectionPreferenceDTO] = Field(default_factory=list, description="우대사항 목록")
    questions: List[ApplicationQuestionDTO] = Field(default_factory=list, description="자소서 문항 목록")

class JobPostingBase(BaseModel):
    # 최상위 공고 정보
    company_name: str = Field(..., description="기업명")
    notice_name: str = Field(..., description="공고명")
    category: str = Field(..., description="채용 구분 (FULL_TIME, INTERN, EXPERIENTIAL_INTERN, CONTRACT, FREELANCER)")
    employment_type: Optional[str] = Field(None, description="고용 형태")
    posted_at: str = Field(..., description="공고 게시일 (YYYY-MM-DDTHH:MM:SS)")
    started_at: str = Field(..., description="접수 시작일 (YYYY-MM-DDTHH:MM:SS)")
    ended_at: Optional[str] = Field(None, description="접수 마감일 (YYYY-MM-DDTHH:MM:SS)")
    notice_url: Optional[str] = Field(None, description="지원 링크")
    headcount: Optional[int] = Field(0, description="총 채용 인원")
    region_1depth: Optional[str] = Field(None, description="근무 지역")
    workplace_address: Optional[str] = Field(None, description="상세 근무지")

    # 통합 연결 필드들 (하위 엔티티 매핑)
    sections: List[NoticeSectionDTO] = Field(default_factory=list, description="모집 부문 및 자격/우대/문항 정보 목록")
    processes: List[NoticeProcessDTO] = Field(default_factory=list, description="전형 절차 목록")
    documents: List[ApplicationDocumentDTO] = Field(default_factory=list, description="제출 서류 목록")
    company_info: Optional[NoticeCompanyInfoDTO] = Field(None, description="기업 정보")
    guideline: Optional[NoticeGuidelineDTO] = Field(None, description="유의사항")

    # 출처 정보 (NotebookLM 스타일)
    citations: List[Citation] = Field(default_factory=list, description="데이터 추출 근거 및 출처 정보")


class JobPostingCreate(JobPostingBase):
    pass

class JobPostingResponse(JobPostingBase):
    id: int

    class Config:
        from_attributes = True

class UrlAnalysisRequest(BaseModel):
    url: str = Field(..., description="분석할 채용 공고 URL")

