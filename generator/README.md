






# Gradient Fusion Cover Generator

A tool to generate localized genre covers for Fusion using TMDB data and custom gradient backgrounds.

## Features

- **Web Interface**: Easy-to-use UI to map genres to background images.
- **TMDB Integration**: Fetches genre lists dynamically for any language (Movie & TV).
- **Customization**: Configurable font, text size, and metadata base URL.
- **Smart Mapping**: Remembers your image choices across languages.
- **Auto-Gallery**: Generates a static HTML gallery to preview and download your covers.
- **Output Standard**: Generates JSON metadata compatible with fusion schemes.

## Project Structure

- `generator/`: Contains the core logic, web server, and assets.
- `resources/`: Output directory where generated images and JSON files are saved.
- `index.html`: (Root) A static gallery to view and access generated resources.

## Prerequisites

- Python 3.x
- A TMDB API Key (free registration at [themoviedb.org](https://www.themoviedb.org/movie))

## Installation

1. Create a virtual environment (optional but recommended):
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### 1. Start the Generator Server
Run the Flask server located in the generator directory:

```bash
python server.py
```

The server will start on **http://127.0.0.1:5001**.

### 2. Configure & Map
1. **API Key**: Enter your TMDB API Key in the top bar.
2. **Language**: Select your desired language code (e.g., `it`, `en`, `fr`).
3. **Load Genres**: Click to fetch the list from TMDB.
4. **Map Images**: 
   - Click the grey box next to a genre.
   - Select a background image from the modal.
   - Click **Save Mapping** to store your choices locally.

### 3. Generate
1. Scroll to the "Generation Settings" section.
2. **Metadata Base URL** (Optional): If you host these images (e.g., on GitHub), enter the base URL here (e.g., `https://raw.githubusercontent.com/user/repo/main/resources`).
3. Click **GENERATE ALL COVERS**.

### 4. View Results
Once generation is complete, the tool automatically updates the **Gallery**.
Open the `index.html` file located in the project root folder in your browser to:
- Preview all generated covers.
- Copy the JSON metadata URL.
- Download the generated JSON files.

## Customization

- **Fonts**: Add custom `.otf` or `.ttf` fonts to `generator/assets/fonts/`.
- **Backgrounds**: Add new background images to `generator/assets/bg_images/`.
