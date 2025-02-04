import os
import pickle
import tempfile
import shutil
from flask import Flask, render_template, request, redirect, url_for
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = tempfile.mkdtemp()
app.secret_key = os.urandom(24)

# Google Drive Configuration
FOLDER_ID = '1j83pj6sIL2mfNiWFqOYbb21vvNvlTwqd'  # REPLACE WITH YOUR FOLDER ID

def get_drive_service():
    """Authenticate using existing token.pickle"""
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            raise Exception('Authentication required. Run generate_token.py first.')
    
    return build('drive', 'v3', credentials=creds)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/upload', methods=['GET'])
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    color_mode = request.form.get('color', 'bw')
    pages = request.form.get('pages', 'all')
    instructions = request.form.get('instructions', '')
    
    if file.filename == '':
        return redirect(request.url)
    
    try:
        temp_dir = tempfile.mkdtemp()
        filename = secure_filename(file.filename)
        file_path = os.path.join(temp_dir, filename)
        file.save(file_path)
        
        service = get_drive_service()
        file_metadata = {
            'name': filename,
            'parents': [FOLDER_ID]
        }
        media = MediaFileUpload(file_path, resumable=True)
        drive_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        description = f"Color: {color_mode}\nPages: {pages}\nInstructions: {instructions}"
        service.files().update(
            fileId=drive_file['id'],
            body={'description': description}
        ).execute()
        
        return redirect(url_for('confirmation'))
    except Exception as e:
        return f'Error: {str(e)}'
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

if __name__ == '__main__':
    app.run(debug=True)
