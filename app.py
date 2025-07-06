from flask import Flask, render_template, request, redirect, url_for, flash, session
import pandas as pd
import os
import PyPDF2
import docx
from werkzeug.utils import secure_filename
from apscheduler.schedulers.background import BackgroundScheduler
from scraper import collect_and_save_jobs  # import your scraping function

app = Flask(__name__)
app.secret_key = 'secret-key'

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ✅ Force HTTPS redirect
@app.before_request
def before_request():
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(file_path):
    text = ""
    with open(file_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text
    return text

def extract_text_from_docx(file_path):
    doc = docx.Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def analyze_cv(text):
    feedback = []
    required_sections = ['education', 'experience', 'skills', 'projects', 'certification']
    lower_text = text.lower()
    for section in required_sections:
        if section not in lower_text:
            feedback.append(f"Missing section: {section.capitalize()}")
    if not feedback:
        feedback.append("✅ CV looks good. All key sections are present!")
    return feedback

def extract_keywords(text):
    keywords = []
    keywords_map = {
        'python': 'Software Development',
        'java': 'Software Development',
        'marketing': 'Marketing',
        'finance': 'Finance',
        'data': 'Data Science',
        'analysis': 'Data Science',
        'sales': 'Sales',
        'communication': 'Communications',
    }
    lower_text = text.lower()
    for key in keywords_map:
        if key in lower_text:
            keywords.append(keywords_map[key])
    return list(set(keywords))

@app.route('/')
def index():
    job_title_filter = request.args.get('job_title', '').strip()
    location_filter = request.args.get('location', '').strip()

    try:
        df = pd.read_csv('job_info.csv')
        unique_job_titles = sorted(df['Job_Title'].dropna().unique())
        unique_locations = sorted(df['Job_Location'].dropna().unique())

        if job_title_filter:
            df = df[df['Job_Title'].str.lower() == job_title_filter.lower()]
        if location_filter:
            df = df[df['Job_Location'].str.lower() == location_filter.lower()]

        job_listings = df.to_dict(orient='records')
    except Exception as e:
        flash(f"Error loading job data: {e}")
        job_listings = []
        unique_job_titles = []
        unique_locations = []

    return render_template(
        'index.html',
        jobs=job_listings,
        suggestions=session.get('career_suggestions', []),
        saved_jobs=session.get('saved_jobs', []),
        selected_job_title=job_title_filter,
        selected_location=location_filter,
        job_titles=unique_job_titles,
        locations=unique_locations
    )

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    feedback = []
    if request.method == 'POST':
        file = request.files.get('cv')
        if not file or file.filename == '':
            flash("No file selected.")
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            if filename.endswith('.pdf'):
                text = extract_text_from_pdf(filepath)
            elif filename.endswith('.docx'):
                text = extract_text_from_docx(filepath)
            else:
                flash("Unsupported file format.")
                return redirect(request.url)

            feedback = analyze_cv(text)
            session['career_suggestions'] = extract_keywords(text)
        else:
            flash("Invalid file type. Please upload a PDF or DOCX.")

    return render_template('upload.html', feedback=feedback)

@app.route('/save_job', methods=['POST'])
def save_job():
    job_id = request.form.get('job_id')
    job_title = request.form.get('job_title')
    company = request.form.get('company')

    if 'saved_jobs' not in session:
        session['saved_jobs'] = []

    saved_jobs = session['saved_jobs']
    if any(job['job_id'] == job_id for job in saved_jobs):
        flash("Job already saved.")
    else:
        saved_jobs.append({'job_id': job_id, 'job_title': job_title, 'company': company})
        session['saved_jobs'] = saved_jobs
        flash("Job saved successfully!")

    return redirect(url_for('index'))

@app.route('/saved_jobs')
def saved_jobs():
    return render_template('saved_jobs.html', saved_jobs=session.get('saved_jobs', []))

@app.route('/remove_job/<job_id>')
def remove_job(job_id):
    saved_jobs = session.get('saved_jobs', [])
    saved_jobs = [job for job in saved_jobs if job['job_id'] != job_id]
    session['saved_jobs'] = saved_jobs
    flash("Job removed from saved list.")
    return redirect(url_for('saved_jobs'))

# ✅ Scheduler setup for web scraping
scheduler = BackgroundScheduler()
scheduler.add_job(func=collect_and_save_jobs, trigger="interval", days=1)  # Run daily
scheduler.start()

# Shut down scheduler on exit
import atexit
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))  # default to 10000 for local or fallback
    app.run(host='0.0.0.0', port=port)
