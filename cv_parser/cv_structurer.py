from langchain_openai import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage
import json
from config import settings

def structure_cv(cv_text, api_key=None, model="gpt-4.1-mini"):
    """
    Parse the CV into sections using either OpenAI LLM (if api_key) or fallback regex method.
    Returns a dict: {section: content}
    """
    if api_key or settings.OPENAI_API_KEY:
        structured = structure_with_llm(cv_text, api_key or settings.OPENAI_API_KEY, model)
    return structured

def structure_with_llm(cv_text, api_key, model):
    """
    Structure CV using LangChain ChatOpenAI
    """
    llm = ChatOpenAI(
        openai_api_key=api_key,
        model=model,
        temperature=0
    )

    system_prompt = "You are a helpful assistant that extracts structured information from CVs in any format."
    
    user_prompt = f"""
You are an expert CV information extractor. Given ANY CV text—regardless of format, order, or section headings—extract and return a JSON object with these standardized keys:

- professional_summary
- education
- experience
- technical_skills
- projects
- certifications

For each, extract the content even if the CV uses different headings (e.g. 'Summary', 'Background', 'Career History', 'Skills & Tools', 'Employment', 'Learning', etc.) or has the content mixed in bullet points, paragraphs, or tables.

If information is missing for a section, return an empty string for that section.

Return only a clean JSON object as your response. Do NOT include any explanation or commentary.

CV TEXT:
-----
{cv_text}
-----
"""

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt)
    ]
    
    try:
        # Use invoke instead of __call__ to fix deprecation warning
        response = llm.invoke(messages)
        text_response = response.content.strip()
        return json.loads(text_response)
    except json.JSONDecodeError:
        return {"llm_raw": text_response}
    except Exception as e:
        return {"error": str(e)}