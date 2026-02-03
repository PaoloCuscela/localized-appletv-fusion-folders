import os
import sys
import subprocess
import requests
import json
import uuid
from flask import Flask, request, jsonify, send_file, send_from_directory
from werkzeug.utils import secure_filename
import shutil

app = Flask(__name__)

# Base Paths configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Aggiornato percorso assets/bg_images come richiesto
BG_IMAGES_DIR = os.path.join(BASE_DIR, 'assets', 'bg_images')
# Output indirizzato verso resources nel root di progetto
OUTPUT_DIR = os.path.join(BASE_DIR, '..', 'resources')
ASSOCIATIONS_FILE = os.path.join(BASE_DIR, 'genre_associations.json')

if not os.path.exists(BG_IMAGES_DIR):
    os.makedirs(BG_IMAGES_DIR)
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Import add_text logic directly
try:
    # Aggiungi cartella corrente al path per importare moduli locali
    sys.path.append(BASE_DIR)
    from add_text import add_text_to_image
except ImportError:
    print("Error: Could not import 'add_text.py'.")

# TMDB Configuration
SECRETS_FILE = os.path.join(BASE_DIR, 'secrets.json')
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def get_api_key():
    if os.path.exists(SECRETS_FILE):
        try:
            with open(SECRETS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('tmdb_api_key', '')
        except:
            pass
    return ""

@app.route('/api/config', methods=['GET', 'POST'])
def handle_config():
    if request.method == 'POST':
        data = request.json
        api_key = data.get('tmdb_api_key')
        with open(SECRETS_FILE, 'w') as f:
            json.dump({"tmdb_api_key": api_key}, f, indent=2)
        return jsonify({'success': True})
    else:
        return jsonify({'tmdb_api_key': get_api_key()})

@app.route('/api/genres/<language>', methods=['GET'])
def get_tmdb_genres(language):
    # Prefer key from query param, else fallback to secrets
    api_key = request.args.get('api_key') or get_api_key()
    
    if not api_key:
         return jsonify({'error': 'TMDB API Key missing. Please set it in config.'}), 400

    try:
        results = {}
        for media_type in ['movie', 'tv']:
            url = f"{TMDB_BASE_URL}/genre/{media_type}/list"
            params = {
                "api_key": api_key,
                "language": language
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # Normalizza i generi: id, name
            results[media_type] = data.get('genres', [])
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/associations', methods=['GET', 'POST'])
def manage_associations():
    if request.method == 'POST':
        data = request.json
        with open(ASSOCIATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return jsonify({'success': True})
    else:
        if os.path.exists(ASSOCIATIONS_FILE):
            with open(ASSOCIATIONS_FILE, 'r', encoding='utf-8') as f:
                return jsonify(json.load(f))
        return jsonify({})

@app.route('/generate_custom', methods=['POST'])
def generate_custom():
    data = request.json
    language = data.get('language')
    associations = data.get('associations', {}) # { "tmdb_id": { "filename": "x.png", "media_type": "movie", "name": "Action" }, ... }
    font_path = data.get('font')
    
    # Resolve relative font path to generator directory
    if font_path and not os.path.isabs(font_path):
        font_path = os.path.join(BASE_DIR, font_path)

    base_url = data.get('baseUrl', '')
    
    # Clean base url
    if base_url.endswith('/'):
        base_url = base_url[:-1]

    # Parametri non usati se prendiamo dimensione immagine, ma utili per font size
    font_size_base = int(data.get('fontsize', 60))

    if not language:
        return jsonify({'error': 'Language is required'}), 400

    generated_count = 0
    errors = []

    # Struttura per il JSON finale
    output_meta = {
        "movie": [],
        "tv": []
    }

    print(f"Starting generation for language: {language}")

    for genre_key, info in associations.items():
        filename = info.get('filename')
        # Ensure Title Case for all words (e.g. "commedia musicale" -> "Commedia Musicale")
        raw_name = info.get('name')
        genre_name = raw_name.title() if raw_name else raw_name
        
        media_type = info.get('media_type') 
        
        if not filename or not genre_name or not media_type:
            continue

        src_path = os.path.join(BG_IMAGES_DIR, filename)
        if not os.path.exists(src_path):
            errors.append(f"Image not found: {filename}")
            continue

        # Definisci cartella output: output/it/movie/
        type_output_dir = os.path.join(OUTPUT_DIR, language, media_type)
        if not os.path.exists(type_output_dir):
            os.makedirs(type_output_dir)

        # Output filename: <lang>_<tmdb_id>.jpg
        tmdb_id = info.get('id')
        out_filename = f"{language}_{tmdb_id}.jpg"
        out_path = os.path.join(type_output_dir, out_filename)

        print(f"Generating {out_filename} from {filename}...")

        try:
            add_text_to_image(
                input_path=src_path,
                text=genre_name,
                output_dir=None,
                specific_output_path=out_path,
                font_path=font_path,
                font_size=font_size_base
            )
            
            generated_count += 1
            
            # Determina layout
            layout = "Poster"
            if media_type == 'tv':
                layout = "Wide"

            # Costruisci URL immagine
            # Pattern: <base>/<lang>/<movie|tv>/<filename>
            final_img_url = f"{base_url}/{language}/{media_type}/{out_filename}" if base_url else out_filename

            # Costruiamo oggetto completo
            entry = {
                "id": str(uuid.uuid4()).upper(),
                "name": genre_name,
                "layout": layout,
                "hideTitle": True,
                "backgroundImageURL": final_img_url,
                "dataSource": {
                    "kind": "tmdbDiscover",
                    "payload": {
                        "type": media_type,
                        "sortBy": "popularity.desc",
                        "includeGenres": [ int(info.get('id')) ],
                        "withOriginalLanguage": language
                    }
                }
            }

            output_meta[media_type].append(entry)

        except Exception as e:
            print(f"Error generating {genre_name}: {e}")
            errors.append(f"Error {genre_name}: {str(e)}")


    # Salva i JSON riassuntivi
    for mtype in ['movie', 'tv']:
        # Sort genres alphabetically by name
        output_meta[mtype].sort(key=lambda x: x['name'])

        json_dir = os.path.join(OUTPUT_DIR, language, mtype)
        if not os.path.exists(json_dir):
            os.makedirs(json_dir, exist_ok=True)
            
        json_filename = f"{language}_{mtype}.json"
        json_path = os.path.join(json_dir, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_meta[mtype], f, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------
    # AUTOMATICALLY REBUILD GALLERY after generation
    # ---------------------------------------------------------
    try:
        # Import dynamically or use subprocess to run build_gallery.py
        # Since we are in the same process/env, running the function is best, 
        # but build_gallery is a script. Let's run it as a script for isolation or import.
        # Given sys.path already has BASE_DIR appended above:
        import build_gallery
        build_gallery.generate_gallery()
        print("Gallery updated automatically.")
    except Exception as e:
        print(f"Failed to auto-update gallery: {e}")
    # ---------------------------------------------------------

    return jsonify({
        'success': True, 
        'count': generated_count,
        'errors': errors
    })

# Route to serve the HTML file
@app.route('/')
def home():
    index_path = os.path.join(BASE_DIR, 'index.html')
    return send_file(index_path)

@app.route('/images', methods=['GET'])
def list_images():
    files = []
    for root, dirs, filenames in os.walk(BG_IMAGES_DIR):
        for f in filenames:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                # Create relative path from BG_IMAGES_DIR
                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, BG_IMAGES_DIR)
                # Ensure slashes are forward slashes for web usage
                rel_path = rel_path.replace(os.path.sep, '/')
                files.append(rel_path)
    return jsonify(sorted(files))

@app.route('/images/<path:filename>', methods=['GET'])
def get_image(filename):
    return send_from_directory(BG_IMAGES_DIR, filename)

@app.route('/upload', methods=['POST'])
def upload_image():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(BG_IMAGES_DIR, filename))
        return jsonify({'success': True, 'filename': filename})

@app.route('/images/<filename>', methods=['DELETE'])
def delete_image(filename):
    try:
        os.remove(os.path.join(BG_IMAGES_DIR, secure_filename(filename)))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/outputs', methods=['GET'])
def list_outputs():
    # Structure: { "it-IT": { "movie": ["f1.jpg", ...], "tv": ["f2.jpg", ...] } }
    tree = {}
    if not os.path.exists(OUTPUT_DIR):
        return jsonify(tree)

    for lang in os.listdir(OUTPUT_DIR):
        lang_path = os.path.join(OUTPUT_DIR, lang)
        if os.path.isdir(lang_path):
            tree[lang] = {}
            for category in os.listdir(lang_path):
                cat_path = os.path.join(lang_path, category)
                if os.path.isdir(cat_path):
                    images = [f for f in os.listdir(cat_path) if f.lower().endswith(('.jpg', '.png'))]
                    tree[lang][category] = sorted(images)
    return jsonify(tree)

@app.route('/view_output/<path:filepath>')
def view_output(filepath):
    return send_from_directory(OUTPUT_DIR, filepath)

@app.route('/download_zip/<language>')
@app.route('/download_zip/<language>/<category>')
def download_zip(language, category=None):
    if category:
        target_path = os.path.join(OUTPUT_DIR, language, category)
        archive_name = f"{language}_{category}_covers"
    else:
        target_path = os.path.join(OUTPUT_DIR, language)
        archive_name = f"{language}_covers"

    if not os.path.exists(target_path):
        return "Folder not found", 404
    
    # Create zip file. root_dir=target_path ensures the zip contains files directly
    shutil.make_archive(archive_name, 'zip', root_dir=target_path)
    
    try:
        return send_file(f"{archive_name}.zip", as_attachment=True)
    except Exception as e:
        return str(e), 500

@app.route('/download_json/<language>/<category>')
def download_json(language, category):
    # category is 'movie' or 'tv'
    # filename is 'movie.json' or 'tv.json'
    filename = f"{category}.json"
    directory = os.path.join(OUTPUT_DIR, language, category)
    try:
        return send_from_directory(directory, filename, as_attachment=True)
    except Exception as e:
        return str(e), 404

# Route to execute the script
@app.route('/run', methods=['POST'])
def run_script():
    data = request.json
    
    # Path to the script we want to run
    script_path = 'generate_genre_covers.py'
    
    # Construct command
    # Using sys.executable ensures we use the same python interpreter (venv) running the server
    cmd = [sys.executable, script_path]
    
    # Add arguments if they exist in the request
    if data.get('language'):
        cmd.extend(['--language', data['language']])
        
    if data.get('font'):
        cmd.extend(['--font', data['font']])
        
    if data.get('fontsize'):
        cmd.extend(['--fontsize', str(data['fontsize'])])

    if data.get('width'):
        cmd.extend(['--width', str(data['width'])])

    if data.get('height'):
        cmd.extend(['--height', str(data['height'])])
        
    if data.get('base_url'):
        cmd.extend(['--base-url', data['base_url']])
        
    # Input Dir is fixed to 'bg_images', so we don't pass it from client

    print(f"Executing command: {' '.join(cmd)}")

    try:
        # Run process
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            cwd=os.getcwd() # Ensure it runs in the current directory
        )
        
        return jsonify({
            'success': result.returncode == 0,
            'stdout': result.stdout,
            'stderr': result.stderr
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'stdout': '',
            'stderr': str(e)
        })

if __name__ == '__main__':
    port = 5001
    print(f"Starting server on http://127.0.0.1:{port}")
    app.run(debug=True, port=port)
