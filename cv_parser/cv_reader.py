
import os

def read_pdf(file_path):
    import fitz  # PyMuPDF, install with: pip install pymupdf
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    return text

def read_latex(file_path):
    """
    Very simple: Strips LaTeX commands and extracts main text.
    This can be enhanced using textract or custom logic.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    # Remove lines starting with % (comments) and LaTeX commands
    content = []
    for line in lines:
        line = line.strip()
        if line.startswith('%') or line.startswith('\\'):
            continue
        # Strip out inline LaTeX commands (e.g. \textbf{...})
        line = remove_latex_commands(line)
        if line:
            content.append(line)
    return "\n".join(content)

def remove_latex_commands(line):
    import re
    # Remove simple LaTeX commands (not bulletproof, but works for most resumes)
    line = re.sub(r'\\[a-zA-Z]+\{([^}]*)\}', r'\1', line)
    line = re.sub(r'\\[a-zA-Z]+', '', line)
    return line

def read_cv(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".pdf":
        return read_pdf(file_path)
    elif ext in [".tex", ".latex"]:
        return read_latex(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
    
def read_docx(file_path):
    from docx import Document  # pip install python-docx
    doc = Document(file_path)
    text = "\n".join([para.text for para in doc.paragraphs])
    return text

def read_cv(file_path):
    ext = os.path.splitext(file_path)[-1].lower()
    if ext == ".pdf":
        return read_pdf(file_path)
    elif ext in [".tex", ".latex"]:
        return read_latex(file_path)
    elif ext == ".docx":
        return read_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")