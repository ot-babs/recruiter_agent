from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from config import settings

def generate_cover_letter(cv_dict: dict, job_dict: dict, tone: str = "professional", model: str = "gpt-4o-mini") -> str:
    """
    Generate a customized cover letter for a candidate.
    Uses OpenAI API key from config.py
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.7
    )

    system_prompt = "You are a professional cover letter writer who crafts compelling, personalized cover letters that highlight candidate strengths and demonstrate clear fit for specific roles."
    
    user_prompt = f"""
Write a professional one-page cover letter for this candidate applying to the specified job position.

CANDIDATE PROFILE:
{cv_dict}

JOB POSITION:
{job_dict}

REQUIREMENTS:
- Use a {tone} tone throughout
- Structure: compelling opening, 2-3 body paragraphs showing fit, strong closing
- Highlight specific achievements that match job requirements
- Show genuine enthusiasm for the role and company
- Include quantifiable results where possible
- Keep it concise but impactful (300-400 words)
- Avoid generic phrases and make it highly personalized

Cover Letter:
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm(messages)
        return response.content.strip()
    except Exception as e:
        return f"Error generating cover letter: {str(e)}"

def generate_message(cv_dict: dict, job_dict: dict, company_context: str = "", tone: str = "concise", model: str = "gpt-4o-mini") -> str:
    """
    Generate a recruiter outreach message with optional company context.
    Uses OpenAI API key from config.py
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.7
    )

    system_prompt = "You write personalized, compelling recruiter outreach messages that grab attention and demonstrate clear value proposition."
    
    # Build company context section
    company_section = ""
    if company_context and company_context.strip():
        company_section = f"""
COMPANY CONTEXT:
{company_context[:800]}  # Limit to avoid token overflow
"""

    user_prompt = f"""
Write a professional LinkedIn message from a candidate to a recruiter expressing interest in the job position.

CANDIDATE PROFILE:
Professional Summary: {cv_dict.get('professional_summary', 'Not provided')}
Key Skills: {cv_dict.get('skills', [])}
Experience: {cv_dict.get('experience', [])}

JOB POSITION:
{job_dict}
{company_section}

REQUIREMENTS:
- Tone: {tone}
- Length: 150-200 words (LinkedIn message length)
- Start with a personalized greeting referencing specific role
- Highlight 2-3 key strengths that directly match job requirements
- Use specific examples or achievements from their background
- Show knowledge of the company (if company context provided)
- Include clear call-to-action
- Be conversational yet professional
- Focus on value proposition - what they bring to the role

Message:
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm(messages)
        return response.content.strip()
    except Exception as e:
        return f"Error generating message: {str(e)}"

def generate_custom_prompt(cv_dict: dict, job_dict: dict, custom_request: str, company_context: str = "", model: str = "gpt-4o-mini") -> str:
    """
    Generate content based on custom user request.
    Flexible function for any custom prompts related to job applications.
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.7
    )

    system_prompt = "You are a professional career advisor and content creator specializing in job applications and career development."
    
    # Build company context section
    company_section = ""
    if company_context and company_context.strip():
        company_section = f"""
COMPANY CONTEXT:
{company_context[:800]}
"""

    user_prompt = f"""
CANDIDATE PROFILE:
{cv_dict}

JOB POSITION:
{job_dict}
{company_section}

CUSTOM REQUEST:
{custom_request}

Please fulfill the custom request using the candidate and job information provided:
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm(messages)
        return response.content.strip()
    except Exception as e:
        return f"Error generating custom content: {str(e)}"