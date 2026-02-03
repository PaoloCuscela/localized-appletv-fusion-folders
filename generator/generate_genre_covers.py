import os
import argparse
import requests
import sys
import json
import random

# Import the function from the sibling script
# Ensure current directory is in sys.path to allow import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from add_text import add_text_to_image
except ImportError:
    print("Error: Could not import 'add_text.py'. Make sure it is in the same directory.")
    sys.exit(1)

TMDB_API_KEY = "c31c67d63f433851d6e822ce86b17f21"
BASE_URL = "https://api.themoviedb.org/3"

# Default configuration constants
DEFAULT_LANGUAGE = "en"
DEFAULT_INPUT_DIR = "bg_images"
DEFAULT_OUTPUT_DIR = "output"
DEFAULT_FONT_SIZE = 60
DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_FONT = "assets/fonts/SF-Pro-Display-Bold.otf"

def get_genres(media_type, language):
    """
    Fetches genres from TMDB API.
    media_type: 'movie' or 'tv'
    """
    url = f"{BASE_URL}/genre/{media_type}/list"
    params = {
        "api_key": TMDB_API_KEY,
        "language": language
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("genres", [])
    except requests.exceptions.RequestException as e:
        print(f"Error fetching genres: {e}")
        return []

def get_image_files(directory):
    """Returns a shuffled list of image files in a directory."""
    valid_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.tiff')
    files = [
        os.path.join(directory, f) 
        for f in os.listdir(directory) 
        if f.lower().endswith(valid_extensions)
    ]
    random.shuffle(files) # Shuffle to ensure random assignment
    return files

def main():
    parser = argparse.ArgumentParser(description="Generate cover images for TMDB genres.")
    parser.add_argument("--language", type=str, default=DEFAULT_LANGUAGE, help="Language for genres (e.g., 'it-IT', 'en-US')")
    parser.add_argument("--input-dir", type=str, default=DEFAULT_INPUT_DIR, help="Directory containing base images")
    parser.add_argument("--output-dir", type=str, default=DEFAULT_OUTPUT_DIR, help="Directory to save generated covers")
    parser.add_argument("--font", type=str, default=DEFAULT_FONT, help="Path to custom font file")
    parser.add_argument("--fontsize", type=int, default=DEFAULT_FONT_SIZE, help="Font size")
    parser.add_argument("--width", type=int, default=None, help="Target width for output image")
    parser.add_argument("--height", type=int, default=None, help="Target height for output image")
    parser.add_argument("--base-url", type=str, default=DEFAULT_BASE_URL, help="Base URL for background images")
    
    args = parser.parse_args()
    
    # 1. Get Base Images
    if not os.path.exists(args.input_dir):
        print(f"Error: Input directory '{args.input_dir}' does not exist.")
        return
        
    base_images = get_image_files(args.input_dir)
    
    if not base_images:
        print(f"Error: No images found in '{args.input_dir}'.")
        return
        
    print(f"Found {len(base_images)} base images to cycle through.")

    # Process both movie and tv
    media_types = ['movie', 'tv']

    for media_type in media_types:
        print(f"\n--- Processing {media_type} ---")
        
        # 2. Fetch Genres
        print(f"Fetching {media_type} genres (lang: {args.language})...")
        genres = get_genres(media_type, args.language)
        
        if not genres:
            print(f"No genres found for {media_type}. Skipping.")
            continue
        
        print(f"Found {len(genres)} genres for {media_type}.")
        
        # 3. Process each genre
        # Create specific output directory
        current_output_dir = os.path.join(args.output_dir, args.language, media_type)
        if not os.path.exists(current_output_dir):
            os.makedirs(current_output_dir)

        json_output = []

        for i, genre in enumerate(genres):
            genre_name = genre['name']
            genre_id = genre['id']
            
            # Round-robin selection of image
            image_index = i % len(base_images)
            base_image_path = base_images[image_index]
            
            print(f"Processing genre: {genre_name} (ID: {genre_id}) using base image: {os.path.basename(base_image_path)}")
            
            # Call the function from add_text.py
            # We assume add_text_to_image handles the saving logic using the text as filename
            # passed via 'text' param.
            add_text_to_image(
                input_path=base_image_path,
                text=genre_name,
                output_dir=current_output_dir,
                font_size=args.fontsize,
                font_path=args.font,
                target_width=args.width,
                target_height=args.height
            )

            # Create safe filename from text (logic duplicated from add_text.py to predict filename)
            safe_text = "".join([c for c in genre_name if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_")
            image_filename = f"{safe_text}.png"
            
            # Construct relative path from output directory
            # Structure is: language/media_type/filename
            relative_path = f"{args.language}/{media_type}/{image_filename}"
            
            # Ensure base_url doesn't end with slash if relative path starts with one (or clean logic)
            base_url_clean = args.base_url.rstrip('/')
            background_image_url = f"{base_url_clean}/{relative_path}"

            # Create JSON entry
            entry = {
                "dataSource": {
                    "kind": "tmdbDiscover",
                    "payload": {
                        "includeGenres": [genre_id],
                        "sortBy": "popularity.desc",
                        "type": media_type
                    }
                },
                "hideTitle": False,
                "layout": "Wide",
                "name": genre_name,
                "backgroundImageURL": background_image_url
            }
            json_output.append(entry)

        # Save JSON file for the current media type inside the media type directory
        json_filename = f"{media_type}.json"
        json_filepath = os.path.join(current_output_dir, json_filename)
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(json_output, f, indent=2, ensure_ascii=False)
        print(f"Saved JSON configuration to: {json_filepath}")
            
    print("\nAll done!")

if __name__ == "__main__":
    main()
