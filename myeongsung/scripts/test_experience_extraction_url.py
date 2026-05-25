import os
import sys
import argparse
from dotenv import load_dotenv

# sys.path에 app 폴더 상위 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.experience_extraction_service import extract_experiences_from_url

# .env 로드
load_dotenv()

def test_url_extraction(url: str):
    print(f"=== URL 경험 추출 테스트 시작 ===")
    print(f"타겟 URL: {url}\n")
    
    try:
        result = extract_experiences_from_url(url)
        print("[추출 성공!]\n")
        
        for idx, exp in enumerate(result.experiences, 1):
            print(f"--- 경험 후보 {idx} ---")
            print(f"경험명: {exp.experience_name}")
            print(f"경험 유형: {exp.experience_type}")
            print(f"기관/소속: {exp.organization}")
            print(f"기간: {exp.period}")
            print(f"나의 역할: {exp.my_role}")
            print(f"S (상황): {exp.situation}")
            print(f"A (행동): {exp.action}")
            print(f"R (결과): {exp.result}")
            print(f"L (배운점): {exp.learnings}")
            print(f"핵심 역량 태그: {exp.core_competencies}")
            print(f"활용 가능 문항: {exp.applicable_questions}")
            print(f"원문 출처 요약:\n{exp.source_text[:300]}...")
            print(f"상태: {exp.status}\n")
            
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="URL 기반 자소서 경험 추출 테스트 스크립트")
    parser.add_argument(
        "--url", 
        type=str, 
        default="https://raw.githubusercontent.com/ApptiveDev/pickd_AI/main/README.md", # 기본 임시 URL 또는 테스트용 URL
        help="경험을 추출할 자소서 또는 포트폴리오 웹페이지 URL"
    )
    
    args = parser.parse_args()
    
    # 예시 실행용 임시 URL이 기본값인 경우 가이드 출력
    if args.url == "https://raw.githubusercontent.com/ApptiveDev/pickd_AI/main/README.md":
        print("[안내] --url 인자를 제공하지 않아 테스트용 기본 URL로 실행됩니다.")
        print("실제 자소서 URL로 테스트하려면 다음과 같이 실행하세요:")
        print("python scripts/test_experience_extraction_url.py --url '원하는_자소서_링크'\n")
        
    test_url_extraction(args.url)
