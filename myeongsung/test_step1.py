import asyncio
from dotenv import load_dotenv
load_dotenv()

from app.services.experience_extraction_service import extract_step1_from_pdf

with open("한국전력공사 합격자소서.pdf", "rb") as f:
    pdf_bytes = f.result = f.read()

result = extract_step1_from_pdf(pdf_bytes)
print(result.model_dump_json(indent=2))
