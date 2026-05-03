import os
import requests
import json
from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.job_dto import JobPostingCreate

def _scrape_url_multimodal(url: str, firecrawl_api_key: str) -> dict:
    """Firecrawl을 사용하여 마크다운과 스크린샷을 동시에 획득"""
    try:
        response = requests.post(
            'https://api.firecrawl.dev/v2/scrape',
            headers={
                'Authorization': f'Bearer {firecrawl_api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'url': url, 
                'formats': ['markdown', 'screenshot'],
                'waitFor': 2000 # 동적 콘텐츠 로딩 대기
            },
            timeout=60
        )
        response.raise_for_status()
        data = response.json().get("data", {})
        return {
            "markdown": data.get("markdown", ""),
            "screenshot_url": data.get("screenshot", "")
        }
    except Exception as e:
        print(f"[!] 스크래핑 실패 ({url}): {e}")
        return {"markdown": "", "screenshot_url": ""}

def _analyze_with_vision(image_url: str, google_api_key: str) -> JobPostingCreate:
    """Gemini 2.0 Flash를 사용하여 공고 이미지를 시각적으로 분석"""
    from google import genai
    from google.genai import types
    import PIL.Image
    import io
    
    client = genai.Client(api_key=google_api_key)
    
    prompt = (
        "제공된 채용 공고 스크린샷을 면밀히 분석하여 구조화된 데이터를 추출하세요.\n"
        "텍스트가 이미지(JPG/PNG)나 Iframe 내에 있더라도 모두 읽어내야 합니다.\n"
        "특히 모집 부문(sections)과 각 부문별 상세 자격요건, 우대사항을 놓치지 마세요."
    )
    
    try:
        # 이미지 다운로드
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        image = PIL.Image.open(io.BytesIO(img_response.content))

        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=[image, prompt],
            config=types.GenerateContentConfig(
                response_mime_type='application/json',
                response_schema=JobPostingCreate.model_json_schema(),
                temperature=0,
            )
        )
        return JobPostingCreate(**json.loads(response.text))
    except Exception as e:
        print(f"[!] 비전 분석 실패: {e}")
        return None

def analyze_job_url(url: str) -> JobPostingCreate:
    """
    텍스트 분석과 비전 분석을 결합한 멀티모달 채용 공고 추출
    """
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY")
    
    if not firecrawl_api_key:
        raise ValueError("FIRECRAWL_API_KEY가 설정되지 않았습니다.")

    try:
        # 1. 멀티모달 데이터 획득 (Markdown + Screenshot)
        print(f"[*] 멀티모달 스크래핑 시작: {url}")
        scrape_data = _scrape_url_multimodal(url, firecrawl_api_key)
        markdown = scrape_data["markdown"]
        screenshot_url = scrape_data["screenshot_url"]

        # 2. 1차 텍스트 분석 (GPT-4o)
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        text_prompt = ChatPromptTemplate.from_messages([
            ("system", "당신은 채용 공고 텍스트 분석 전문가입니다. 주어진 마크다운에서 정보를 추출하세요."),
            ("user", "{markdown}")
        ])
        text_chain = text_prompt | llm.with_structured_output(JobPostingCreate)
        text_result = text_chain.invoke({"markdown": markdown})

        # 3. 2차 비전 분석 (정보가 부족하거나 보강이 필요한 경우)
        # 모집 부문(sections)이 비어있으면 비전 엔진 가동
        if (not text_result.sections or len(text_result.sections) == 0) and screenshot_url:
            print("[*] 텍스트 정보 부족 감지 -> 비전 엔진(Gemini 2.0 Flash) 가동")
            vision_result = _analyze_with_vision(screenshot_url, google_api_key)
            if vision_result:
                # 비전 결과로 텍스트 결과 보완
                text_result.sections = vision_result.sections
                if vision_result.company_info:
                    text_result.company_info = vision_result.company_info
                print("[*] 비전 엔진을 통해 데이터를 성공적으로 보완했습니다.")

        return text_result

    except Exception as e:
        print(f"[!] 분석 중 오류 발생: {e}")
        raise ValueError(f"통합 분석 중 오류가 발생했습니다: {str(e)}")
