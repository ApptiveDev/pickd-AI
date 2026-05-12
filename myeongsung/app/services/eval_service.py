import os
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from app.schemas.job_dto import JobPostingCreate
from pydantic import BaseModel, Field
from typing import List

class FieldScore(BaseModel):
    field_name: str
    score: float
    reason: str

class EvalResult(BaseModel):
    overall_score: float = 0.0
    completeness_score: float
    accuracy_score: float
    structure_score: float
    hallucination_score: float
    field_scores: List[FieldScore] = []
    summary: str
    improvements: List[str] = []

def log_evaluation(extraction: JobPostingCreate, source_text: str, case_name: str):
    """
    분석 결과를 평가하고 결과를 logs/evaluation_history.jsonl에 기록합니다.
    """
    extraction_json = extraction.model_dump_json()
    
    judge_llm = ChatOpenAI(model="gpt-4o", temperature=0)
    judge_prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 채용 공고 추출 품질을 평가하는 전문 심사위원입니다.\n"
            "원본 텍스트와 추출된 JSON을 비교하여 completeness, accuracy, structure, hallucination 점수(0~1)를 매기세요."
        )),
        ("user", "Source Content:\n{source_text}\n\nExtraction Result (JSON):\n{extraction_json}")
    ])
    
    chain = judge_prompt | judge_llm.with_structured_output(EvalResult)
    
    try:
        result = chain.invoke({
            "source_text": source_text[:3000],
            "extraction_json": extraction_json
        })
        result.overall_score = (result.completeness_score + result.accuracy_score + result.structure_score + result.hallucination_score) / 4
        
        # 로그 기록
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "case_name": case_name,
            "overall_score": result.overall_score,
            "metrics": result.model_dump(),
            "extraction_summary": {
                "company": extraction.company_name,
                "notice": extraction.notice_name
            }
        }
        
        os.makedirs("logs", exist_ok=True)
        with open("logs/evaluation_history.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
            
        print(f"[✓] Evaluation logged for {case_name} (Score: {result.overall_score:.2f})")
    except Exception as e:
        print(f"[!] Evaluation logging failed: {e}")
