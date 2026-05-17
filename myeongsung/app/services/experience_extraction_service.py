import os
import requests
from bs4 import BeautifulSoup
import fitz  # PyMuPDF
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.resume_dto import ExperienceExtractionResponse

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
        result = chain.invoke({"text": text}, config={"run_name": "experience-extraction"})
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

