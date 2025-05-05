from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import uuid
import hashlib
from datetime import datetime
import json
import mimetypes

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = os.path.abspath('uploads')
app.config['BANNED_EXTENSIONS'] = {'exe', 'sh', 'php', 'js'}
app.config['DATA_FILE'] = 'files.json'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    if '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext not in app.config['BANNED_EXTENSIONS']


def generate_file_path(uuid_name, ext):
    dir1 = uuid_name[:2]
    dir2 = uuid_name[2:4]
    path = os.path.join(app.config['UPLOAD_FOLDER'], dir1, dir2)
    os.makedirs(path, exist_ok=True)
    return os.path.join(dir1, dir2, f"{uuid_name}.{ext}")


def calculate_md5(file_stream):
    md5_hash = hashlib.md5()
    for chunk in iter(lambda: file_stream.read(4096), b''):
        md5_hash.update(chunk)
    file_stream.seek(0)
    return md5_hash.hexdigest()


def load_data():
    try:
        with open(app.config['DATA_FILE'], 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_data(data):
    with open(app.config['DATA_FILE'], 'w') as f:
        json.dump(data, f, indent=4)


files_data = load_data()


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    global files_data
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('File type not allowed', 'danger')
            return redirect(request.url)

        file_stream = file.stream
        file_hash = calculate_md5(file_stream)

        for entry in files_data:
            if entry['md5'] == file_hash:
                flash('File already exists', 'danger')
                return redirect(request.url)

        ext = file.filename.rsplit('.', 1)[1].lower()
        uuid_name = uuid.uuid4().hex
        relative_path = generate_file_path(uuid_name, ext)
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], relative_path)
        file.save(full_path)

        new_entry = {
            'original_name': file.filename,
            'uuid_name': uuid_name,
            'upload_date': datetime.now().isoformat(),
            'relative_path': relative_path.replace('\\', '/'),
            'extension': ext,
            'md5': file_hash
        }
        files_data.append(new_entry)
        save_data(files_data)
        flash('File successfully uploaded', 'success')
        return redirect(url_for('upload_file'))

    return render_template('upload.html', files=files_data)


@app.route('/delete/<uuid_name>', methods=['POST'])
def delete_file(uuid_name):
    global files_data
    entry_to_delete = None

    for entry in files_data:
        if entry['uuid_name'] == uuid_name:
            entry_to_delete = entry
            break

    if entry_to_delete:
        try:
            full_path = os.path.join(app.config['UPLOAD_FOLDER'], entry_to_delete['relative_path'])
            os.remove(full_path)
            files_data.remove(entry_to_delete)
            save_data(files_data)
            flash('File successfully deleted', 'success')
        except Exception as e:
            flash(f'Error deleting file: {str(e)}', 'danger')
    else:
        flash('File not found', 'danger')

    return redirect(url_for('upload_file'))


@app.route('/view/<path:filepath>')
def view_image(filepath):
    full_path = os.path.join(app.config['UPLOAD_FOLDER'], filepath)

    if not os.path.exists(full_path):
        return "File not found", 404

    return send_from_directory(
        directory=app.config['UPLOAD_FOLDER'],
        path=filepath,
        mimetype=mimetypes.guess_type(full_path)[0]
    )


if __name__ == '__main__':
    app.run(debug=True)