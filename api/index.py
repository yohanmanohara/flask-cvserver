from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
import PyPDF2
import re
import os
import json

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def home():
    return redirect(url_for('upload_file'))

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            return error_response('No file part in request')
            
        file = request.files['file']
        
        if file.filename == '':
            return error_response('No selected file')
        
        if file and allowed_file(file.filename):
            try:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                
                with open(filepath, 'rb') as f:
                    text = extract_text_from_pdf(f)
                    cv_info = parse_cv_info(text)
                
                os.remove(filepath)
                
                # Return JSON if requested via AJAX or specific content type
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify(cv_info)
                return render_results(cv_info)
                
            except Exception as e:
                if 'filepath' in locals() and os.path.exists(filepath):
                    os.remove(filepath)
                return error_response(f'Error processing file: {str(e)}')
        
        return error_response('Allowed file type is PDF')
    
    return render_upload_form()

@app.route('/api/upload', methods=['POST'])
def api_upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in request'}), 400
        
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            with open(filepath, 'rb') as f:
                text = extract_text_from_pdf(f)
                cv_info = parse_cv_info(text)
            
            os.remove(filepath)
            return jsonify(cv_info)
            
        except Exception as e:
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({'error': f'Error processing file: {str(e)}'}), 500
    
    return jsonify({'error': 'Allowed file type is PDF'}), 400

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
        return text
    except Exception as e:
        raise Exception(f"Could not read PDF: {str(e)}")

def parse_cv_info(text):
    # Improved parsing patterns
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    name_pattern = r'(?:^|\n)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
    skills_pattern = r'(?i)(skills|technical skills|key competencies|expertise)[:\s]*(.*?)(?=\n\w+:|$)'
    
    # Extract information
    emails = list(set(re.findall(email_pattern, text)))
    phones = list(set(re.findall(phone_pattern, text)))
    possible_names = re.findall(name_pattern, text)
    skills_section = re.search(skills_pattern, text, re.DOTALL)
    
    # Extract skills if section exists
    skills = []
    if skills_section:
        skills_text = skills_section.group(2)
        skills = [skill.strip() for skill in re.split(r'[,•\-•]', skills_text) if skill.strip()]
    
    # Try to find the most likely name
    name = "Not Found"
    for candidate in possible_names:
        candidate = candidate.strip()
        if len(candidate.split()) >= 2:  # At least first and last name
            name = candidate
            break
    
    return {
        'name': name,
        'emails': emails,
        'phones': phones,
        'skills': skills,
        'text': text
    }

def render_upload_form():
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CV Parser | Upload</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {
                --primary: #4361ee;
                --secondary: #3f37c9;
                --light: #f8f9fa;
                --dark: #212529;
            }
            body {
                background-color: #f5f7fb;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            }
            .upload-container {
                max-width: 600px;
                margin: 5rem auto;
                padding: 2rem;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
            }
            .upload-card {
                border: 2px dashed #d1d5db;
                border-radius: 8px;
                padding: 3rem 2rem;
                text-align: center;
                transition: all 0.3s ease;
                background: #f9fafb;
                cursor: pointer;
            }
            .upload-card:hover {
                border-color: var(--primary);
                background: rgba(67, 97, 238, 0.05);
            }
            .upload-card i {
                font-size: 3rem;
                color: var(--primary);
                margin-bottom: 1rem;
            }
            .btn-primary {
                background-color: var(--primary);
                border-color: var(--primary);
            }
            .btn-primary:hover {
                background-color: var(--secondary);
                border-color: var(--secondary);
            }
            #file-info {
                margin-top: 1rem;
                font-size: 0.9rem;
                color: #6b7280;
            }
            .json-preview {
                background: #f8f9fa;
                border-radius: 5px;
                padding: 15px;
                max-height: 300px;
                overflow-y: auto;
                font-family: monospace;
                white-space: pre-wrap;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="upload-container">
                <h1 class="text-center mb-4"><i class="fas fa-file-upload me-2"></i>CV Parser</h1>
                <p class="text-center text-muted mb-4">Upload your CV in PDF format to extract information</p>
                
                <form method="post" enctype="multipart/form-data" id="upload-form">
                    <div class="upload-card" id="drop-area">
                        <i class="fas fa-cloud-upload-alt"></i>
                        <h5>Drag & drop your PDF file here</h5>
                        <p class="text-muted">or</p>
                        <button type="button" class="btn btn-primary px-4" onclick="document.getElementById('file-input').click()">
                            <i class="fas fa-folder-open me-2"></i>Browse Files
                        </button>
                        <input type="file" id="file-input" name="file" accept=".pdf" required hidden>
                        <div id="file-info"></div>
                    </div>
                    <div class="d-grid mt-3">
                        <button type="submit" class="btn btn-primary btn-lg" id="submit-btn" disabled>
                            <i class="fas fa-spinner fa-spin me-2 d-none"></i>Process CV
                        </button>
                    </div>
                </form>
                
                <div class="mt-4" id="json-result" style="display: none;">
                    <h4 class="mb-3">JSON Output</h4>
                    <div class="json-preview" id="json-output"></div>
                    <button class="btn btn-outline-primary mt-2" onclick="copyToClipboard()">
                        <i class="fas fa-copy me-2"></i>Copy JSON
                    </button>
                </div>
            </div>
        </div>

        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
        <script>
            const dropArea = document.getElementById('drop-area');
            const fileInput = document.getElementById('file-input');
            const fileInfo = document.getElementById('file-info');
            const submitBtn = document.getElementById('submit-btn');
            const form = document.getElementById('upload-form');
            const jsonResult = document.getElementById('json-result');
            const jsonOutput = document.getElementById('json-output');

            // Prevent default drag behaviors
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, preventDefaults, false);
            });

            function preventDefaults(e) {
                e.preventDefault();
                e.stopPropagation();
            }

            // Highlight drop area when item is dragged over it
            ['dragenter', 'dragover'].forEach(eventName => {
                dropArea.addEventListener(eventName, highlight, false);
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropArea.addEventListener(eventName, unhighlight, false);
            });

            function highlight() {
                dropArea.classList.add('bg-light');
                dropArea.style.borderColor = '#4361ee';
            }

            function unhighlight() {
                dropArea.classList.remove('bg-light');
                dropArea.style.borderColor = '#d1d5db';
            }

            // Handle dropped files
            dropArea.addEventListener('drop', handleDrop, false);

            function handleDrop(e) {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files.length) {
                    fileInput.files = files;
                    handleFiles(files);
                }
            }

            // Handle selected files
            fileInput.addEventListener('change', function() {
                handleFiles(this.files);
            });

            function handleFiles(files) {
                if (files.length > 0) {
                    const file = files[0];
                    if (file.type === 'application/pdf') {
                        fileInfo.innerHTML = `
                            <div class="alert alert-success py-2">
                                <i class="fas fa-file-pdf me-2"></i>
                                <strong>${file.name}</strong> (${(file.size / 1024 / 1024).toFixed(2)} MB)
                                <button type="button" class="btn-close float-end" onclick="clearFile()"></button>
                            </div>
                        `;
                        submitBtn.disabled = false;
                    } else {
                        fileInfo.innerHTML = `
                            <div class="alert alert-danger py-2">
                                <i class="fas fa-exclamation-circle me-2"></i>
                                Please select a PDF file
                            </div>
                        `;
                        submitBtn.disabled = true;
                    }
                }
            }

            function clearFile() {
                fileInput.value = '';
                fileInfo.innerHTML = '';
                submitBtn.disabled = true;
                jsonResult.style.display = 'none';
            }

            function copyToClipboard() {
                navigator.clipboard.writeText(jsonOutput.textContent)
                    .then(() => {
                        const copyBtn = document.querySelector('button[onclick="copyToClipboard()"]');
                        const originalText = copyBtn.innerHTML;
                        copyBtn.innerHTML = '<i class="fas fa-check me-2"></i>Copied!';
                        setTimeout(() => {
                            copyBtn.innerHTML = originalText;
                        }, 2000);
                    });
            }

            // Form submission
            form.addEventListener('submit', function(e) {
                e.preventDefault();
                
                const spinner = submitBtn.querySelector('.fa-spinner');
                spinner.classList.remove('d-none');
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
                
                const formData = new FormData(form);
                
                fetch('/api/upload', {
                    method: 'POST',
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    jsonOutput.textContent = JSON.stringify(data, null, 2);
                    jsonResult.style.display = 'block';
                })
                .catch(error => {
                    alert('Error processing file: ' + error.message);
                })
                .finally(() => {
                    spinner.classList.add('d-none');
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2 d-none"></i>Process CV';
                });
            });
        </script>
    </body>
    </html>
    ''')

def render_results(cv_info):
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CV Parser | Results</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                font-family: Arial, sans-serif;
                padding: 20px;
            }
            .json-container {
                max-width: 800px;
                margin: 0 auto;
            }
            pre {
                background: #f4f4f4;
                padding: 20px;
                border-radius: 5px;
                overflow-x: auto;
            }
        </style>
    </head>
    <body>
        <div class="json-container">
            <h1 class="mb-4">CV Information (JSON)</h1>
            <a href="/upload" class="btn btn-primary mb-4">
                <i class="fas fa-arrow-left me-2"></i>Upload Another
            </a>
            <pre id="json-output">{{ cv_info|tojson(indent=4) }}</pre>
            <button class="btn btn-secondary mt-3" onclick="copyToClipboard()">
                <i class="fas fa-copy me-2"></i>Copy JSON
            </button>
        </div>

        <script>
            function copyToClipboard() {
                const el = document.getElementById('json-output');
                navigator.clipboard.writeText(el.textContent)
                    .then(() => {
                        const btn = document.querySelector('button[onclick="copyToClipboard()"]');
                        const originalText = btn.innerHTML;
                        btn.innerHTML = '<i class="fas fa-check me-2"></i>Copied!';
                        setTimeout(() => {
                            btn.innerHTML = originalText;
                        }, 2000);
                    });
            }
        </script>
    </body>
    </html>
    ''', cv_info=cv_info)

def error_response(message):
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Error | CV Parser</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            body {
                background-color: #f5f7fb;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                height: 100vh;
                display: flex;
                align-items: center;
            }
            .error-container {
                max-width: 500px;
                margin: 0 auto;
                padding: 2rem;
                background: white;
                border-radius: 10px;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
                text-align: center;
            }
            .error-icon {
                font-size: 4rem;
                color: #dc3545;
                margin-bottom: 1rem;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="error-container">
                <div class="error-icon">
                    <i class="fas fa-exclamation-circle"></i>
                </div>
                <h2 class="mb-3">Error Processing Request</h2>
                <p class="text-muted mb-4">{{ message }}</p>
                <a href="/upload" class="btn btn-primary">
                    <i class="fas fa-arrow-left me-2"></i>Try Again
                </a>
            </div>
        </div>
    </body>
    </html>
    ''', message=message)

if __name__ == '__main__':
    app.run(debug=True)