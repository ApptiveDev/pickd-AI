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

class ApplicationDocumentDTO(BaseModel):
    mandatory_documents: Optional[str] = Field(None, description="필수 제출 서류")
    proof_documents: Optional[str] = Field(None, description="증빙 서류")
    apply_method: Optional[str] = Field(None, description="지원 방법 (예: 온라인, 이메일 등)")
    apply_url_or_email: Optional[str] = Field(None, description="지원 URL 또는 이메일 주소")
    submission_notes: Optional[str] = Field(None, description="제출 관련 유의사항")

class NoticeProcessDTO(BaseModel):
    process_name: str = Field(..., description="전형 단계명 (예: 공통 전형, 개발자 전형)")
    document_screen_schedule: Optional[str] = Field(None, description="서류전형 일정")
    written_exam_schedule: Optional[str] = Field(None, description="필기전형 일정")
    interview_schedule: Optional[str] = Field(None, description="면접전형 일정")
    join_date: Optional[str] = Field(None, description="입사 예정일")
    application_period: Optional[str] = Field(None, description="접수 기간")
    schedule_notes: Optional[str] = Field(None, description="일정 유의사항")

class SectionPreferenceDTO(BaseModel):
    general_preference: Optional[str] = Field(None, description="우대사항")
    additional_points: Optional[str] = Field(None, description="가점사항")
    veteran_preference: Optional[str] = Field(None, description="취업지원대상 우대")
    disability_preference: Optional[str] = Field(None, description="장애인 우대")
    certificate_preference: Optional[str] = Field(None, description="자격증 가점")

class SectionQualificationDTO(BaseModel):
    general_qualification: str = Field(..., description="지원 자격 (일반)")
    mandatory_qualification: Optional[str] = Field(None, description="필수 자격")

class NoticeSectionDTO(BaseModel):
    section_name: str = Field(..., description="모집 부문명 (예: IT 본부, 공통 부문)")
    job_title: str = Field(..., description="직무명 (예: 백엔드 개발자)")
    responsibilities: Optional[str] = Field(None, description="담당 업무 (핵심 요약 및 상세 설명 통합)")
    workplace: Optional[str] = Field(None, description="부문별 근무지")
    headcount: Optional[str] = Field(None, description="부문별 채용 인원")
    
    qualifications: List[SectionQualificationDTO] = Field(default_factory=list, description="지원 자격 목록")
    preferences: List[SectionPreferenceDTO] = Field(default_factory=list, description="우대사항 목록")

class JobPostingBase(BaseModel):
    # 최상위 공고 정보
    company_name: str = Field(..., description="기업명")
    notice_name: str = Field(..., description="공고명")
    category: str = Field(..., description="채용 구분 (FULL_TIME, INTERN, EXPERIENTIAL_INTERN, CONTRACT, FREELANCER)")
    employment_type: Optional[str] = Field(None, description="고용 형태")
    started_at: str = Field(..., description="접수 시작일 (YYYY-MM-DDTHH:MM:SS)")
    ended_at: Optional[str] = Field(None, description="접수 마감일 (YYYY-MM-DDTHH:MM:SS)")
    notice_url: Optional[str] = Field(None, description="지원 링크")
    headcount: Optional[int] = Field(0, description="채용 인원")
    region_1depth: Optional[str] = Field(None, description="근무지역")
    workplace_address: Optional[str] = Field(None, description="근무지")

    # 통합 연결 필드들 (하위 엔티티 매핑)
    sections: List[NoticeSectionDTO] = Field(default_factory=list, description="모집 부문 및 자격/우대 정보 목록")
    processes: List[NoticeProcessDTO] = Field(default_factory=list, description="전형 절차 목록")
    documents: List[ApplicationDocumentDTO] = Field(default_factory=list, description="제출 서류 목록")

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
