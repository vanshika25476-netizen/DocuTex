# DocuTeX — A calmer way to write in LaTeX

DocuTeX converts Word documents into clean, editable LaTeX projects with a polished browser workflow.

## Contributors

- **Graphic Era University student**

## Features

- Drag-and-drop `.docx` upload with progress feedback
- Clear validation for unsupported, oversized, or invalid files
- Word document and generated LaTeX split preview
- Editable LaTeX output with refreshable preview
- Export as `.tex`, PDF, or ZIP project
- Sample document for first-time users
- Conversion history with download and delete actions
- Responsive mobile layout with preview tabs
- Dark and light theme support
- Keyboard-friendly upload flow and visible focus states

## Requirements

- Python 3.10+
- Flask
- `python-docx`
- Optional: a LaTeX compiler such as `pdflatex` for high-fidelity PDF export

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

## PDF export

When `pdflatex` is available on the server, DocuTex uses it to compile the generated LaTeX. If it is unavailable, the app provides a fallback PDF so the export action remains usable.

## Project structure

```text
.
├── app.py                 # Flask routes and export handling
├── converter.py           # DOCX to LaTeX conversion
├── templates/index.html   # Responsive application UI
└── uploads/               # Temporary uploaded files
```

## License

Add the project license here before public distribution.

---

Built with care by **Graphic Era University student**.
