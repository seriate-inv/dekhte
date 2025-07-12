from flask import Flask, render_template, request, redirect, send_file, url_for
import csv, os
from datetime import datetime
from werkzeug.utils import secure_filename
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
CSV_FILE = 'data.csv'
FILTERED_CSV = 'filtered.csv'
EMAIL_TO = 'seriate001archana@gmail.com'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ✅ Home Page
@app.route('/')
def index():
    return render_template('index.html')

# ✅ Submit Entry
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    email = request.form['email']
    entry_type = request.form['type']
    latitude = request.form.get('latitude', '')
    longitude = request.form.get('longitude', '')
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    image_file = request.files['image']
    image_name = secure_filename(image_file.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_name)
    image_file.save(image_path)

    with open(CSV_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([name, email, entry_type, timestamp, latitude, longitude, image_name])
    
    return redirect('/')

# ✅ Admin Panel with Filters
@app.route('/admin')
def admin():
    name_filter = request.args.get('name', '').lower()
    date_filter = request.args.get('date', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')

    data = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) == 7:
                    name, email, type_, timestamp, lat, long, img = row
                    if name_filter and name_filter not in name.lower():
                        continue
                    if date_filter and not timestamp.startswith(date_filter):
                        continue
                    if not date_filter and not is_within_range(timestamp, from_date, to_date):
                        continue
                    data.append({
                        'name': name, 'email': email, 'type': type_,
                        'timestamp': timestamp, 'latitude': lat,
                        'longitude': long, 'image': img
                    })
    return render_template('admin.html', data=data)

# ✅ Delete Image Entry
@app.route('/delete', methods=['POST'])
def delete_image_only():
    target_time = request.form['timestamp']
    target_img = request.form['image']
    updated_rows = []

    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 7:
                if row[3] == target_time and row[6] == target_img:
                    row[6] = ''  # Clear image field
                updated_rows.append(row)

    with open(CSV_FILE, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(updated_rows)

    try:
        os.remove(os.path.join(UPLOAD_FOLDER, target_img))
    except FileNotFoundError:
        pass

    return redirect('/admin')

# ✅ Download CSV with filters
@app.route('/download_csv')
def download_csv():
    name_filter = request.args.get('name', '').lower()
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    filtered = []

    # Use absolute path to filtered.csv
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filtered_path = os.path.join(base_dir, 'filtered.csv')

    if not os.path.exists(CSV_FILE):
        return "Data file not found!", 404

    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) != 7:
                continue
            if name_filter and name_filter not in row[0].lower():
                continue
            if not is_within_range(row[3], from_date, to_date):
                continue
            filtered.append(row)

    if not filtered:
        return "No matching data found for download.", 404

    with open(filtered_path, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(filtered)

    return send_file(filtered_path, as_attachment=True)


# ✅ Email CSV with filters
@app.route('/email_csv')
def email_csv():
    name_filter = request.args.get('name', '').lower()
    date_filter = request.args.get('date', '')
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    filtered = []

    with open(CSV_FILE, 'r') as file:
        reader = csv.reader(file)
        for row in reader:
            if len(row) == 7:
                if name_filter and name_filter not in row[0].lower():
                    continue
                if date_filter and not row[3].startswith(date_filter):
                    continue
                if not date_filter and not is_within_range(row[3], from_date, to_date):
                    continue
                filtered.append(row)

    with open(FILTERED_CSV, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(filtered)

    send_email_with_attachment(FILTERED_CSV)
    return redirect('/admin')

# ✅ Email function
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

# ✅ Range Filter Helper
def is_within_range(timestamp_str, from_date_str, to_date_str):
    try:
        entry_date = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S").date()
        if from_date_str:
            from_date = datetime.strptime(from_date_str, "%Y-%m-%d").date()
            if entry_date < from_date:
                return False
        if to_date_str:
            to_date = datetime.strptime(to_date_str, "%Y-%m-%d").date()
            if entry_date > to_date:
                return False
        return True
    except:
        return False

# ✅ Run
if __name__ == '__main__':
    app.run(debug=True)
