from pydantic import BaseModel, Field
from typing import List, Optional, Union

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
