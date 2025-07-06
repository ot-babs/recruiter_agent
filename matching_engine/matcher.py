from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import json
from config import settings

def match_cv_to_job(cv_dict: dict, job_dict: dict, model: str = "gpt-4.1-mini") -> dict:
    """
    Leverage LLM to compare CV and job and return structured match info.
    Uses OpenAI API key from config.py
    """
    llm = ChatOpenAI(
        openai_api_key=settings.OPENAI_API_KEY,
        model=model,
        temperature=0
    )

    system_prompt = "You are a helpful assistant for evaluating CV-job fit."
    
    user_prompt = f"""
You are a recruiter AI assistant. Compare this candidate CV and a job description, and provide:

1. overall_match_score: 0–100
2. strengths: list of 3 aligned skills/experience
3. weaknesses: list of 3 missing or weak areas (optional)
4. summary: 2–3 sentences explaining the match

Respond in JSON:

CV JSON:
{json.dumps(cv_dict, indent=2)}

Job JSON:
{json.dumps(job_dict, indent=2)}
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        response = llm(messages)
        txt = response.content.strip()
        return json.loads(txt)
    except json.JSONDecodeError:
        return {"error": "invalid-json", "raw": txt}
    except Exception as e:
        return {"error": "API call failed", "details": str(e)}