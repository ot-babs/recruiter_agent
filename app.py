import os
import streamlit as st
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile

# Project modules
from cv_parser.cv_reader import read_cv
from cv_parser.cv_structurer import structure_cv
from cv_parser.cv_embedder import chunk_cv, embed_cv
from job_scraper.linkedin_scraper import fetch_linkedin_job_sync
from job_scraper.job_parser import parse_job_description
from job_scraper.recruiter_scraper import fetch_recruiter_info_sync, format_company_info_as_markdown  # Add the recruiter scraper
from job_scraper.recruiter_profile_scraper import fetch_recruiter_profile_sync, format_recruiter_profile_as_markdown  # Add recruiter profile scraper
from matching_engine.matcher import match_cv_to_job
from matching_engine.prompt_generator import generate_cover_letter, generate_message

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Recruiter Agent", layout="wide")
st.title("🧭 Recruiter Recruitment Agent")

# Initialize session state variables
if 'cv_struct' not in st.session_state:
    st.session_state.cv_struct = None
if 'job_struct' not in st.session_state:
    st.session_state.job_struct = None
if 'company_info' not in st.session_state:
    st.session_state.company_info = None
if 'recruiter_profile' not in st.session_state:
    st.session_state.recruiter_profile = None
if 'match_results' not in st.session_state:
    st.session_state.match_results = None
if 'cover_letter' not in st.session_state:
    st.session_state.cover_letter = None
if 'recruiter_message' not in st.session_state:
    st.session_state.recruiter_message = None
if 'job_manual_required' not in st.session_state:
    st.session_state.job_manual_required = False
if 'company_manual_required' not in st.session_state:
    st.session_state.company_manual_required = False
if 'recruiter_manual_required' not in st.session_state:
    st.session_state.recruiter_manual_required = False
if 'manual_job_text' not in st.session_state:
    st.session_state.manual_job_text = None
if 'manual_company_text' not in st.session_state:
    st.session_state.manual_company_text = None
if 'manual_recruiter_text' not in st.session_state:
    st.session_state.manual_recruiter_text = None

with st.sidebar:
    st.header("Upload & Input")
    cv_file = st.file_uploader("Upload your CV (PDF, .tex, .docx)", type=["pdf", "tex", "docx"])
    job_url = st.text_input("LinkedIn job URL")
    company_url = st.text_input("Company LinkedIn URL (optional)", help="For additional company context")
    recruiter_url = st.text_input("Recruiter LinkedIn Profile URL (optional)", help="For personalized recruiter messages")
    
    # Manual input sections (shown when scraping fails)
    if st.session_state.get('job_manual_required', False):
        st.warning("⚠️ Job scraping failed. Please paste the job description manually:")
        manual_job_text = st.text_area("Job Description", height=200, key="manual_job_input")
        if st.button("Parse Job Description"):
            if manual_job_text.strip():
                st.session_state.manual_job_text = manual_job_text
                st.session_state.job_manual_required = False
                st.rerun()
    
    if st.session_state.get('company_manual_required', False):
        st.warning("⚠️ Company scraping failed. Please paste company information manually:")
        manual_company_text = st.text_area("Company Information", height=150, key="manual_company_input")
        if st.button("Parse Company Information"):
            if manual_company_text.strip():
                st.session_state.manual_company_text = manual_company_text
                st.session_state.company_manual_required = False
                st.rerun()
    
    if st.session_state.get('recruiter_manual_required', False):
        st.warning("⚠️ Recruiter profile scraping failed. Please paste recruiter information manually:")
        manual_recruiter_text = st.text_area("Recruiter Profile Information", height=150, key="manual_recruiter_input")
        if st.button("Parse Recruiter Profile"):
            if manual_recruiter_text.strip():
                st.session_state.manual_recruiter_text = manual_recruiter_text
                st.session_state.recruiter_manual_required = False
                st.rerun()

    run_button = st.button("Analyze")

# Main analysis logic
if run_button:
    if not cv_file or not job_url:
        st.error("Please upload a CV and enter a LinkedIn URL.")
    else:
        # CV processing
        with st.spinner("Extracting and parsing CV..."):
            file_name = cv_file.name
            with NamedTemporaryFile(suffix=file_name) as tmp:
                tmp.write(cv_file.getbuffer())
                tmp.flush()
                cv_text = read_cv(tmp.name)
            st.session_state.cv_struct = structure_cv(cv_text, api_key=API_KEY)

        # Job scraping
        with st.spinner("Scraping LinkedIn and parsing job description..."):
            manual_job_text = st.session_state.get('manual_job_text', None)
            job_raw = fetch_linkedin_job_sync(job_url, manual_job_text)
            
            # Handle manual input requirement
            if job_raw.get('error') == 'MANUAL_INPUT_REQUIRED':
                st.session_state.job_manual_required = True
                st.error(f"Job scraping failed: {job_raw.get('original_error', 'Unknown error')}")
                st.info("Please provide the job description manually in the sidebar.")
                st.stop()
            
            st.session_state.job_struct = parse_job_description(job_raw["markdown"])

        # Company info scraping (if URL provided)
        if company_url:
            with st.spinner("Scraping company information..."):
                manual_company_text = st.session_state.get('manual_company_text', None)
                company_raw = fetch_recruiter_info_sync(company_url, manual_company_text)
                
                # Handle manual input requirement
                if company_raw.get('error') == 'MANUAL_INPUT_REQUIRED':
                    st.session_state.company_manual_required = True
                    st.warning(f"Company scraping failed: {company_raw.get('original_error', 'Unknown error')}")
                    st.info("You can provide company information manually in the sidebar (optional).")
                    st.session_state.company_info = None
                else:
                    st.session_state.company_info = company_raw

        # Recruiter profile scraping (if URL provided)
        if recruiter_url:
            with st.spinner("Scraping recruiter profile..."):
                manual_recruiter_text = st.session_state.get('manual_recruiter_text', None)
                recruiter_raw = fetch_recruiter_profile_sync(recruiter_url, manual_recruiter_text)
                
                # Handle manual input requirement
                if recruiter_raw.get('error') == 'MANUAL_INPUT_REQUIRED':
                    st.session_state.recruiter_manual_required = True
                    st.warning(f"Recruiter profile scraping failed: {recruiter_raw.get('original_error', 'Unknown error')}")
                    st.info("You can provide recruiter profile information manually in the sidebar for better personalization.")
                    st.session_state.recruiter_profile = None
                else:
                    st.session_state.recruiter_profile = recruiter_raw

        # Matching
        with st.spinner("Evaluating match..."):
            st.session_state.match_results = match_cv_to_job(
                st.session_state.cv_struct, 
                st.session_state.job_struct
            )
        
        # Clear previous generated content when re-analyzing
        st.session_state.cover_letter = None
        st.session_state.recruiter_message = None

# Display results if they exist in session state
if st.session_state.cv_struct and st.session_state.job_struct:
    # Display results side-by-side
    cv_col, job_col = st.columns(2)
    with cv_col:
        st.subheader("📄 Parsed CV")
        st.json(st.session_state.cv_struct, expanded=False)
    with job_col:
        st.subheader("💼 Parsed Job")
        st.json(st.session_state.job_struct, expanded=False)

    # Display company info if available
    if st.session_state.company_info:
        st.subheader("🏢 Company Information")
        if st.session_state.company_info.get('error') and st.session_state.company_info.get('error') != 'MANUAL_INPUT_REQUIRED':
            st.error(f"Error scraping company: {st.session_state.company_info['error']}")
        else:
            with st.expander("Company Details", expanded=False):
                formatted_company_info = format_company_info_as_markdown(st.session_state.company_info)
                st.markdown(formatted_company_info)

    # Display recruiter profile if available
    if st.session_state.recruiter_profile:
        st.subheader("👤 Recruiter Profile")
        if st.session_state.recruiter_profile.get('error') and st.session_state.recruiter_profile.get('error') != 'MANUAL_INPUT_REQUIRED':
            st.error(f"Error scraping recruiter profile: {st.session_state.recruiter_profile['error']}")
        else:
            with st.expander("Recruiter Details", expanded=False):
                formatted_recruiter_info = format_recruiter_profile_as_markdown(st.session_state.recruiter_profile)
                st.markdown(formatted_recruiter_info)

    # Display match results
    if st.session_state.match_results:
        st.subheader("🔍 Match Results")
        st.json(st.session_state.match_results, expanded=True)

    # Communication generation section
    st.subheader("✉️ Generate Communication")
    
    # Create columns for the buttons
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Generate Cover Letter", key="cover"):
            with st.spinner("Crafting cover letter..."):
                st.session_state.cover_letter = generate_cover_letter(
                    st.session_state.cv_struct, 
                    st.session_state.job_struct
                )
    
    with col2:
        if st.button("Generate Recruiter Message", key="message"):
            with st.spinner("Crafting recruiter message..."):
                # Include company info in the message generation if available
                company_context = ""
                if st.session_state.company_info and not st.session_state.company_info.get('error'):
                    company_context = format_company_info_as_markdown(st.session_state.company_info)
                
                # Include recruiter profile context if available
                recruiter_context = ""
                if st.session_state.recruiter_profile and not st.session_state.recruiter_profile.get('error'):
                    recruiter_context = format_recruiter_profile_as_markdown(st.session_state.recruiter_profile)
                
                st.session_state.recruiter_message = generate_message(
                    st.session_state.cv_struct, 
                    st.session_state.job_struct, 
                    company_context=company_context,
                    recruiter_context=recruiter_context
                )

    # Display generated content
    if st.session_state.cover_letter:
        st.subheader("📝 Cover Letter")
        st.text_area("Cover Letter", st.session_state.cover_letter, height=200, key="cover_display")
        st.download_button(
            "Download Cover Letter", 
            data=st.session_state.cover_letter, 
            file_name="cover_letter.txt",
            key="download_cover"
        )

    if st.session_state.recruiter_message:
        st.subheader("💬 Recruiter Message")
        st.text_area("Recruiter Message", st.session_state.recruiter_message, height=150, key="message_display")
        st.download_button(
            "Download Message", 
            data=st.session_state.recruiter_message, 
            file_name="recruiter_message.txt",
            key="download_message"
        )

# Clear session state button (optional, for debugging/reset)
if st.sidebar.button("Clear All Data"):
    for key in ['cv_struct', 'job_struct', 'company_info', 'recruiter_profile', 'match_results', 'cover_letter', 'recruiter_message', 
                'job_manual_required', 'company_manual_required', 'recruiter_manual_required', 'manual_job_text', 'manual_company_text', 'manual_recruiter_text']:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()