from flask import Flask, render_template, request, redirect, send_file, url_for
import csv, os
from datetime import datetime
from werkzeug.utils import secure_filename
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import requests

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
CSV_FILE = 'data.csv'
FILTERED_CSV = 'filtered.csv'
EMAIL_TO = 'seriate001archana@gmail.com'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def get_user_filename(name, email, type_):
    return f"{name}_{email}_{type_}.csv"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    entry_type = request.form['type']
    latitude = request.form.get('latitude', '0')
    longitude = request.form.get('longitude', '0')
    address = request.form.get('address', 'Location not available')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Check for existing entry if this is an exit
    if entry_type == 'Exit':
        entry_exists = False
        user_filename = get_user_filename(name, email, 'Entry')
        if os.path.exists(os.path.join(UPLOAD_FOLDER, user_filename.replace('.csv', '.jpg'))):
            entry_exists = True
        
        if not entry_exists:
            return render_template('error.html', 
                                 message="No matching entry found for this name and email. Please check your details or contact support.")

    image_file = request.files['image']
    image_ext = os.path.splitext(image_file.filename)[1]
    image_name = get_user_filename(name, email, entry_type).replace('.csv', image_ext)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    image_file.save(image_path)

    # Save data to CSV
    with open(CSV_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([
            name, email, entry_type, timestamp, 
            latitude, longitude, address, image_name
        ])
    
    return redirect('/success')

@app.route('/success')
def success():
    return render_template('success.html')

@app.route('/admin')
def admin():
    name_filter = request.args.get('name', '').lower()
    date_filter = request.args.get('date', '')

    data = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 8:
                    name, email, type_, timestamp, lat, long, address, img = row
                    if name_filter and name_filter not in name.lower():
                        continue
                    if date_filter and not timestamp.startswith(date_filter):
                        continue
                    
                    # Check if image exists
                    img_exists = os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], img))
                    
                    data.append({
                        'name': name, 'email': email, 'type': type_,
                        'timestamp': timestamp, 'latitude': lat,
                        'longitude': long, 'address': address, 
                        'image': img if img_exists else None
                    })
    return render_template('admin.html', data=data)

@app.route('/delete_image', methods=['POST'])
def delete_image():
    image_name = request.form['image']
    
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, image_name))
    except FileNotFoundError:
        pass

    return redirect('/admin')

@app.route('/download_csv')
def download_csv():
    name_filter = request.args.get('name', '').lower()
    date_filter = request.args.get('date', '')
    filtered = []

    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 8:
                if name_filter and name_filter not in row[0].lower():
                    continue
                if date_filter and not row[3].startswith(date_filter):
                    continue
                filtered.append(row)

    with open(FILTERED_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(filtered)

    return send_file(FILTERED_CSV, as_attachment=True)

@app.route('/email_csv')
def email_csv():
    name_filter = request.args.get('name', '').lower()
    date_filter = request.args.get('date', '')
    filtered = []

    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) >= 8:
                if name_filter and name_filter not in row[0].lower():
                    continue
                if date_filter and not row[3].startswith(date_filter):
                    continue
                filtered.append(row)

    with open(FILTERED_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(filtered)

    send_email_with_attachment(FILTERED_CSV)
    return redirect('/admin')

def send_email_with_attachment(filepath):
    sender_email = "seriate001archana@gmail.com"
    sender_pass = "wyyf gduw ulql vpqz"

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = EMAIL_TO
    msg['Subject'] = 'Filtered CSV Report'

    with open(filepath, 'rb') as f:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(filepath)}"')
        msg.attach(part)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_pass)
        server.sendmail(sender_email, EMAIL_TO, msg.as_string())

if __name__ == '__main__':
    app.run(debug=True)