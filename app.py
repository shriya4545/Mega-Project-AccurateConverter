from flask import Flask, render_template, request, jsonify, send_file
import os
from constants import parse_dxf, convert_to_svg, save_to_mongodb
from datetime import datetime
from constants import collection

app = Flask(__name__)

@app.errorhandler(Exception)
def handle_error(error):
    return jsonify({"error": str(error)}), 500

UPLOAD_FOLDER = 'uploads/'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024

parsed_data_file = 'parsed_data.json'
if os.path.exists(parsed_data_file):
    open(parsed_data_file, 'w').close()

def clear_parsed_data():
    with open(parsed_data_file, 'w') as f:
        f.write('')

def delete_old_svgs():
    for file_name in os.listdir(app.config['UPLOAD_FOLDER']):
        if file_name.endswith('.svg'):
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], file_name))

@app.route('/')
def index():
    clear_parsed_data()
    delete_old_svgs()
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and file.filename.lower().endswith('.dxf'):
        clear_parsed_data()
        delete_old_svgs()
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        min_x, max_x, min_y, max_y = parse_dxf(file_path)
        
        svg_filename = f"output_{os.path.splitext(file.filename)[0]}.svg"
        svg_output = os.path.join(app.config['UPLOAD_FOLDER'], svg_filename)
        
        convert_to_svg(parsed_data_file, svg_output, min_x, max_x, min_y, max_y)
        save_to_mongodb(file_path, svg_output)
        
        with open(svg_output, 'r') as svg_file:
            svg_content = svg_file.read()
        
        return jsonify({"svg": svg_content, "filename": svg_filename}), 200
    else:
        return jsonify({"error": "Invalid file format. Please upload a DXF file."}), 400

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "File not found"}), 404

@app.route('/history', methods=['GET'])
def get_conversion_history():
    history = collection.find({}, {"filename": 1, "upload_time": 1}).sort("upload_time", -1).limit(10)
    history_list = [
        {"filename": item["filename"], "upload_time": item["upload_time"].strftime("%Y-%m-%d %H:%M:%S")}
        for item in history
    ]
    return jsonify(history_list)

@app.route('/file/<filename>')
def serve_svg(filename):
    file_data = collection.find_one({"filename": filename})
    
    if not file_data or "svg_file" not in file_data:
        return jsonify({"error": "File not found"}), 404
    
    svg_content = file_data["svg_file"].decode("utf-8")
    return f"<html><body>{svg_content}</body></html>"

if __name__ == '__main__':
    app.run(debug=True)
