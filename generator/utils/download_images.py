import json
import requests
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# URL del JSON (può essere passato come argomento)
if len(sys.argv) > 1:
    json_url = sys.argv[1]
else:
    json_url = "https://raw.githubusercontent.com/amcottre/Fusion-JSON/refs/heads/main/Apple%20Genres.json"

# Cartella di destinazione
output_folder = "downloaded_images"

def download_json(url):
    """Scarica il file JSON"""
    print(f"Downloading JSON from {url}...")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def download_image(url, folder, filename=None):
    """Scarica una singola immagine"""
    if not filename:
        # Estrae il nome del file dall'URL
        filename = os.path.basename(urlparse(url).path)
    
    filepath = os.path.join(folder, filename)
    
    # Evita di scaricare se il file esiste già
    if os.path.exists(filepath):
        print(f"  ⏭️  Skipping {filename} (already exists)")
        return
    
    try:
        print(f"  ⬇️  Downloading {filename}...")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"  ✅ Downloaded {filename}")
    except Exception as e:
        print(f"  ❌ Error downloading {filename}: {e}")

def main():
    # Crea la cartella di output
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    try:
        # Scarica il JSON
        data = download_json(json_url)
        
        # Trova tutte le immagini nel JSON
        image_urls = []
        
        def extract_urls(obj, path=""):
            """Estrae ricorsivamente tutti gli URL di immagini dal JSON"""
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and (value.startswith('http://') or value.startswith('https://')):
                        # Controlla se è un'immagine
                        if any(ext in value.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']):
                            image_urls.append(value)
                    else:
                        extract_urls(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    extract_urls(item, f"{path}[{i}]")
        
        extract_urls(data)
        
        print(f"\nFound {len(image_urls)} images to download\n")
        
        # Scarica tutte le immagini
        for i, url in enumerate(image_urls, 1):
            print(f"[{i}/{len(image_urls)}]")
            download_image(url, output_folder)
        
        print(f"\n✅ Download completed! Images saved in '{output_folder}' folder")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")

if __name__ == "__main__":
    main()
