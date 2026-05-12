import os
import asyncio
from dotenv import load_dotenv
from app.services.job_analysis_service import analyze_job_url
import json

# .env 파일 로드
load_dotenv()

async def test_saramin_analysis():
    url = "https://www.saramin.co.kr/zf_user/jobs/relay/view?rec_idx=53645367&view_type=list&t_ref=main&t_ref_content=major_company&t_category=relay_view#seq=1"
    
    print(f"🚀 테스트 시작 (URL: {url})")
    print("--- 개선된 재귀적 스크래핑 로직 가동 중 ---")
    
    try:
        result = analyze_job_url(url)
        
        print("\n" + "="*50)
        print("✅ 분석 완료!")
        print("="*50)
        print(f"🏢 기업명: {result.company_name}")
        print(f"📌 공고명: {result.notice_name}")
        print(f"📅 기간: {result.started_at} ~ {result.ended_at}")
        
        print("\n[모집 부문]")
        for sec in result.sections:
            print(f"- {sec.section_name} ({sec.job_title})")
            if sec.responsibilities:
                print(f"  └ 업무: {sec.responsibilities[:50]}...")
        
        print("\n[발견된 출처(Citations)]")
        for cit in result.citations[:3]:
            print(f"- 필드: {cit.field}")
            print(f"  내용: {cit.content[:60]}...")
            print(f"  링크: {cit.source_url}")
            
        # 상세 결과 저장
        with open("tests/results/saramin_test_result.json", "w", encoding="utf-8") as f:
            f.write(result.model_dump_json(indent=2))
            
    except Exception as e:
        print(f"\n❌ 분석 실패: {e}")

if __name__ == "__main__":
    asyncio.run(test_saramin_analysis())
