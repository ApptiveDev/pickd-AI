import os
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import Any, List, Optional
from app.schemas.resume_dto import (
    ExperienceExtractionResponse,
    ExperiencePresetSchema,
    ExperienceSummary,
    Step1ExtractionResponse,
    Step2ExtractionResponse,
    Step2ExtractedExperience,
    Step2V2ExtractionResponse,
)
from app.services.experience_preset_service import build_dynamic_step2_model
def extract_step1_from_text(text: str) -> Step1ExtractionResponse:
    """
    텍스트에서 1차 경험 추출 (상세 증빙형 / 스펙 증빙형 분류 및 경험명 추출)
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 사용자의 자기소개서(자소서) 또는 이력서 원문에서 경험 목록을 1차적으로 파악하고 분류하는 전문가입니다.\n"
            "주어진 텍스트에 포함된 모든 경험을 찾아내고, 각각을 대분류(상세 서술형, 스펙·증빙형)와 소분류로 정확히 나누어 반환하세요.\n\n"
            "### 🚨 엄격한 분류 기준 (반드시 아래의 매핑을 지킬 것):\n"
            "1. **상세 서술형 (상세 증빙형)**:\n"
            "   - 오직 이 소분류만 가능: 프로젝트, 대외활동, 인턴/직무경험, 공모전, 봉사활동, 교환학생, 알바, 학부연구생\n"
            "2. **스펙·증빙형**:\n"
            "   - 오직 이 소분류만 가능: 어학, 자격증, 수상, 수강과목, 교육 이수\n\n"
            "발견된 모든 독립된 경험의 이름(experience_name)을 추출하고, 위 매핑 규칙에 어긋나지 않도록 대분류(experience_group)와 소분류(experience_type)를 짝지어 반환하세요."
        )),
        ("user", "다음 내용에서 1차 경험 목록을 추출해주세요:\n\n{text}")
    ])
    
    chain = prompt | llm.with_structured_output(Step1ExtractionResponse)
    
    try:
        return chain.invoke({"text": text})
    except Exception as e:
        raise ValueError(f"1차 경험 추출 중 오류가 발생했습니다: {str(e)}")

def extract_step1_from_url(url: str) -> Step1ExtractionResponse:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
            doc = fitz.open(stream=response.content, filetype="pdf")
            text_list = [page.get_text() for page in doc]
            full_text = "\n".join(text_list)
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
                
            full_text = soup.get_text(separator="\n")
            lines = (line.strip() for line in full_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            full_text = "\n".join(chunk for chunk in chunks if chunk)
        
        if not full_text.strip():
            raise ValueError("URL에서 유의미한 텍스트를 추출하지 못했습니다.")
            
        return extract_step1_from_text(full_text)
    except Exception as e:
        raise ValueError(f"URL 분석 중 오류가 발생했습니다: {str(e)}")

def extract_step1_from_pdf(file_content: bytes) -> Step1ExtractionResponse:
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        text_list = [page.get_text() for page in doc]
        full_text = "\n".join(text_list)
        
        if not full_text.strip():
            raise ValueError("PDF에서 유의미한 텍스트를 추출하지 못했습니다.")
            
        return extract_step1_from_text(full_text)
    except Exception as e:
        raise ValueError(f"PDF 분석 중 오류가 발생했습니다: {str(e)}")


def extract_experiences_from_text(text: str) -> ExperienceExtractionResponse:
    """
    텍스트 본문(자소서 등)에서 AI를 사용해 경험을 STAR 기반으로 구조화하여 추출합니다.
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 사용자의 자기소개서(자소서) 원문에서 경험(Experience)을 추출하는 전문가입니다.\n"
            "주어진 자소서 내용에서 하나 또는 여러 개의 독립된 경험을 추출하여 구조화된 데이터로 반환하세요.\n\n"
            "### 추출 가이드라인:\n"
            "1. **경험 분리**: 자소서 하나에 여러 경험(예: 인턴, 해커톤 등)이 섞여 있다면 각각을 분리하여 추출하세요.\n"
            "2. **STAR 구조화**: 각 경험에 대해 다음 항목들을 명확히 분류하세요.\n"
            "   - 경험명 (experience_name)\n"
            "   - 경험 유형 (experience_type)\n"
            "   - 기관/소속 (organization)\n"
            "   - 기간 (period)\n"
            "   - 나의 역할 (my_role)\n"
            "   - [S] 문제상황 (situation)\n"
            "   - [A] 주요 행동 (action)\n"
            "   - [R] 결과/성과 (result)\n"
            "   - [L] 배운 점 (learnings)\n"
            "3. **역량 태그**: 해당 경험을 통해 어필할 수 있는 핵심 역량(예: 문제해결, 사용자 이해, 기획력, 소익성 등)을 2~4개 추출하여 core_competencies 필드에 저장하세요.\n"
            "4. **활용 가능 문항**: 이 경험이 어떤 면접/자소서 문항(예: 갈등 극복, 도전, 직무 역량, 공익 기여 등)에 적합한지 추천하여 applicable_questions 필드에 저장하세요.\n"
            "5. **원문 출처**: 해당 경험을 추출한 원문의 실제 문장들을 source_text 필드에 기록하세요.\n"
            "6. **상태**: 상태(status)는 기본적으로 '미확인'으로 지정하세요.\n"
        )),
        ("user", "다음은 자기소개서 내용입니다. 위 가이드라인에 따라 경험을 추출해주세요:\n\n{text}")
    ])
    
    chain = prompt | llm.with_structured_output(ExperienceExtractionResponse)
    
    try:
        result = chain.invoke(
            {"text": text},
            config={
                "run_name": "experience-extraction",
                "tags": ["experience-extraction", "cover-letter", "ncs-public"],
                "metadata": {
                    "model": "gpt-4o",
                    "extraction_format": "STAR+L",
                    "project": "pickd"
                }
            }
        )
        return result
    except Exception as e:
        raise ValueError(f"경험 추출 중 오류가 발생했습니다: {str(e)}")


def extract_experiences_from_url(url: str) -> ExperienceExtractionResponse:
    """
    URL에서 텍스트를 추출한 후 경험 추출 로직을 실행합니다.
    """
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
            doc = fitz.open(stream=response.content, filetype="pdf")
            text_list = [page.get_text() for page in doc]
            full_text = "\n".join(text_list)
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
                
            full_text = soup.get_text(separator="\n")
            lines = (line.strip() for line in full_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            full_text = "\n".join(chunk for chunk in chunks if chunk)
        
        if not full_text.strip():
            raise ValueError("URL에서 유의미한 텍스트를 추출하지 못했습니다.")
            
        return extract_experiences_from_text(full_text)
    except Exception as e:
        raise ValueError(f"URL 분석 중 오류가 발생했습니다: {str(e)}")


def extract_experiences_from_pdf(file_content: bytes) -> ExperienceExtractionResponse:
    """
    PDF 바이너리 데이터에서 PyMuPDF를 사용하여 텍스트를 추출한 후 경험 추출 로직을 실행합니다.
    """
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        text_list = []
        for page in doc:
            text_list.append(page.get_text())
        full_text = "\n".join(text_list)
        
        if not full_text.strip():
            raise ValueError("PDF에서 유의미한 텍스트를 추출하지 못했습니다.")
            
        return extract_experiences_from_text(full_text)
    except Exception as e:
        raise ValueError(f"PDF 분석 중 오류가 발생했습니다: {str(e)}")

def _step2_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 사용자의 원문 텍스트에서 특정 경험의 상세 항목을 추출하는 전문가입니다.\n"
            "사용자가 제공하는 '선택된 경험'에 대하여 원문에서 해당하는 내용을 찾아 지정된 스키마에 맞게 상세 정보를 추출하세요.\n\n"
            "### 추출 가이드라인:\n"
            "1. 선택된 경험과 원문을 대조하여, 해당 경험이 언급된 부분을 찾습니다.\n"
            "2. 경험의 `experience_group`과 `experience_type`을 유지하면서, `basic_info` 필드를 해당 타입에 맞게 추출해야 합니다.\n"
            "   - '상세 서술형' (프로젝트, 대외활동, 인턴/직무경험, 공모전, 봉사활동, 교환학생 등)\n"
            "   - '스펙·증빙형' (어학, 자격증, 수상, 수강과목, 교육 이수 등)\n"
            "3. 해당 소분류별 스키마에 정의된 정보만 원문에서 추출하며, 원문에서 찾을 수 없는 정보는 null 또는 빈 문자열로 남겨둡니다.\n"
            "4. `keywords` 필드에는 다음 **[제공된 역량/태도 키워드 풀]** 내에서만 매핑하여 저장하세요.\n"
            "   - [키워드 풀]: 문제 해결, 창의적 학습, 리더십, 의사소통, 팀워크, 분석력, 실행력, 책임감, 적응력, 꼼꼼함, 도전 정신, 기획력\n"
            "   - 원문의 내용을 냉정하고 객관적으로 판단하여 이 경험을 가장 잘 대표하는 키워드를 1~3개 선택하세요.\n"
            "   - 🚨 주의사항: 억지로 키워드를 매핑해서는 안 됩니다. 위 키워드 풀 중에 원문과 정확히 부합하는 키워드가 없다면 빈 리스트를 반환하세요.\n"
            "   - 제공된 풀 외의 새로운 단어를 임의로 만들어내지 마세요.\n"
            "5. 원문에서 해당 경험의 전체 '본문'을 추출하여 `experience_content` 필드에 하나의 문자열로 저장하고, 이를 문장 단위(또는 의미 있는 한 줄 단위)로 분리하여 `tagged_body_text` 배열에도 저장하세요.\n"
            "   - 원문 내용 중 모든 문장을 빠짐없이 추출해야 하며, 각 문장(sentence)마다 가장 적합한 1개의 태그(tag)를 부여하세요.\n"
            "   - ⚠️ 중요: 한 경험(`experience`) 내에서 '일반 문장'을 제외한 나머지 태그들은 단 1번만 사용할 수 있습니다.\n"
            "   - 동일한 의미의 문장이 여러 개일 경우 가장 핵심적인 1개의 문장에만 해당 태그를 부여하고, 나머지는 '일반 문장'으로 분류하세요.\n"
            "   - 허용된 태그: 나의 역할, 문제 상황, 실행 과정, 성과, 수치 성과, 배운 점, 직무 연결성, 협업 방식, 일반 문장\n"
            "   - 🚨 특별 규칙: '스펙·증빙형' (어학, 자격증, 오픽 등) 경험의 경우, 원문에 여러 스펙이 쉼표나 파이프(|) 등으로 나열되어 있더라도, `experience_content`에는 **오직 현재 추출 중인 경험과 관련된 부분(예: 토익 경험이라면 '토익점수 : 850' 등)**만 추출해야 합니다. 나열된 전체 문자열을 그대로 가져오지 마세요.\n"
        )),
        ("user", "다음은 원문 텍스트입니다:\n\n<TEXT>\n{text}\n</TEXT>\n\n다음은 상세 내용을 추출해야 할 선택된 경험입니다:\n{selected_experience}")
    ])


def extract_step2_from_text(text: str, selected_experiences: List[ExperienceSummary]) -> Step2ExtractionResponse:
    """
    1차 추출에서 사용자가 선택한 경험 리스트를 바탕으로, 각 경험의 소분류에 맞는 맞춤형 필드를 원문에서 추출합니다.
    (TPM 제한 방지를 위해 각 경험별로 개별 추출 후 병합합니다.)
    """
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = _step2_prompt()
    
    chain = prompt | llm.with_structured_output(Step2ExtractedExperience)
    
    extracted_experiences = []
    for exp in selected_experiences:
        try:
            result = chain.invoke(
                {
                    "text": text,
                    "selected_experience": exp.model_dump()
                },
                config={
                    "run_name": f"experience-step2-extraction-{exp.experience_name}",
                    "tags": ["experience-extraction", "step2"]
                }
            )
            extracted_experiences.append(result)
        except Exception as e:
            raise ValueError(f"'{exp.experience_name}' 2차 경험 추출 중 오류가 발생했습니다: {str(e)}")
            
    return Step2ExtractionResponse(experiences=extracted_experiences)


def extract_step2_v2_from_text(
    text: str,
    selected_experiences: List[ExperienceSummary],
    preset_schemas: List[ExperiencePresetSchema],
    llm: Optional[Any] = None,
) -> Step2V2ExtractionResponse:
    preset_by_type = {
        preset.experience_type_name: preset
        for preset in preset_schemas
    }
    prompt = _step2_prompt()
    extraction_llm = llm or ChatOpenAI(model="gpt-4o", temperature=0)
    extracted_experiences = []

    for experience in selected_experiences:
        preset = preset_by_type.get(experience.experience_type)
        if preset is None:
            raise ValueError(
                f"'{experience.experience_type}' 경험의 프리셋 스키마가 없습니다."
            )
        output_model = build_dynamic_step2_model(experience, preset)
        chain = prompt | extraction_llm.with_structured_output(output_model)
        try:
            result = chain.invoke(
                {
                    "text": text,
                    "selected_experience": experience.model_dump(),
                },
                config={
                    "run_name": f"experience-step2-v2-extraction-{experience.experience_name}",
                    "tags": ["experience-extraction", "step2-v2"],
                },
            )
        except Exception as e:
            raise ValueError(
                f"'{experience.experience_name}' 2차 V2 경험 추출 중 오류가 발생했습니다: {str(e)}"
            )

        if result.experience_type != experience.experience_type:
            raise ValueError("AI 응답의 경험 유형이 선택 경험과 일치하지 않습니다.")
        if result.experience_group != experience.experience_group:
            raise ValueError("AI 응답의 경험 그룹이 선택 경험과 일치하지 않습니다.")
        extracted_experiences.append(result.model_dump())

    return Step2V2ExtractionResponse(experiences=extracted_experiences)

def extract_step2_from_url(url: str, selected_experiences: List[ExperienceSummary]) -> Step2ExtractionResponse:
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        response.raise_for_status()
        
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
            doc = fitz.open(stream=response.content, filetype="pdf")
            text_list = [page.get_text() for page in doc]
            full_text = "\n".join(text_list)
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
                
            full_text = soup.get_text(separator="\n")
            lines = (line.strip() for line in full_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            full_text = "\n".join(chunk for chunk in chunks if chunk)
        
        if not full_text.strip():
            raise ValueError("URL에서 유의미한 텍스트를 추출하지 못했습니다.")
            
        return extract_step2_from_text(full_text, selected_experiences)
    except Exception as e:
        raise ValueError(f"URL 분석 중 오류가 발생했습니다: {str(e)}")

def extract_step2_from_pdf(file_content: bytes, selected_experiences: List[ExperienceSummary]) -> Step2ExtractionResponse:
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        text_list = [page.get_text() for page in doc]
        full_text = "\n".join(text_list)
        
        if not full_text.strip():
            raise ValueError("PDF에서 유의미한 텍스트를 추출하지 못했습니다.")
            
        return extract_step2_from_text(full_text, selected_experiences)
    except Exception as e:
        raise ValueError(f"PDF 분석 중 오류가 발생했습니다: {str(e)}")


def extract_step2_v2_from_url(
    url: str,
    selected_experiences: List[ExperienceSummary],
    preset_schemas: List[ExperiencePresetSchema],
) -> Step2V2ExtractionResponse:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").lower()
        if "application/pdf" in content_type or url.lower().split("?")[0].endswith(".pdf"):
            doc = fitz.open(stream=response.content, filetype="pdf")
            full_text = "\n".join(page.get_text() for page in doc)
        else:
            soup = BeautifulSoup(response.text, "html.parser")
            for script in soup(["script", "style"]):
                script.decompose()
            raw_text = soup.get_text(separator="\n")
            lines = (line.strip() for line in raw_text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            full_text = "\n".join(chunk for chunk in chunks if chunk)

        if not full_text.strip():
            raise ValueError("URL에서 유의미한 텍스트를 추출하지 못했습니다.")
        return extract_step2_v2_from_text(
            full_text,
            selected_experiences,
            preset_schemas,
        )
    except Exception as e:
        raise ValueError(f"URL 분석 중 오류가 발생했습니다: {str(e)}")


def extract_step2_v2_from_pdf(
    file_content: bytes,
    selected_experiences: List[ExperienceSummary],
    preset_schemas: List[ExperiencePresetSchema],
) -> Step2V2ExtractionResponse:
    try:
        doc = fitz.open(stream=file_content, filetype="pdf")
        full_text = "\n".join(page.get_text() for page in doc)
        if not full_text.strip():
            raise ValueError("PDF에서 유의미한 텍스트를 추출하지 못했습니다.")
        return extract_step2_v2_from_text(
            full_text,
            selected_experiences,
            preset_schemas,
        )
    except Exception as e:
        raise ValueError(f"PDF 분석 중 오류가 발생했습니다: {str(e)}")
