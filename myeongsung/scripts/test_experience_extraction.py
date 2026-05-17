import os
import sys
from dotenv import load_dotenv

# sys.path에 app 폴더 상위 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.experience_extraction_service import extract_experiences_from_text

# .env 로드
load_dotenv()

def test_extraction():
    sample_cover_letter = """
[문항 1] 본인이 지원한 직무에 대해 어떤 역량을 갖추고 있으며, 이를 발휘한 구체적인 경험을 기술해 주십시오.

저는 IT융합 해커톤에 참가하여 '경식이 AI 전화 서비스'를 기획하고 우수한 성과를 거둔 경험이 있습니다.
당시 고령층 사용자들이 복잡한 디지털 여가 추천 모바일 앱에 접근하기 어려워한다는 문제상황에 주목했습니다.
저는 이 문제를 해결하기 위해 팀의 서비스 기획 및 사용자 조사를 총괄하며, 팀원들과 함께 인근 노인복지센터 및 공원에 직접 찾아가 현장 인터뷰를 수행했습니다. 현장 실사 과정에서 고령층의 피드백을 통해 단순 터치 방식보다 음성 기반 전화 방식이 훨씬 접근성이 좋다는 사실을 파악하고 기획의 방향을 전환하였습니다.
그 결과, 전화를 걸면 음성 안내와 대화를 통해 실시간 여가 및 복지 정보를 추천해주는 AI 전화를 설계했고, 부산대학교 IT융합 해커톤에서 최종적으로 장려상과 인기상을 동시에 수상하는 쾌거를 이루었습니다.
이 과정에서 사용자 중심의 문제해결 역량과 기획력을 크게 향상시킬 수 있었습니다.
"""

    print("=== 경험 추출 테스트 시작 ===")
    try:
        result = extract_experiences_from_text(sample_cover_letter)
        print("\n[추출 성공!]")
        for idx, exp in enumerate(result.experiences, 1):
            print(f"\n--- 경험 후보 {idx} ---")
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
            print(f"원문 출처: {exp.source_text}")
            print(f"상태: {exp.status}")
    except Exception as e:
        print(f"에러 발생: {e}")

if __name__ == "__main__":
    test_extraction()
