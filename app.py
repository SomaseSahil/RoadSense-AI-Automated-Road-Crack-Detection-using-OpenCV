import os
import socket
import qrcode
from io import BytesIO
from flask import Flask, render_template, request, jsonify, send_file, url_for, send_from_directory

from crack_detection import process_cracks

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(basedir, 'dataset')
app.config['OUTPUT_FOLDER'] = os.path.join(basedir, 'output')

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def calculate_parameters(crack_percentage):
    # Map percentage to a simulated realistic road thickness measurement in millimeters
    # Adjusted multiplier to better reflect visual surface area
    estimated_mm = crack_percentage * 45.0
    
    if estimated_mm < 15.0:
        thickness = f"{estimated_mm:.1f} mm"
        severity = "Low"
        life = "5-10 Years"
        action = "The pavement shows superficial cracking with no deep structural damage. Routine monitoring is recommended every 6-12 months. Small surface seals can be applied if cracks begin to widen during seasonal temperature shifts."
        score = min(100, 100 - (crack_percentage * 8))
    elif estimated_mm < 35.0:
        thickness = f"{estimated_mm:.1f} mm"
        severity = "Medium"
        life = "2-5 Years"
        action = "Moderate cracking detected. It is highly advised to apply a surface seal or crack-filling treatment (e.g., hot-pour rubberized asphalt) to prevent water infiltration. Water intrusion at this stage will rapidly accelerate base layer deterioration."
        score = 100 - (crack_percentage * 15)
    else:
        thickness = f"{estimated_mm:.1f} mm"
        severity = "High"
        life = "< 1 Year"
        action = "Severe structural failure detected. The crack thickness indicates the base layers may be compromised. Full depth patching or comprehensive rehabilitation of the road segment is required immediately to restore safe load-bearing capacity and prevent vehicular damage."
        score = max(0, 100 - (crack_percentage * 25))
        
    return {
        "thickness": thickness,
        "severity": severity,
        "life": life,
        "area": f"{crack_percentage:.2f}%",
        "action": action,
        "score": f"{score:.1f} / 100"
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/mobile')
def mobile():
    return render_template('mobile_camera.html')

latest_scan_result = None

@app.route('/latest_result')
def get_latest_result():
    if latest_scan_result:
        return jsonify(latest_scan_result)
    return jsonify({"success": False})

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # Process image
        out_filename, crack_pct, crack_count = process_cracks(filepath)
        
        if out_filename is None:
            return jsonify({"error": "Failed to process image"}), 500
            
        params = calculate_parameters(crack_pct)
        params["crack_count"] = crack_count
        
        global latest_scan_result
        latest_scan_result = {
            "success": True,
            "original_image": url_for('static_upload', filename=filename),
            "processed_image": url_for('static_output', filename=out_filename),
            "parameters": params,
            "percentage": round(crack_pct, 2)
        }
        
        return jsonify(latest_scan_result)

@app.route('/qr')
def generate_qr():
    ip = get_local_ip()
    url = f"http://{ip}:5000/mobile"
    # To force Google Lens to see it as a URL immediately
    print(f"Generating QR for: {url}")
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/uploads/<filename>')
def static_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/outputs/<filename>')
def static_output(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
