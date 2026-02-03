import os
import json
import shutil

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) # generator/
PROJECT_ROOT = os.path.dirname(BASE_DIR) # root
RESOURCES_DIR = os.path.join(PROJECT_ROOT, "resources")
OUTPUT_HTML = os.path.join(PROJECT_ROOT, "index.html")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AppleTV Localized Fusion Folders</title>
    <style>
        :root {{
            --bg-color: #121212;
            --card-bg: #1c1c1e;
            --text-color: #f5f5f7;
            --secondary-text: #86868b;
            --accent: #2997ff;
            --border: #333;
        }}
        body {{
            margin: 0;
            padding: 40px;
            background: var(--bg-color);
            color: var(--text-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        
        header {{ margin-bottom: 60px; text-align: center; }}
        h1 {{ font-size: 3rem; font-weight: 700; background: linear-gradient(135deg, #fff 0%, #888 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0; }}
        .subtitle {{ color: var(--secondary-text); margin-top: 10px; font-size: 1.2rem; }}

        .lang-section {{ margin-bottom: 80px; }}
        .lang-title {{ font-size: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 30px; text-transform: capitalize; }}
        
        .type-section {{ margin-bottom: 50px; padding-left: 20px; }}
        .type-header {{ display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }}
        .type-title {{ font-size: 1.5rem; font-weight: 600; color: var(--accent); }}
        
        .actions {{ display: flex; gap: 10px; }}
        .btn {{
            background: rgba(255,255,255,0.1);
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.2s;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn:hover {{ background: rgba(255,255,255,0.2); transform: translateY(-1px); }}
        .btn:active {{ transform: translateY(0); }}
        .btn-copy {{ background: var(--accent); }}
        .btn-copy:hover {{ background: #0077ed; }}

        .carousel-container {{ position: relative; }}
        .carousel {{
            display: flex;
            gap: 20px;
            overflow-x: auto;
            padding: 10px 0 30px 0;
            scroll-snap-type: x mandatory;
            scroll-behavior: smooth;
            -webkit-overflow-scrolling: touch;
        }}
        .carousel::-webkit-scrollbar {{ height: 8px; }}
        .carousel::-webkit-scrollbar-track {{ background: transparent; }}
        .carousel::-webkit-scrollbar-thumb {{ background: #444; border-radius: 4px; }}
        
        .card {{
            flex: 0 0 auto;
            width: 200px;
            scroll-snap-align: start;
            background: var(--card-bg);
            border-radius: 12px;
            overflow: hidden;
            transition: transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            position: relative;
        }}
        .card:hover {{ transform: scale(1.05); z-index: 2; box-shadow: 0 10px 20px rgba(0,0,0,0.4); }}
        
        .card-img-wrapper {{ width: 100%; overflow: hidden; background: #000; }}
        .card-poster .card-img-wrapper {{ aspect-ratio: 2/3; }}
        .card-wide .card-img-wrapper {{ aspect-ratio: 16/9; }}
        .card-wide {{ width: 300px; }}

        .card img {{ width: 100%; height: 100%; object-fit: cover; transition: opacity 0.3s; }}
        
        .card-info {{ padding: 12px; }}
        .card-name {{ font-weight: 600; font-size: 0.95rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-bottom: 4px; }}
        .card-meta {{ font-size: 0.75rem; color: var(--secondary-text); }}

        .toast {{
            position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%);
            background: rgba(0,0,0,0.8); color: white; padding: 10px 24px; border-radius: 30px;
            font-size: 0.9rem; pointer-events: none; opacity: 0; transition: opacity 0.3s;
            backdrop-filter: blur(10px); z-index: 1000;
        }}
        .toast.show {{ opacity: 1; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AppleTV Localized Fusion Folders</h1>
            <div class="subtitle">A list of localized folder to import into Fusion App</div>
        </header>

        {content}

    </div>
    
    <div id="toast" class="toast">Copied to clipboard!</div>

    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                showToast("Copied path to clipboard!");
            }});
        }}

        function showToast(msg) {{
            const t = document.getElementById('toast');
            t.textContent = msg;
            t.classList.add('show');
            setTimeout(() => t.classList.remove('show'), 2000);
        }}
    </script>
</body>
</html>
"""

def generate_gallery():
    if not os.path.exists(RESOURCES_DIR):
        print("Resources directory not found.")
        return

    sections_html = ""
    
    # Iterate Languages
    languages = sorted([d for d in os.listdir(RESOURCES_DIR) if os.path.isdir(os.path.join(RESOURCES_DIR, d))])
    
    if not languages:
        sections_html = "<p style='text-align:center; color:#666;'>No generated resources found yet.</p>"

    # Emoji mapping
    FLAGS = {
        'it': '🇮🇹', 'en': '🇺🇸', 'fr': '🇫🇷', 'de': '🇩🇪', 'es': '🇪🇸', 
        'ja': '🇯🇵', 'ko': '🇰🇷', 'zh': '🇨🇳', 'ru': '🇷🇺', 'pt': '🇵🇹',
        'nl': '🇳🇱', 'pl': '🇵🇱', 'sv': '🇸🇪', 'da': '🇩🇰', 'fi': '🇫🇮',
        'no': '🇳🇴', 'el': '🇬🇷', 'tr': '🇹🇷', 'cs': '🇨🇿', 'hu': '🇭🇺',
        'ro': '🇷🇴', 'uk': '🇺🇦', 'be': '🇧🇪', 'at': '🇦🇹', 'ch': '🇨🇭'
    }

    for lang in languages:
        lang_path = os.path.join(RESOURCES_DIR, lang)
        # Use flag if available, else uppercase code
        display_lang = FLAGS.get(lang.lower(), lang.upper())
        
        sections_html += f'<div class="lang-section"><div class="lang-title">{display_lang}</div>'
        
        # Iterate Types (movie, tv)
        for media_type in ['movie', 'tv']:
            type_path = os.path.join(lang_path, media_type)
            json_file = os.path.join(type_path, f"{lang}_{media_type}.json")
            
            if os.path.exists(json_file):
                with open(json_file, 'r', encoding='utf-8') as f:
                    try:
                        items = json.load(f)
                    except:
                        items = []
                
                if not items:
                    continue

                rel_json_path = f"https://raw.githubusercontent.com/PaoloCuscela/localized-appletv-fusion-folders/main/resources/{lang}/{media_type}/{lang}_{media_type}.json"
                
                # Determine card style based on first item or media_type
                # Always use vertical poster style as requested (2:3)
                is_wide = False
                card_class = "card-poster"
                type_label = "TV Shows" if media_type == 'tv' else "Movies"

                # Cards HTML
                cards_html = ""
                for item in items:
                    name = item.get('name', 'Unknown')
                    img_url = item.get('backgroundImageURL', '')
                    
                    # Resolve Image Src
                    if img_url.startswith('http'):
                        src = img_url
                    else:
                        # Assume filename, relative to index.html (in Resources)
                        src = f"{img_url}"
                    
                    # Just in case it's just a filename in local json without baseurl
                    
                    cards_html += f"""
                    <div class="card {card_class}" title="{name}">
                        <div class="card-img-wrapper">
                            <img src="{src}" alt="{name}" loading="lazy">
                        </div>
                    </div>
                    """

                sections_html += f"""
                <div class="type-section">
                    <div class="type-header">
                        <div class="type-title">{type_label} <span style="font-size:0.8em; color:var(--secondary-text); font-weight:400; margin-left:10px;">({len(items)})</span></div>
                        <div class="actions">
                            <button class="btn btn-copy" onclick="copyToClipboard('{rel_json_path}')">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                                Copy URL
                            </button>
                            <a href="{rel_json_path}" download class="btn">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                                Download JSON
                            </a>
                        </div>
                    </div>
                    <div class="carousel-container">
                        <div class="carousel">
                            {cards_html}
                        </div>
                    </div>
                </div>
                """
        
        sections_html += '</div>'

    final_html = HTML_TEMPLATE.format(content=sections_html)
    
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(final_html)
    
    print(f"Generated gallery at: {OUTPUT_HTML}")

if __name__ == "__main__":
    generate_gallery()