import os
import random
import argparse
import requests
import json
from PIL import Image, ImageDraw

# URL of the JSON file with the gradients
GRADIENTS_JSON_URL = "https://raw.githubusercontent.com/ghosh/uiGradients/master/gradients.json"

def hex_to_rgb(hex_color):
    """Converts a hex string (e.g., '#FF0000' or 'FF0000') to an (r, g, b) tuple."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_gradients_list():
    """
    Downloads the gradients.json file and returns the list of gradients.
    """
    print("Downloading gradients list from GitHub...")
    try:
        response = requests.get(GRADIENTS_JSON_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error downloading gradients list: {e}")
        return []

def create_linear_gradient(width, height, start_color, end_color):
    """
    Creates an image with a linear diagonal gradient.
    """
    img = Image.new('RGB', (width, height), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Gradient from Top-Left to Bottom-Right
    # We iterate over the sum of x + y = k
    # k ranges from 0 to width + height
    steps = width + height
    for k in range(steps):
        t = k / steps
        r = int(start_color[0] + (end_color[0] - start_color[0]) * t)
        g = int(start_color[1] + (end_color[1] - start_color[1]) * t)
        b = int(start_color[2] + (end_color[2] - start_color[2]) * t)
        color = (r, g, b)
        
        # Find intersection points of line x + y = k with the rectangle boundaries
        points = []
        
        # Intersection with Top edge (y=0) -> x=k
        if 0 <= k < width:
            points.append((k, 0))
        
        # Intersection with Left edge (x=0) -> y=k
        if 0 <= k < height:
            points.append((0, k))
            
        # Intersection with Bottom edge (y=height-1) -> x = k - (height-1)
        # Note: We use height-1 to be exact on the pixel grid
        if 0 <= k - (height - 1) < width:
            points.append((k - (height - 1), height - 1))
            
        # Intersection with Right edge (x=width-1) -> y = k - (width-1)
        if 0 <= k - (width - 1) < height:
            points.append((width - 1, k - (width - 1)))
        
        # Remove exact duplicates
        unique_points = sorted(list(set(points)))
        
        if len(unique_points) >= 2:
            # Draw line between the two furthest points found
            p1 = unique_points[0]
            p2 = unique_points[-1]
            # width=2 to prevent gaps
            draw.line([p1, p2], fill=color, width=2)
            
    return img

def main():
    parser = argparse.ArgumentParser(description="Create gradient images from uiGradients.")
    parser.add_argument("--width", type=int, help="Width of the image", default=1920)
    parser.add_argument("--height", type=int, help="Height of the image", default=1080)
    parser.add_argument("--count", type=int, help="Number of images to create", default=5)
    parser.add_argument("--output", type=str, help="Output directory", default="gradient_images")
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"Created directory: {args.output}")

    # Fetch gradient list
    gradients_list = get_gradients_list()
    if not gradients_list:
        print("No gradients found. Exiting.")
        return

    print(f"Generating {args.count} images at {args.width}x{args.height}...")

    for i in range(args.count):
        # Pick a random gradient from the list
        gradient_data = random.choice(gradients_list)
        name = gradient_data.get('name', f'gradient_{i}')
        colors = gradient_data.get('colors', [])

        if len(colors) < 2:
            print(f"Skipping {name} (not enough colors)")
            continue

        # We take the first and the last color to ensure a distinctive gradient
        # (Some definitions in that JSON have more than 2 colors)
        c1_hex = colors[0]
        c2_hex = colors[-1] 
        
        c1 = hex_to_rgb(c1_hex)
        c2 = hex_to_rgb(c2_hex)
        
        img = create_linear_gradient(args.width, args.height, c1, c2)
        
        # Filename using index
        filename = f"{i+1}.png"
        filepath = os.path.join(args.output, filename)
        
        img.save(filepath)
        print(f"Saved {filepath} ({name})")

    print("Done!")

if __name__ == "__main__":
    main()
