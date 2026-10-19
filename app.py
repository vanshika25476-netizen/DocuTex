from flask import Flask, render_template, request, send_file, redirect, url_for
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge
from werkzeug.utils import secure_filename
from converter import convert_docx_to_latex
import io
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 25 * 1024 * 1024
history = []


def fallback_pdf(text):
    safe = text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    lines = safe.splitlines()[:48]
    content = 'BT /F1 9 Tf 48 760 Td ' + ' '.join(f'({line[:105]}) Tj 0 -14 Td' for line in lines) + ' ET'
    objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R] /Count 1 >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>', f'<< /Length {len(content.encode("latin-1", "replace"))} >>\nstream\n{content}\nendstream', '<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>']
    pdf = '%PDF-1.4\n'; offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf.encode('latin-1'))); pdf += f'{index} 0 obj\n{obj}\nendobj\n'
    xref = len(pdf.encode('latin-1')); pdf += 'xref\n0 6\n0000000000 65535 f \n' + ''.join(f'{offset:010d} 00000 n \n' for offset in offsets[1:])
    pdf += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'
    return pdf.encode('latin-1', 'replace')


def make_pdf(code):
    if shutil.which('pdflatex'):
        with tempfile.TemporaryDirectory() as folder:
            tex = os.path.join(folder, 'document.tex')
            open(tex, 'w', encoding='utf-8').write(code)
            result = subprocess.run(['pdflatex', '-interaction=nonstopmode', '-halt-on-error', 'document.tex'], cwd=folder, capture_output=True, timeout=30)
            pdf = os.path.join(folder, 'document.pdf')
            if result.returncode == 0 and os.path.exists(pdf):
                return open(pdf, 'rb').read(), 'compiled'
    return fallback_pdf(code), 'preview'


def render_result(latex_code='', error='', original_name='', stats=None):
    return render_template('index.html', latex_code=latex_code, error=error, original_name=original_name, stats=stats or {}, history=history[-8:][::-1])


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'GET':
        return render_result()
    file = request.files.get('document')
    if not file or not file.filename:
        return render_result(error='Choose a .docx file before converting.')
    filename = secure_filename(file.filename)
    if not filename or not filename.lower().endswith('.docx'):
        return render_result(error='Unsupported file type. DocuTeX accepts DOCX files only.')
    data = file.read()
    if not data:
        return render_result(error='This file is empty. Choose a document with content.')
    if len(data) > app.config['MAX_CONTENT_LENGTH']:
        return render_result(error='This file is larger than 25 MB. Please choose a smaller document.')
    if not data.startswith(b'PK'):
        return render_result(error='This does not look like a valid DOCX file. Please re-save it from Word and try again.')
    try:
        with tempfile.NamedTemporaryFile(suffix='.docx') as uploaded:
            uploaded.write(data)
            uploaded.flush()
            code = convert_docx_to_latex(uploaded.name)
    except (BadRequest, ValueError, OSError, zipfile.BadZipFile):
        return render_result(error='We could not read this DOCX. It may be corrupted, password-protected, or missing required document parts.')
    except Exception:
        app.logger.exception('DOCX conversion failed for %s', filename)
        return render_result(error='Conversion failed unexpectedly. Please try again with another DOCX file.')

    item = {'name': filename, 'time': datetime.now().strftime('%b %d, %H:%M'), 'chars': len(code)}
    history.append(item)
    stats = {'paragraphs': max(0, code.count('\n\n')), 'chars': len(code), 'time': '< 1s'}
    return render_result(code, original_name=file.filename, stats=stats)


@app.route('/sample')
def sample():
    code = '\\documentclass{article}\n\\usepackage{amsmath}\n\\begin{document}\n\\section{A sample document}\nThis sample is ready to edit and export.\\par\n\\[ E = mc^2 \\]\n\\end{document}\n'
    return render_result(code, original_name='sample-document.docx', stats={'paragraphs': 2, 'chars': len(code), 'time': '< 1s'})


@app.route('/edit', methods=['POST'])
def edit():
    code = request.form.get('latex_code', '')
    if not code.strip():
        return render_result(error='Paste or generate LaTeX before refreshing the preview.')
    stats = {'paragraphs': max(0, code.count('\\n\\n')), 'chars': len(code), 'time': 'edited'}
    return render_result(code, original_name=request.form.get('original_name', 'edited-document.docx'), stats=stats)


@app.route('/download', methods=['POST'])
def download():
    return send_file(io.BytesIO(request.form.get('latex_code', '').encode()), mimetype='text/plain', as_attachment=True, download_name='document.tex')


@app.route('/download/pdf', methods=['POST'])
def download_pdf():
    pdf, mode = make_pdf(request.form.get('latex_code', ''))
    response = send_file(io.BytesIO(pdf), mimetype='application/pdf', as_attachment=True, download_name='document.pdf')
    response.headers['X-DocuTeX-PDF-Mode'] = mode
    return response


@app.route('/download/zip', methods=['POST'])
def download_zip():
    code = request.form.get('latex_code', '')
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr('document.tex', code)
        bundle.writestr('README.txt', 'DocuTeX project\nCompile document.tex with your LaTeX distribution.\n')
    archive.seek(0)
    return send_file(archive, mimetype='application/zip', as_attachment=True, download_name='docutex-project.zip')


@app.errorhandler(RequestEntityTooLarge)
def too_large(_):
    return render_result(error='This file is larger than 25 MB. Please choose a smaller document.'), 413


@app.errorhandler(BadRequest)
def malformed_request(_):
    return render_result(error='The upload could not be read. Please choose the DOCX file again and retry.'), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 3000)), debug=True)
