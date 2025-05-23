import os
import uuid
from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from ultralytics import YOLO
import cv2

UPLOAD_FOLDER = 'uploads'  # Directory for uploaded files
PROCESSED_FOLDER = 'processed'  # Directory for processed files
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov'}  # Allowed video formats

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['PROCESSED_FOLDER'] = PROCESSED_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create upload folder if not exists
os.makedirs(PROCESSED_FOLDER, exist_ok=True)  # Create processed folder if not exists

model = YOLO('yolov8n.pt')  # Load YOLO model

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file part'}), 400
    file = request.files['video']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return jsonify({'status': 'success', 'filename': unique_filename}), 200
    return jsonify({'status': 'error', 'message': 'Invalid file type'}), 400

@app.route('/process', methods=['POST'])
def process_video():
    data = request.json
    filename = data.get('filename')
    if not filename:
        return jsonify({'status': 'error', 'message': 'Filename required'}), 400

    input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if not os.path.exists(input_path):
        return jsonify({'status': 'error', 'message': 'File not found'}), 404

    output_filename = f"processed_{filename}"
    output_path = os.path.join(app.config['PROCESSED_FOLDER'], output_filename)

    cap = cv2.VideoCapture(input_path)  # Open video file
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)

    out = cv2.VideoWriter(output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)  # Run YOLO model on frame
        boxes = results[0].boxes
        count = 0
        for box in boxes:
            cls = int(box.cls[0])
            if cls == 0:  # Class 0 = person in YOLO
                count += 1
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)  # Draw rectangle around person

        cv2.putText(frame, f'People count: {count}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)  # Display count
        out.write(frame)

    cap.release()
    out.release()

    return jsonify({
        'status': 'success',
        'download_url': f'/download/{output_filename}'
    }), 200

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    return send_from_directory(app.config['PROCESSED_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)  # Start Flask app
