from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import json
import re
from config import settings

def parse_recruiter_profile(recruiter_markdown: str, model: str = "gpt-4o-mini") -> dict:
    """
    Convert a recruiter profile into structured JSON:
    -> name, position, company, location, specializations, experience, approach, etc.
    Uses OpenAI API key from config.py
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0
    )
    
    system_prompt = """You are an expert recruiter profile analyzer. Extract structured data from LinkedIn recruiter profiles. 
    Always return valid JSON without markdown formatting. Focus on professional recruiting context."""
    
    user_prompt = f"""
Analyze this recruiter's LinkedIn profile and extract the following fields in JSON format:

- recruiter_name (string): Full name
- current_position (string): Job title/role
- current_company (string): Current employer
- location (string): Geographic location
- years_experience (string): Years in recruiting (e.g., "5+ years", "10+ years")
- specializations (list): Areas of recruiting expertise (e.g., ["Tech Recruiting", "Executive Search"])
- industry_focus (list): Industries they recruit for (e.g., ["Technology", "Healthcare"])
- education (string): Educational background if mentioned
- recruiting_approach (string): Their recruiting philosophy/methodology if described
- notable_achievements (list): Any mentioned accomplishments or metrics
- contact_preferences (list): Preferred ways to be contacted if mentioned
- personality_traits (list): Professional characteristics (e.g., ["Detail-oriented", "Relationship-focused"])

IMPORTANT: 
- Return ONLY the JSON object, no markdown formatting, no code blocks, no extra text
- If information is not available, use "Not specified" for strings and empty arrays [] for lists
- Extract implied information where reasonable (e.g., "Senior" in title suggests experience level)
- Focus on recruiting-relevant information

Recruiter profile content:
----
{recruiter_markdown}
----
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm(messages)
        content = response.content.strip()
        
        # Remove markdown code blocks if present
        content = clean_json_response(content)
        
        # Parse and validate the JSON
        parsed_data = json.loads(content)
        
        # Ensure all required fields exist with defaults
        validated_data = validate_recruiter_data(parsed_data)
        
        return validated_data
        
    except json.JSONDecodeError as e:
        return {
            "error": "failed to parse JSON", 
            "raw": content,
            "json_error": str(e)
        }
    except Exception as e:
        return {
            "error": "API call failed", 
            "details": str(e)
        }

def validate_recruiter_data(data: dict) -> dict:
    """
    Ensure recruiter data has all required fields with proper defaults
    """
    required_fields = {
        "recruiter_name": "Recruiter",
        "current_position": "Talent Acquisition Specialist", 
        "current_company": "Not specified",
        "location": "Not specified",
        "years_experience": "Not specified",
        "specializations": [],
        "industry_focus": [],
        "education": "Not specified",
        "recruiting_approach": "Not specified",
        "notable_achievements": [],
        "contact_preferences": [],
        "personality_traits": []
    }
    
    # Fill in missing fields with defaults
    for field, default_value in required_fields.items():
        if field not in data or data[field] is None:
            data[field] = default_value
        
        # Convert empty strings to defaults for string fields
        if isinstance(default_value, str) and data[field] == "":
            data[field] = default_value
            
        # Ensure lists are actually lists
        if isinstance(default_value, list) and not isinstance(data[field], list):
            if isinstance(data[field], str) and data[field] != "Not specified":
                # Convert string to single-item list
                data[field] = [data[field]]
            else:
                data[field] = default_value
    
    # Clean up list items
    for list_field in ["specializations", "industry_focus", "notable_achievements", "contact_preferences", "personality_traits"]:
        if isinstance(data[list_field], list):
            # Remove empty strings and None values
            data[list_field] = [item for item in data[list_field] if item and str(item).strip()]
            # Limit to reasonable number of items
            data[list_field] = data[list_field][:5]
    
    return data

def clean_json_response(content: str) -> str:
    """
    Clean JSON response by removing markdown code blocks and extra formatting
    """
    # Remove markdown code blocks
    content = re.sub(r'```json\s*', '', content)
    content = re.sub(r'```\s*', '', content)
    
    # Remove any leading/trailing whitespace
    content = content.strip()
    
    # If content starts with text before JSON, try to extract JSON
    json_match = re.search(r'\{.*\}', content, re.DOTALL)
    if json_match:
        content = json_match.group(0)
    
    return content

def enhance_recruiter_data_with_insights(recruiter_data: dict, job_context: dict = None) -> dict:
    """
    Add AI-generated insights about the recruiter for better personalization
    """
    if recruiter_data.get('error'):
        return recruiter_data
    
    # Generate personalization insights
    insights = generate_recruiter_insights(recruiter_data, job_context)
    recruiter_data['personalization_insights'] = insights
    
    return recruiter_data

def generate_recruiter_insights(recruiter_data: dict, job_context: dict = None) -> dict:
    """
    Generate actionable insights for personalizing communication with the recruiter
    """
    insights = {
        "communication_style": "professional",
        "key_talking_points": [],
        "personalization_hooks": [],
        "approach_recommendations": []
    }
    
    # Analyze experience level
    experience = recruiter_data.get('years_experience', '')
    if any(term in experience.lower() for term in ['senior', '10+', 'lead', 'principal']):
        insights["communication_style"] = "executive"
        insights["approach_recommendations"].append("Reference industry trends and strategic recruiting challenges")
    elif any(term in experience.lower() for term in ['junior', '1-3', 'associate']):
        insights["communication_style"] = "enthusiastic"
        insights["approach_recommendations"].append("Show appreciation for their growing expertise")
    
    # Analyze specializations for talking points
    specializations = recruiter_data.get('specializations', [])
    for spec in specializations:
        if 'tech' in spec.lower():
            insights["key_talking_points"].append("Technical skills alignment")
        if 'executive' in spec.lower():
            insights["key_talking_points"].append("Leadership experience")
        if 'startup' in spec.lower():
            insights["key_talking_points"].append("Entrepreneurial mindset")
    
    # Company-based personalization hooks
    company = recruiter_data.get('current_company', '')
    if company and company != "Not specified":
        insights["personalization_hooks"].append(f"Knowledge of {company}'s recruiting needs")
    
    # Location-based insights
    location = recruiter_data.get('location', '')
    if location and location != "Not specified":
        insights["personalization_hooks"].append(f"Familiarity with {location} market")
    
    return insights

def format_recruiter_summary(recruiter_data: dict) -> str:
    """
    Create a human-readable summary of the recruiter profile
    """
    if recruiter_data.get('error'):
        return f"Error parsing recruiter profile: {recruiter_data.get('error', 'Unknown error')}"
    
    name = recruiter_data.get('recruiter_name', 'Recruiter')
    position = recruiter_data.get('current_position', 'Recruiter')
    company = recruiter_data.get('current_company', 'Unknown Company')
    experience = recruiter_data.get('years_experience', 'Unknown experience')
    specializations = recruiter_data.get('specializations', [])
    
    summary = f"""
**{name}**
*{position} at {company}*

**Experience:** {experience}
**Specializations:** {', '.join(specializations) if specializations else 'General recruiting'}
**Location:** {recruiter_data.get('location', 'Not specified')}

**Recruiting Focus:** {', '.join(recruiter_data.get('industry_focus', [])) if recruiter_data.get('industry_focus') else 'Various industries'}
"""
    
    if recruiter_data.get('recruiting_approach') and recruiter_data['recruiting_approach'] != "Not specified":
        summary += f"\n**Approach:** {recruiter_data['recruiting_approach']}"
    
    if recruiter_data.get('personalization_insights'):
        insights = recruiter_data['personalization_insights']
        if insights.get('key_talking_points'):
            summary += f"\n\n**Key Discussion Points:** {', '.join(insights['key_talking_points'])}"
    
    return summary.strip()

# Example usage and testing function
def test_recruiter_parser():
    """Test function to validate the recruiter parser"""
    sample_markdown = """
    # Sarah Johnson | LinkedIn

    Senior Technical Recruiter at Google
    San Francisco Bay Area · 500+ connections

    ## About
    Passionate technical recruiter with 8+ years of experience building world-class engineering teams. 
    I specialize in full-stack development, machine learning, and senior engineering leadership roles.
    
    My approach focuses on understanding both technical requirements and cultural fit. I believe in 
    transparent communication and building long-term relationships with candidates.

    ## Experience
    **Senior Technical Recruiter** - Google (2021-Present)
    - Lead recruiting for ML and AI teams
    - Achieved 95% offer acceptance rate
    - Built diverse engineering teams across 5 product areas

    **Technical Recruiter** - Stripe (2019-2021)
    - Focused on backend and infrastructure engineering
    - Reduced time-to-hire by 30%

    ## Education
    Bachelor's Degree in Psychology - UC Berkeley
    """
    
    result = parse_recruiter_profile(sample_markdown)
    print("Parsed Recruiter Data:")
    print(json.dumps(result, indent=2))
    
    summary = format_recruiter_summary(result)
    print("\nFormatted Summary:")
    print(summary)

if __name__ == "__main__":
    test_recruiter_parser()