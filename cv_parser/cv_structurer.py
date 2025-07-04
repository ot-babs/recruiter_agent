
import json

def structure_cv(cv_text, api_key=None, model="gpt-3.5-turbo"):
    """
    Parse the CV into sections using either OpenAI LLM (if api_key) or fallback regex method.
    Returns a dict: {section: content}
    """
    if api_key:
        structured = structure_with_llm(cv_text, api_key, model)
    return structured

def structure_with_llm(cv_text, api_key, model):
    import openai
    import json
    openai.api_key = api_key

    prompt = f"""
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

    response = openai.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "You are a helpful assistant that extracts structured information from CVs in any format."},
                  {"role": "user", "content": prompt}],
        temperature=0
    )
    text_response = response.choices[0].message.content.strip()
    try:
        return json.loads(text_response)
    except Exception:
        return {"llm_raw": text_response}