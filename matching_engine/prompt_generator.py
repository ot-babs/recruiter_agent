from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
from config import settings
import json

def analyze_rice_factors_llm(cv_dict: dict, job_dict: dict, company_context: str = "", recruiter_context: str = "", model: str = "gpt-4o-mini") -> dict:
    """
    Use LLM to dynamically analyze RICE factors based on specific context
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.3  # Lower temperature for more consistent analysis
    )

    system_prompt = """You are an expert in human psychology and persuasion, specifically trained in the RICE methodology (Reward, Ideology, Coercion, Ego) used by intelligence agencies to understand and influence motivation.

RICE Framework:
- REWARD: What the person desires (recognition, money, success, solutions to problems)
- IDEOLOGY: Core beliefs, values, and principles that drive them
- COERCION: Fears, pressures, or negative consequences they want to avoid
- EGO: How they see themselves, their professional identity, and what makes them feel important

Your task is to analyze the hiring manager/recruiter psychology and identify specific RICE factors that would be most relevant for this particular job application context."""

    user_prompt = f"""
Analyze this job application scenario and identify the key RICE factors that would motivate the hiring manager/recruiter to be interested in this candidate.

CANDIDATE PROFILE:
{cv_dict}

JOB POSITION:
{job_dict}

COMPANY CONTEXT:
{company_context if company_context else "No specific company context provided"}

RECRUITER PROFILE:
{recruiter_context if recruiter_context else "No specific recruiter context provided"}

Please analyze and return ONLY a JSON object with this structure:
{{
    "reward": ["specific reward 1", "specific reward 2", "specific reward 3"],
    "ideology": ["specific ideology 1", "specific ideology 2", "specific ideology 3"],
    "coercion": ["specific pressure/fear 1", "specific pressure/fear 2"],
    "ego": ["specific ego appeal 1", "specific ego appeal 2", "specific ego appeal 3"],
    "primary_motivation": "reward|ideology|coercion|ego",
    "key_insights": ["insight 1", "insight 2", "insight 3"]
}}

Focus on:
- What would THIS specific hiring manager/recruiter want most?
- What values does THIS company/role represent?
- What pressures does THIS hiring situation create?
- How does THIS recruiter see their professional identity?

Be specific to this context, not generic.
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm(messages)
        content = response.content.strip()
        
        # Clean JSON response
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()
        
        return json.loads(content)
    except Exception as e:
        # Fallback to basic structure if parsing fails
        return {
            "reward": ["Finding a qualified candidate", "Successful hire", "Meeting hiring goals"],
            "ideology": ["Quality over quantity", "Cultural fit", "Professional excellence"],
            "coercion": ["Competitive job market", "Urgent hiring needs", "Missing good candidates"],
            "ego": ["Professional judgment", "Talent identification skills", "Industry expertise"],
            "primary_motivation": "reward",
            "key_insights": ["Standard hiring motivation", "Professional recruiting approach"]
        }

def generate_cover_letter(cv_dict: dict, job_dict: dict, company_context: str = "", tone: str = "professional", model: str = "gpt-4o-mini") -> str:
    """
    Generate a RICE-optimized cover letter using LLM analysis
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.7
    )

    # First, analyze RICE factors
    rice_analysis = analyze_rice_factors_llm(cv_dict, job_dict, company_context, "", model)

    system_prompt = """You are a master cover letter writer who understands the deep psychology of hiring managers. You use the RICE methodology (Reward, Ideology, Coercion, Ego) to craft letters that connect on multiple psychological levels.

Your expertise:
- Creating genuine emotional connection while remaining professional
- Weaving psychological triggers naturally into compelling narratives
- Balancing confidence with humility
- Making hiring managers feel smart for considering this candidate
- Building urgency without being pushy

You write cover letters that hiring managers actually want to read and that make them excited to meet the candidate."""
    
    user_prompt = f"""
Write a compelling cover letter that leverages the RICE psychological framework to maximize impact.

CANDIDATE PROFILE:
{cv_dict}

JOB POSITION:
{job_dict}

COMPANY CONTEXT:
{company_context if company_context else "Research the company independently"}

RICE PSYCHOLOGICAL ANALYSIS:
{json.dumps(rice_analysis, indent=2)}

REQUIREMENTS:
- Tone: {tone}
- Length: 300-400 words
- Structure: Hook opening, 2-3 body paragraphs, strong closing
- Integrate RICE factors naturally into the narrative
- Primary focus on the "{rice_analysis.get('primary_motivation', 'reward')}" motivation
- Include specific achievements that resonate with identified motivations
- Create subtle urgency and FOMO where appropriate
- Appeal to the hiring manager's professional judgment and expertise
- Make them feel this candidate aligns perfectly with their values
- Include quantifiable results that address their key rewards/concerns

PSYCHOLOGICAL INTEGRATION:
- REWARD: Demonstrate clear value and solutions to their problems
- IDEOLOGY: Show alignment with company values and professional principles
- COERCION: Create appropriate urgency and competitive pressure
- EGO: Appeal to their expertise in identifying exceptional talent

Make this feel personal, researched, and impossible to ignore. The hiring manager should feel compelled to interview this candidate.
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

def generate_message(cv_dict: dict, job_dict: dict, company_context: str = "", recruiter_context: str = "", tone: str = "professional", model: str = "gpt-4o-mini") -> str:
    """
    Generate a RICE-optimized recruiter message using enhanced recruiter data
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.7
    )

    # Analyze RICE factors including recruiter context
    rice_analysis = analyze_rice_factors_llm(cv_dict, job_dict, company_context, recruiter_context, model)

    system_prompt = """You are an expert at crafting irresistible recruiter outreach messages. You understand recruiter psychology deeply and know exactly what makes them want to respond and engage.

Your expertise:
- Understanding what recruiters value most in candidates
- Creating messages that stand out in crowded inboxes
- Building rapport quickly through genuine personalization
- Demonstrating candidate value while respecting recruiter expertise
- Making recruiters feel excited about presenting this candidate

You write messages that recruiters actually want to respond to and that make them look good to their clients/hiring managers."""

    user_prompt = f"""
Write a compelling LinkedIn message that uses RICE psychology to maximize recruiter engagement and response.

CANDIDATE PROFILE:
{cv_dict}

JOB POSITION:
{job_dict}

COMPANY CONTEXT:
{company_context if company_context else "No specific company context available"}

RECRUITER PROFILE & CONTEXT:
{recruiter_context if recruiter_context else "No specific recruiter context available"}

RICE PSYCHOLOGICAL ANALYSIS:
{json.dumps(rice_analysis, indent=2)}

REQUIREMENTS:
- Tone: {tone} but conversational
- Length: 150-200 words (LinkedIn message optimal length)
- Primary psychological focus: {rice_analysis.get('primary_motivation', 'reward')}
- Address recruiter by name if available in context
- Reference their specific expertise/specializations when possible
- Show you've researched both the role and their background
- Highlight 2-3 achievements that align with their RICE motivations
- Include subtle competitive pressure (other opportunities/interest)
- Make them feel smart for considering you
- End with clear but non-pushy call-to-action

PSYCHOLOGICAL INTEGRATION:
- REWARD: Show how you solve their hiring challenges and make them successful
- IDEOLOGY: Demonstrate alignment with their professional values and approach
- COERCION: Create gentle urgency around timing and market competition
- EGO: Appeal to their expertise in identifying exceptional talent

PERSONALIZATION FOCUS:
- If recruiter specializes in certain areas, connect your experience directly
- If they have industry focus, emphasize relevant background
- Reference their current company or achievements when appropriate
- Match communication style to their professional persona

Make this feel like you've done your homework and genuinely want to work with THIS specific recruiter, not just any recruiter.
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

def generate_custom_prompt(cv_dict: dict, job_dict: dict, custom_request: str, company_context: str = "", recruiter_context: str = "", model: str = "gpt-4o-mini") -> str:
    """
    Generate custom content using RICE methodology for any user request
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0.7
    )

    # Analyze RICE factors for context
    rice_analysis = analyze_rice_factors_llm(cv_dict, job_dict, company_context, recruiter_context, model)

    system_prompt = """You are a career strategy expert who understands the psychology of hiring and recruitment. You use the RICE methodology to create compelling career-related content that resonates with decision-makers."""
    
    user_prompt = f"""
Create content based on the custom request below, incorporating RICE psychological insights where relevant.

CANDIDATE PROFILE:
{cv_dict}

JOB POSITION:
{job_dict}

COMPANY CONTEXT:
{company_context if company_context else "No specific company context"}

RECRUITER CONTEXT:
{recruiter_context if recruiter_context else "No specific recruiter context"}

RICE ANALYSIS:
{json.dumps(rice_analysis, indent=2)}

CUSTOM REQUEST:
{custom_request}

Guidelines:
- Fulfill the custom request while leveraging psychological insights
- Consider the RICE motivations of the target audience
- Make the content compelling and action-oriented
- Ensure authenticity and professionalism
- Use specific details from the candidate and role context

Response:
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

def test_rice_analysis():
    """Test function to see RICE analysis in action"""
    sample_cv = {
        "professional_summary": "Senior Software Engineer with 8 years experience in AI/ML",
        "skills": ["Python", "Machine Learning", "AWS", "Team Leadership"],
        "experience": ["Led ML team of 5 engineers", "Deployed models serving 1M+ users"]
    }
    
    sample_job = {
        "title": "Senior ML Engineer",
        "company": "Google",
        "requirements": ["5+ years ML experience", "Python expertise", "Leadership skills"]
    }
    
    sample_recruiter = """
    Sarah Johnson - Senior Technical Recruiter at Google
    Specializes in AI/ML roles, 10+ years experience
    Focuses on senior engineering positions and cultural fit
    """
    
    rice_result = analyze_rice_factors_llm(sample_cv, sample_job, "", sample_recruiter)
    print("RICE Analysis Result:")
    print(json.dumps(rice_result, indent=2))

if __name__ == "__main__":
    test_rice_analysis()