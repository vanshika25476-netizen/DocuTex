from docx import Document
from docx.opc.exceptions import PackageNotFoundError
from zipfile import BadZipFile, ZipFile


REQUIRED_DOCX_PARTS = {'word/document.xml', '[Content_Types].xml'}


def escape_latex(text):
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(char, char) for char in text)


def convert_docx_to_latex(file_path):
    try:
        with ZipFile(file_path) as archive:
            names = set(archive.namelist())
            if not REQUIRED_DOCX_PARTS.issubset(names):
                raise ValueError('Invalid DOCX package')
    except (BadZipFile, OSError) as exc:
        raise ValueError('Invalid DOCX package') from exc

    try:
        doc = Document(file_path)
    except (BadZipFile, PackageNotFoundError, ValueError, OSError) as exc:
        raise ValueError('Invalid DOCX document') from exc

    lines = []
    in_bullets = False

    for paragraph in doc.paragraphs:
        text = (paragraph.text or '').strip()

        if not text:
            continue

        try:
            style = (paragraph.style.name or '').lower()
        except (AttributeError, KeyError):
            style = ''
        is_bullet = "list bullet" in style or "bullet" in style


        if is_bullet:
            if not in_bullets:
                lines.append("\\begin{itemize}\n")
                in_bullets = True
        elif in_bullets:
            lines.append("\\end{itemize}\n\n")
            in_bullets = False

        parts = []
        for run in paragraph.runs:
            run_text = escape_latex(run.text)
            if run.bold and run_text:
                run_text = r"\textbf{" + run_text + "}"
            parts.append(run_text)

        converted_text = "".join(parts).strip()

        if not converted_text:
            continue

        if "heading 1" in style:
            lines.append(f"\\section{{{converted_text}}}\n\n")
        elif "heading 2" in style:
            lines.append(f"\\subsection{{{converted_text}}}\n\n")
        elif "heading 3" in style:
            lines.append(f"\\subsubsection{{{converted_text}}}\n\n")
        elif is_bullet:
            lines.append(f"\\item {converted_text}\n")
        else:
            lines.append(converted_text + "\n\n")

    if in_bullets:
        lines.append("\\end{itemize}\n\n")

    return (
        "\\documentclass{article}\n"
        "\\begin{document}\n\n"
        + "".join(lines)
        + "\\end{document}\n"
    )
