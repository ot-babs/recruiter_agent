import os
import streamlit as st
from dotenv import load_dotenv
from tempfile import NamedTemporaryFile
from pathlib import Path

# Project modules
from cv_parser.cv_reader import read_cv
from cv_parser.cv_structurer import structure_cv
from cv_parser.cv_embedder import chunk_cv, embed_cv
from job_scraper.linkedin_scraper import fetch_linkedin_job_sync
from job_scraper.job_parser import parse_job_description
from job_scraper.recruiter_scraper import fetch_recruiter_info_sync, format_company_info_as_markdown
from job_scraper.recruiter_profile_scraper import fetch_recruiter_profile_sync, format_recruiter_profile_as_markdown
from matching_engine.matcher import match_cv_to_job
from matching_engine.prompt_generator import generate_cover_letter, generate_message

# Load environment variables
load_dotenv()
API_KEY = os.getenv("OPENAI_API_KEY")

def load_css():
    """Load custom CSS for professional styling"""
    css_file = Path("assets/style.css")
    if css_file.exists():
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        # Fallback inline CSS if file doesn't exist
        st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary-color: #2563eb;
            --primary-dark: #1d4ed8;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --error-color: #ef4444;
            --background-color: #f8fafc;
            --surface-color: #ffffff;
            --text-primary: #1e293b;
            --border-radius: 12px;
            --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
        }
        
        * { font-family: 'Inter', sans-serif; }
        
        .main .block-container {
            max-width: 1400px;
            padding: 2rem 1rem;
            background: linear-gradient(135deg, var(--background-color) 0%, #ffffff 100%);
        }
        
        .stButton > button {
            background: linear-gradient(135deg, var(--primary-color), var(--primary-dark));
            color: white;
            border: none;
            border-radius: var(--border-radius);
            padding: 0.75rem 1.5rem;
            font-weight: 500;
            transition: all 0.3s ease;
            width: 100%;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md);
        }
        </style>
        """, unsafe_allow_html=True)

def init_session_state():
    """Initialize all session state variables"""
    default_states = {
        'cv_struct': None,
        'job_struct': None,
        'company_info': None,
        'recruiter_profile': None,
        'match_results': None,
        'cover_letter': None,
        'recruiter_message': None,
        'job_manual_required': False,
        'company_manual_required': False,
        'recruiter_manual_required': False,
        'manual_job_text': None,
        'manual_company_text': None,
        'manual_recruiter_text': None,
        'analysis_step': 'upload'  # Track current step
    }
    
    for key, default_value in default_states.items():
        if key not in st.session_state:
            st.session_state[key] = default_value

def render_header():
    """Render the application header"""
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="background: linear-gradient(135deg, #2563eb, #1d4ed8); 
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                   font-size: 3rem; font-weight: 700; margin-bottom: 0.5rem;">
            🧭 Recruiter Agent Pro
        </h1>
        <p style="color: #64748b; font-size: 1.2rem; margin-bottom: 0;">
            AI-Powered Job Matching & Communication Generator
        </p>
    </div>
    """, unsafe_allow_html=True)

def render_progress_indicator():
    """Render progress indicator based on current step"""
    steps = [
        ("📄", "Upload CV", st.session_state.cv_struct is not None),
        ("🔍", "Job Analysis", st.session_state.job_struct is not None),
        ("🏢", "Company Info", st.session_state.company_info is not None or not st.session_state.get('company_url')),
        ("👤", "Recruiter", st.session_state.recruiter_profile is not None or not st.session_state.get('recruiter_url')),
        ("📊", "Matching", st.session_state.match_results is not None),
        ("✉️", "Generate", st.session_state.cover_letter is not None or st.session_state.recruiter_message is not None)
    ]
    
    cols = st.columns(len(steps))
    for i, (icon, label, completed) in enumerate(steps):
        with cols[i]:
            status_class = "✅" if completed else "⏳"
            st.markdown(f"""
            <div style="text-align: center; padding: 1rem; 
                        background: {'#f0f9ff' if completed else '#f8fafc'}; 
                        border-radius: 8px; margin-bottom: 1rem;">
                <div style="font-size: 1.5rem;">{icon}</div>
                <div style="font-size: 0.85rem; font-weight: 500; color: #64748b;">{label}</div>
                <div style="font-size: 1rem;">{status_class}</div>
            </div>
            """, unsafe_allow_html=True)

def render_input_section():
    """Render the input section with improved UX"""
    with st.container():
        st.markdown("## 📋 Step 1: Upload & Configure")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # File upload
            st.markdown("### 📄 Upload Your CV")
            cv_file = st.file_uploader(
                "Choose your CV file", 
                type=["pdf", "tex", "docx"],
                help="Supported formats: PDF, LaTeX (.tex), Word (.docx)"
            )
            
            # URLs input
            st.markdown("### 🔗 LinkedIn URLs")
            job_url = st.text_input(
                "Job URL (Required)", 
                placeholder="https://linkedin.com/jobs/view/...",
                help="Copy the LinkedIn job posting URL"
            )
            
            company_url = st.text_input(
                "Company URL (Optional)", 
                placeholder="https://linkedin.com/company/...",
                help="Company LinkedIn page for additional context"
            )
            
            recruiter_url = st.text_input(
                "Recruiter Profile URL (Optional)", 
                placeholder="https://linkedin.com/in/...",
                help="Recruiter's LinkedIn profile for personalized messages"
            )
        
        with col2:
            st.markdown("### ℹ️ Tips")
            st.info("""
            **For best results:**
            - Use a well-formatted CV
            - Ensure job URL is accessible
            - Add company & recruiter URLs for personalization
            - Check that you're not logged into LinkedIn in the same browser
            """)
            
            if cv_file and job_url:
                st.success("✅ Ready to analyze!")
            else:
                st.warning("⚠️ CV and Job URL required")
        
        return cv_file, job_url, company_url, recruiter_url

def render_manual_input_sections():
    """Render manual input sections when scraping fails"""
    if st.session_state.get('job_manual_required', False):
        with st.expander("⚠️ Manual Job Description Required", expanded=True):
            st.warning("Job scraping failed. Please paste the job description manually:")
            manual_job_text = st.text_area(
                "Job Description", 
                height=200, 
                key="manual_job_input",
                placeholder="Paste the complete job description here..."
            )
            if st.button("Parse Job Description", key="parse_job"):
                if manual_job_text.strip():
                    st.session_state.manual_job_text = manual_job_text
                    st.session_state.job_manual_required = False
                    st.rerun()
                else:
                    st.error("Please enter a job description")
    
    if st.session_state.get('company_manual_required', False):
        with st.expander("⚠️ Manual Company Information", expanded=False):
            st.warning("Company scraping failed. You can provide company information manually:")
            manual_company_text = st.text_area(
                "Company Information", 
                height=150, 
                key="manual_company_input",
                placeholder="Paste company description, size, industry, etc."
            )
            if st.button("Parse Company Information", key="parse_company"):
                if manual_company_text.strip():
                    st.session_state.manual_company_text = manual_company_text
                    st.session_state.company_manual_required = False
                    st.rerun()
    
    if st.session_state.get('recruiter_manual_required', False):
        with st.expander("⚠️ Manual Recruiter Profile", expanded=False):
            st.warning("Recruiter profile scraping failed. You can provide recruiter information manually:")
            manual_recruiter_text = st.text_area(
                "Recruiter Profile Information", 
                height=150, 
                key="manual_recruiter_input",
                placeholder="Paste recruiter's name, position, background, specializations..."
            )
            if st.button("Parse Recruiter Profile", key="parse_recruiter"):
                if manual_recruiter_text.strip():
                    st.session_state.manual_recruiter_text = manual_recruiter_text
                    st.session_state.recruiter_manual_required = False
                    st.rerun()

def process_cv(cv_file):
    """Process CV file and return structured data"""
    try:
        file_name = cv_file.name
        with NamedTemporaryFile(suffix=file_name) as tmp:
            tmp.write(cv_file.getbuffer())
            tmp.flush()
            cv_text = read_cv(tmp.name)
        return structure_cv(cv_text, api_key=API_KEY)
    except Exception as e:
        st.error(f"Error processing CV: {str(e)}")
        return None

def process_job(job_url):
    """Process job URL and return structured data"""
    try:
        manual_job_text = st.session_state.get('manual_job_text', None)
        job_raw = fetch_linkedin_job_sync(job_url, manual_job_text)
        
        if job_raw.get('error') == 'MANUAL_INPUT_REQUIRED':
            st.session_state.job_manual_required = True
            st.error(f"Job scraping failed: {job_raw.get('original_error', 'Unknown error')}")
            st.info("Please provide the job description manually above.")
            return None
        
        return parse_job_description(job_raw["markdown"])
    except Exception as e:
        st.error(f"Error processing job: {str(e)}")
        return None

def process_company(company_url):
    """Process company URL and return data"""
    if not company_url:
        return None
        
    try:
        manual_company_text = st.session_state.get('manual_company_text', None)
        company_raw = fetch_recruiter_info_sync(company_url, manual_company_text)
        
        if company_raw.get('error') == 'MANUAL_INPUT_REQUIRED':
            st.session_state.company_manual_required = True
            st.warning(f"Company scraping failed: {company_raw.get('original_error', 'Unknown error')}")
            return None
        
        return company_raw
    except Exception as e:
        st.warning(f"Error processing company: {str(e)}")
        return None

def process_recruiter(recruiter_url):
    """Process recruiter URL and return data"""
    if not recruiter_url:
        return None
        
    try:
        manual_recruiter_text = st.session_state.get('manual_recruiter_text', None)
        recruiter_raw = fetch_recruiter_profile_sync(recruiter_url, manual_recruiter_text)
        
        if recruiter_raw.get('error') == 'MANUAL_INPUT_REQUIRED':
            st.session_state.recruiter_manual_required = True
            st.warning(f"Recruiter profile scraping failed: {recruiter_raw.get('original_error', 'Unknown error')}")
            return None
        
        return recruiter_raw
    except Exception as e:
        st.warning(f"Error processing recruiter: {str(e)}")
        return None

def render_results():
    """Render analysis results in an organized way"""
    if not (st.session_state.cv_struct and st.session_state.job_struct):
        return
    
    st.markdown("## 📊 Analysis Results")
    
    # Results tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 CV", "💼 Job", "🏢 Company", "👤 Recruiter", "🔍 Match"])
    
    with tab1:
        st.markdown("### Parsed CV Structure")
        st.json(st.session_state.cv_struct, expanded=False)
    
    with tab2:
        st.markdown("### Job Requirements")
        st.json(st.session_state.job_struct, expanded=False)
    
    with tab3:
        if st.session_state.company_info:
            if st.session_state.company_info.get('error') and st.session_state.company_info.get('error') != 'MANUAL_INPUT_REQUIRED':
                st.error(f"Error: {st.session_state.company_info['error']}")
            else:
                formatted_company_info = format_company_info_as_markdown(st.session_state.company_info)
                st.markdown(formatted_company_info)
        else:
            st.info("No company information provided")
    
    with tab4:
        if st.session_state.recruiter_profile:
            if st.session_state.recruiter_profile.get('error') and st.session_state.recruiter_profile.get('error') != 'MANUAL_INPUT_REQUIRED':
                st.error(f"Error: {st.session_state.recruiter_profile['error']}")
            else:
                formatted_recruiter_info = format_recruiter_profile_as_markdown(st.session_state.recruiter_profile)
                st.markdown(formatted_recruiter_info)
        else:
            st.info("No recruiter profile provided")
    
    with tab5:
        if st.session_state.match_results:
            st.json(st.session_state.match_results, expanded=True)
        else:
            st.info("Run analysis to see match results")

def render_communication_section():
    """Render communication generation section"""
    if not (st.session_state.cv_struct and st.session_state.job_struct):
        return
    
    st.markdown("## ✉️ Generate Professional Communications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📝 Cover Letter")
        if st.button("Generate Cover Letter", key="generate_cover", type="primary"):
            with st.spinner("Crafting your cover letter..."):
                st.session_state.cover_letter = generate_cover_letter(
                    st.session_state.cv_struct, 
                    st.session_state.job_struct
                )
        
        if st.session_state.cover_letter:
            st.text_area(
                "Cover Letter", 
                st.session_state.cover_letter, 
                height=300, 
                key="cover_display"
            )
            st.download_button(
                "📥 Download Cover Letter", 
                data=st.session_state.cover_letter, 
                file_name="cover_letter.txt",
                key="download_cover",
                type="secondary"
            )
    
    with col2:
        st.markdown("### 💬 Recruiter Message")
        if st.button("Generate Recruiter Message", key="generate_message", type="primary"):
            with st.spinner("Crafting your recruiter message..."):
                company_context = ""
                if st.session_state.company_info and not st.session_state.company_info.get('error'):
                    company_context = format_company_info_as_markdown(st.session_state.company_info)
                
                recruiter_context = ""
                if st.session_state.recruiter_profile and not st.session_state.recruiter_profile.get('error'):
                    recruiter_context = format_recruiter_profile_as_markdown(st.session_state.recruiter_profile)
                
                st.session_state.recruiter_message = generate_message(
                    st.session_state.cv_struct, 
                    st.session_state.job_struct, 
                    company_context=company_context,
                    recruiter_context=recruiter_context
                )
        
        if st.session_state.recruiter_message:
            st.text_area(
                "Recruiter Message", 
                st.session_state.recruiter_message, 
                height=300, 
                key="message_display"
            )
            st.download_button(
                "📥 Download Message", 
                data=st.session_state.recruiter_message, 
                file_name="recruiter_message.txt",
                key="download_message",
                type="secondary"
            )

def main():
    """Main application function"""
    # Page config
    st.set_page_config(
        page_title="Recruiter Agent Pro", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Load CSS and initialize
    load_css()
    init_session_state()
    
    # Render UI
    render_header()
    render_progress_indicator()
    
    # Main content
    cv_file, job_url, company_url, recruiter_url = render_input_section()
    
    # Store URLs in session state for access in other functions
    st.session_state.company_url = company_url
    st.session_state.recruiter_url = recruiter_url
    
    # Manual input sections
    render_manual_input_sections()
    
    # Analysis button
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start Analysis", key="analyze", type="primary"):
            if not cv_file or not job_url:
                st.error("Please upload a CV and enter a LinkedIn job URL.")
                st.stop()
            
            # Clear previous results
            for key in ['cv_struct', 'job_struct', 'company_info', 'recruiter_profile', 'match_results', 'cover_letter', 'recruiter_message']:
                st.session_state[key] = None
            
            # Process each component
            progress_bar = st.progress(0)
            
            # CV Processing
            with st.spinner("📄 Processing CV..."):
                st.session_state.cv_struct = process_cv(cv_file)
                progress_bar.progress(20)
            
            if not st.session_state.cv_struct:
                st.stop()
            
            # Job Processing
            with st.spinner("💼 Analyzing job posting..."):
                st.session_state.job_struct = process_job(job_url)
                progress_bar.progress(40)
            
            if not st.session_state.job_struct:
                st.stop()
            
            # Company Processing
            if company_url:
                with st.spinner("🏢 Gathering company insights..."):
                    st.session_state.company_info = process_company(company_url)
                    progress_bar.progress(60)
            
            # Recruiter Processing
            if recruiter_url:
                with st.spinner("👤 Analyzing recruiter profile..."):
                    st.session_state.recruiter_profile = process_recruiter(recruiter_url)
                    progress_bar.progress(80)
            
            # Matching
            with st.spinner("🔍 Calculating match score..."):
                st.session_state.match_results = match_cv_to_job(
                    st.session_state.cv_struct, 
                    st.session_state.job_struct
                )
                progress_bar.progress(100)
            
            st.success("✅ Analysis complete!")
            st.balloons()
    
    # Render results and communication sections
    render_results()
    render_communication_section()
    
    # Footer
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔄 Reset All Data", key="reset"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

if __name__ == "__main__":
    main()