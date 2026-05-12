import streamlit as st
import requests
import fitz  # PyMuPDF
from PIL import Image, ImageDraw
import io
import os

st.set_page_config(page_title="Pickd AI - JD Analyzer Demo", layout="wide")

st.title("🚀 Pickd AI - 채용 공고 분석 데모")
st.markdown("PDF, URL, 이미지 공고를 분석하고 출처를 시각적으로 확인하세요.")

# --- 사이드바 설정 ---
st.sidebar.header("설정")
analysis_mode = st.sidebar.selectbox("분석 모드 선택", ["PDF 분석", "URL 분석", "이미지 분석"])
api_base_url = st.sidebar.text_input("API 서버 주소", "http://127.0.0.1:8001/api/v1")

# --- 유틸리티 함수 ---
def draw_bbox(image, bbox, citation, label=None):
    """이미지 위에 bbox를 그리며, 정규화된 좌표(0-1)와 픽셀 좌표를 모두 대응합니다."""
    img_w, img_h = image.size
    
    # 1. 정규화 여부 확인 (모든 값이 1.1 이하이면 0~1 사이의 비율로 간주)
    is_normalized = all(v <= 1.1 for v in bbox)
    
    if is_normalized:
        # 0~1 사이의 비율인 경우 -> 이미지 크기를 직접 곱함
        scaled_bbox = [
            bbox[0] * img_w,
            bbox[1] * img_h,
            bbox[2] * img_w,
            bbox[3] * img_h
        ]
    else:
        # 절대 좌표(Point/Pixel)인 경우 -> 기존 스케일 보정 로직 사용
        orig_w = citation.get("page_width") or img_w
        orig_h = citation.get("page_height") or img_h
        scale_x = img_w / orig_w
        scale_y = img_h / orig_h
        scaled_bbox = [
            bbox[0] * scale_x,
            bbox[1] * scale_y,
            bbox[2] * scale_x,
            bbox[3] * scale_y
        ]
    
    # 디버깅용 로그
    st.write(f"🔍 **Debug BBox**: {'Normalized' if is_normalized else 'Absolute'} {bbox} -> Scaled {scaled_bbox}")
    
    draw = ImageDraw.Draw(image)
    draw.rectangle(scaled_bbox, outline="#FF69B4", width=5)
    if label:
        draw.text((scaled_bbox[0], scaled_bbox[1]-15), label, fill="#FF69B4")
    return image




def render_pdf_page(pdf_bytes, page_num):
    """PDF 특정 페이지를 이미지로 렌더링하고 원본 크기 정보를 함께 반환합니다."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc.load_page(page_num - 1)
    
    # 원본 페이지 크기 (Point 단위)
    pdf_size = (page.rect.width, page.rect.height)
    
    # 렌더링 (DPI를 높여서 더 선명하게 볼 수도 있음, 여기서는 1.0배율)
    pix = page.get_pixmap()
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    
    return img, pdf_size


# --- 메인 로직 ---
if analysis_mode == "PDF 분석":
    uploaded_file = st.file_uploader("분석할 PDF 파일을 업로드하세요", type=["pdf"])
    if uploaded_file and st.button("PDF 분석 시작"):
        with st.spinner("Upstage & LLM 분석 중..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            response = requests.post(f"{api_base_url}/analyze/pdf", files=files)
            
            if response.status_code == 200:
                result = response.json()
                st.session_state["analysis_result"] = result
                st.session_state["pdf_bytes"] = uploaded_file.getvalue()
                # 헤더에서 신뢰도 추출
                st.session_state["confidence"] = response.headers.get("X-Analysis-Confidence", "0")
                st.success("분석 완료!")
            else:
                st.error(f"오류 발생: {response.text}")

elif analysis_mode == "URL 분석":
    url = st.text_input("채용 공고 URL을 입력하세요", placeholder="https://www.saramin.co.kr/...")
    if url and st.button("URL 분석 시작"):
        with st.spinner("Firecrawl & LLM 분석 중..."):
            response = requests.post(f"{api_base_url}/analyze/url", json={"url": url})
            if response.status_code == 200:
                st.session_state["analysis_result"] = response.json()
                # 헤더에서 신뢰도 추출
                st.session_state["confidence"] = response.headers.get("X-Analysis-Confidence", "0")
                st.success("분석 완료!")
            else:
                st.error(f"오류 발생: {response.text}")

elif analysis_mode == "이미지 분석":
    uploaded_files = st.file_uploader("공고 이미지들을 업로드하세요 (다중 선택 가능)", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
    if uploaded_files and st.button("이미지 통합 분석 시작"):
        with st.spinner("Gemini 2.5 Flash-Lite 분석 중..."):
            files = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
            response = requests.post(f"{api_base_url}/analyze/image", files=files)
            if response.status_code == 200:
                st.session_state["analysis_result"] = response.json()
                st.session_state["image_bytes_list"] = [f.getvalue() for f in uploaded_files]
                # 헤더에서 신뢰도 추출
                st.session_state["confidence"] = response.headers.get("X-Analysis-Confidence", "0")
                st.success("분석 완료!")
            else:
                st.error(f"오류 발생: {response.text}")

# --- 결과 표시 및 시각화 ---
if "analysis_result" in st.session_state:
    result = st.session_state["analysis_result"]
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📋 추출된 채용 정보")
        
        # 신뢰도 지수 표시
        if "confidence" in st.session_state:
            conf = float(st.session_state["confidence"])
            color = "green" if conf >= 0.8 else "orange" if conf >= 0.5 else "red"
            st.markdown(f"**💡 분석 신뢰도:** :{color}[{conf*100:.0f}%]")
            st.progress(conf)
        
        # 1. 최상위 공고 정보
        st.markdown(f"### 🏢 {result.get('company_name', '기업명 없음')}")
        st.markdown(f"#### {result.get('notice_name', '공고명 없음')}")
        
        st.write(f"**채용 구분**: {result.get('category', 'N/A')} | **고용 형태**: {result.get('employment_type', 'N/A')}")
        st.write(f"**접수 기간**: {result.get('started_at', 'N/A')} ~ {result.get('ended_at', 'N/A')}")
        st.write(f"**채용 인원**: {result.get('headcount', '0')}명 | **근무 지역**: {result.get('region_1depth', '')} {result.get('workplace_address', '')}")
        if result.get('notice_url'):
            st.link_button("공고 원문 링크", result['notice_url'])
            
        st.divider()

        # 2. 계층형 정보 탭으로 구성
        tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎯 모집 부문", "🗓 전형 절차", "📄 제출 서류", "🏢 기업 정보", "⚠️ 유의사항"])

        # 탭 1: 모집 부문 (자격, 우대, 자소서 포함)
        with tab1:
            sections = result.get('sections', [])
            if not sections:
                st.info("모집 부문 정보가 없습니다.")
            for i, section in enumerate(sections):
                with st.expander(f"📌 {section.get('section_name', '부문명')} - {section.get('job_title', '직무명')}", expanded=True):
                    st.write(f"**세부 직무**: {section.get('sub_job_title', 'N/A')} | **인원**: {section.get('headcount', 'N/A')}")
                    st.write(f"**담당 업무**: {section.get('responsibilities', 'N/A')}")
                    
                    if section.get('qualifications'):
                        st.markdown("**✅ [지원 자격]**")
                        for q in section['qualifications']:
                            st.write(f"- 필수: {q.get('mandatory_qualification', 'N/A')}")
                            st.write(f"- 학력/전공: {q.get('education_requirement', '')} / {q.get('major_requirement', '')}")
                    
                    if section.get('preferences'):
                        st.markdown("**⭐ [우대 사항]**")
                        for p in section['preferences']:
                            st.write(f"- 우대: {p.get('general_preference', 'N/A')}")
                    
                    if section.get('questions'):
                        st.markdown("**📝 [자소서 문항]**")
                        for q in section['questions']:
                            st.info(f"Q{q.get('question_number', '?')}. {q.get('question_content', '')} ({q.get('character_limit', '제한 없음')})")

        # 탭 2: 전형 절차
        with tab2:
            processes = result.get('processes', [])
            if not processes:
                st.info("전형 절차 정보가 없습니다.")
            for p in processes:
                st.markdown(f"**🔹 {p.get('process_name', '전형')}**")
                st.write(f"- 서류 일정: {p.get('document_screen_schedule', 'N/A')}")
                st.write(f"- 코테/필기: {p.get('coding_test_schedule', '')} {p.get('written_exam_schedule', '')}")
                st.write(f"- 면접 일정: {p.get('interview_schedule', 'N/A')}")
                st.write(f"- 합격 발표: {p.get('announcement_date', 'N/A')}")
                st.divider()

        # 탭 3: 제출 서류
        with tab3:
            documents = result.get('documents', [])
            if not documents:
                st.info("제출 서류 정보가 없습니다.")
            for d in documents:
                st.markdown(f"**📄 대상: {d.get('target_type', '공통')}**")
                st.write(f"- 필수 서류: {d.get('mandatory_documents', 'N/A')}")
                st.write(f"- 선택 서류: {d.get('optional_documents', 'N/A')}")
                st.write(f"- 제출 형식: {d.get('submission_format', 'N/A')}")
                st.divider()

        # 탭 4: 기업 정보
        with tab4:
            ci = result.get('company_info', {})
            if not ci:
                st.info("기업 정보가 없습니다.")
            else:
                st.write(f"**소개**: {ci.get('company_introduction', 'N/A')}")
                st.write(f"**인재상**: {ci.get('ideal_candidate', 'N/A')}")
                st.write(f"**근무조건**: {ci.get('working_conditions', 'N/A')}")
                st.write(f"**복리후생**: {ci.get('benefits', 'N/A')}")

        # 탭 5: 유의사항
        with tab5:
            gl = result.get('guideline', {})
            if not gl:
                st.info("유의사항 정보가 없습니다.")
            else:
                st.write(f"**공통 유의사항**: {gl.get('general_notes', 'N/A')}")
                st.write(f"**중복 지원**: {gl.get('duplicate_apply_restriction', 'N/A')}")
                st.write(f"**합격 취소**: {gl.get('cancellation_conditions', 'N/A')}")

        st.divider()
        st.subheader("🔗 출처(Citations) 목록")
        for i, citation in enumerate(result.get("citations", [])):
            with st.expander(f"[{i+1}] 필드명: {citation['field']}"):
                st.write(f"**내용**: {citation['content']}")
                if citation.get("source_url"):
                    st.link_button("원본 위치 확인", citation["source_url"])
                
                # 시각화 버튼
                if st.button(f"위치 보기", key=f"btn_{i}"):
                    st.session_state["selected_citation"] = citation

    with col2:
        st.subheader("📍 원본 위치 시각화")
        if "selected_citation" in st.session_state:
            cit = st.session_state["selected_citation"]
            
            # PDF 시각화
            if analysis_mode == "PDF 분석" and "pdf_bytes" in st.session_state:
                page_img, pdf_size = render_pdf_page(st.session_state["pdf_bytes"], cit["page"])
                if cit.get("bbox"):
                    page_img = draw_bbox(page_img, cit["bbox"], cit, cit["field"])
                    st.image(page_img, caption=f"Page {cit['page']} 분석 결과", width="stretch")
                else:
                    st.warning("⚠️ 이 출처에 대한 좌표 정보(bbox)가 결과에 포함되지 않았습니다.")
                    st.image(page_img, caption=f"Page {cit['page']} (좌표 없음)", width="stretch")



            
            # 이미지 시각화
            elif analysis_mode == "이미지 분석" and "image_bytes_list" in st.session_state:
                img_idx = cit["page"] - 1
                if 0 <= img_idx < len(st.session_state["image_bytes_list"]):
                    img = Image.open(io.BytesIO(st.session_state["image_bytes_list"][img_idx]))
                    if cit.get("bbox"):
                        # Gemini bbox는 보통 정규화되어 있을 수 있으므로 처리 필요 (현재는 Upstage 스타일 좌표 가정)
                        img = draw_bbox(img, cit["bbox"], cit, cit["field"])
                    st.image(img, caption=f"이미지 {cit['page']} 분석 결과", width="stretch")

            
            # URL은 링크로 대체
            else:
                st.info("URL 분석은 '원본 위치 확인' 버튼을 클릭해 브라우저에서 직접 확인하세요.")
        else:
            st.info("왼쪽 목록에서 '위치 보기' 버튼을 클릭하면 이곳에 해당 영역이 표시됩니다.")
