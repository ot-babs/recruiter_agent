from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import json
import re
from config import settings

def parse_job_description(job_markdown: str, model: str = "gpt-4.1-mini") -> dict:
    """
    Convert a job description into a structured JSON:
    -> title, responsibilities, requirements, location, seniority, skills.
    Uses OpenAI API key from config.py
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0
    )
    
    system_prompt = "You are a parser extracting structured data from job postings. Always return valid JSON without markdown formatting."
    
    user_prompt = f"""
You are a skilled job-ad parser. Given the following job description in markdown format, extract the following fields in JSON:
- title
- company
- location
- seniority_level
- responsibilities (list)
- requirements (list)
- key_skills (list)

IMPORTANT: Return ONLY the JSON object, no markdown formatting, no code blocks, no extra text.

Job description:
----
{job_markdown}
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
        
        return json.loads(content)
    except json.JSONDecodeError:
        return {"error": "failed to parse JSON", "raw": content}
    except Exception as e:
        return {"error": "API call failed", "details": str(e)}

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