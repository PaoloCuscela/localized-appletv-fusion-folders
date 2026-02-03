import os
import argparse
from PIL import Image, ImageDraw, ImageFont, ImageFilter

def add_text_to_image(input_path, text, output_dir=None, font_size=40, font_path=None, target_width=None, target_height=None, specific_output_path=None, padding_y=80, padding_x=80):
    """
    Adds text to the bottom-left corner of an image.
    If target_width and target_height are provided, crops/resizes the image first.
    specific_output_path: If provided, saves to this exact path (ignoring output_dir and auto-naming).
    """
    try:
        img = Image.open(input_path).convert("RGBA")


        # Resize and Crop logic if dimensions provided
        if target_width and target_height:
            width, height = img.size
            aspect_ratio_img = width / height
            aspect_ratio_target = target_width / target_height
            
            if aspect_ratio_img > aspect_ratio_target:
                # Image is wider than target. Resizing based on height to fill area
                new_height = target_height
                new_width = int(new_height * aspect_ratio_img)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Center Crop Width
                left = (new_width - target_width) / 2
                top = 0
                right = (new_width + target_width) / 2
                bottom = target_height
                
                img = img.crop((left, top, right, bottom))
            else:
                # Image is taller/narrower than target. Resizing based on width to fill area
                new_width = target_width
                new_height = int(new_width / aspect_ratio_img)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Center Crop Height
                left = 0
                top = (new_height - target_height) / 2
                right = target_width
                bottom = (new_height + target_height) / 2
                
                img = img.crop((left, top, right, bottom))

        width, height = img.size
        
        draw = ImageDraw.Draw(img)
        
        # Load font
        font = None # Initialize to handle definition
        try:
            if font_path:
                print(f"Attempting to load custom font: {font_path} with size {font_size}")
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    print(f"Successfully loaded custom font: {font.getname()}")
                except Exception as e:
                    print(f"Error: Could not load the custom font at '{font_path}'.")
                    raise e
            else:
                print(f"No custom font provided. Attempting to load default font with size {font_size}")
                # Try to load a nice default font for macOS/Linux/Windows
                # Common locations/names
                try:
                    font = ImageFont.truetype("Arial.ttf", font_size)
                except IOError:
                    # Fallbacks for different OS
                    try:
                        font = ImageFont.truetype("/Library/Fonts/Arial.ttf", font_size) # macOS
                    except IOError:
                        try:
                             font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size) # Linux
                        except IOError:
                            print("Warning: Could not load specific font. Using default (might be small).")
                            font = ImageFont.load_default()
                            
        except Exception as e:
            if font_path:
                # If a specific font was requested and failed, stop and report error
                print(f"Critical Error: Failed to load requested font '{font_path}': {e}")
                return
            else:
                print(f"Error loading font: {e}. Using default.")
                font = ImageFont.load_default()

        # Helper to get size of a single line of text
        def get_text_size(txt):
            if hasattr(draw, "textbbox"):
                bbox = draw.textbbox((0, 0), txt, font=font)
                return bbox[2] - bbox[0], bbox[3] - bbox[1]
            else:
                return draw.textsize(txt, font=font)

        # Position: Bottom Left with padding
        # padding_x and padding_y are passed as arguments
        max_width = width - (padding_x * 2)

        # Wrap text
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            w, h = get_text_size(test_line)
            if w <= max_width:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word) # Force word even if too long
                    current_line = []
        if current_line:
            lines.append(' '.join(current_line))
            
        if not lines:
            lines = [text]

        # Calculate line height (using a reference character)
        ref_w, ref_h = get_text_size("Mg") 
        line_height = ref_h * 1.2 # 1.2 line height
        
        total_text_height = len(lines) * line_height
        
        x = padding_x
        # Start Y (Top of the text block)
        y = height - total_text_height - padding_y - 10 # Extra 10 for descenders

        # Create shadow layer for "light and expanded" shadow
        shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        
        # Shadow settings
        shadow_color = (0, 0, 0, 80) 
        blur_radius = 8
        shadow_stroke = 6
        
        # Draw shadow text
        cur_y = y
        for line in lines:
            shadow_draw.text((x, cur_y), line, font=font, fill=shadow_color, stroke_width=shadow_stroke, stroke_fill=shadow_color)
            cur_y += line_height
        
        # Apply blur
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(blur_radius))
        
        # Composite shadow onto image
        img = Image.alpha_composite(img, shadow_layer)
        draw = ImageDraw.Draw(img) # New draw interface (though we won't draw directly on img for the gradient text)

        # --- Gradient Text ---
        
        # 1. Create a mask for the text
        # This will be a black/white image where white is the text shape
        text_mask = Image.new('L', img.size, 0)
        mask_draw = ImageDraw.Draw(text_mask)
        
        cur_y = y
        for line in lines:
            mask_draw.text((x, cur_y), line, font=font, fill=255)
            cur_y += line_height
        
        # 2. Create the vertical gradient fill
        # It needs to cover the text area. We can make it the size of the whole image or just the text bbox.
        # Let's make it the size of the whole image for simplicity in pasting.
        gradient = Image.new('RGBA', img.size, (0,0,0,0))
        gradient_draw = ImageDraw.Draw(gradient)
        
        # Define colors
        top_color = (255, 255, 255, 255) # White
        bottom_color = (200, 200, 200, 255) # Light Gray
        
        # Draw gradient only within the text vertical range
        # y is top of text, y + text_height is bottom
        # We add some buffer to ensure covers fully
        g_start_y = y
        g_end_y = y + total_text_height + 30 # +30 buffer
        
        for i_y in range(int(g_start_y), int(g_end_y)):
            # Calculate ratio (0 at top, 1 at bottom)
            ratio = (i_y - g_start_y) / (g_end_y - g_start_y)
            ratio = max(0, min(1, ratio)) # Clamp
            
            # Interpolate color
            r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
            g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
            b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
            
            # Draw horizontal line across the whole image width at this y
            gradient_draw.line([(0, i_y), (width, i_y)], fill=(r, g, b, 255))
            
        # 3. Composite gradient using the text mask
        # Paste the gradient onto the main image, using the text_mask as the alpha mask
        img.paste(gradient, (0, 0), text_mask)
        
        print(f"Drawing gradient text '{text}' with font: {font.getname()}")

        # Save output
        if specific_output_path:
            output_path = specific_output_path
            # Ensure dir exists
            out_dir = os.path.dirname(output_path)
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir)
        else:
            if not output_dir:
                output_dir = "output_def"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            # Create safe filename from text
            safe_text = "".join([c for c in text if c.isalnum() or c in (' ', '-', '_')]).strip().replace(" ", "_")
            filename = f"{safe_text}.png"
            output_path = os.path.join(output_dir, filename)
        
        # Convert back to RGB to save as PNG/JPG without issues if alpha not needed, 
        # but PNG supports RGBA.
        # If output path ends with .jpg or .jpeg, convert to RGB
        if output_path.lower().endswith(('.jpg', '.jpeg')):
            img.convert("RGB").save(output_path, quality=95)
        else:
            img.save(output_path)
            
        print(f"Saved image with text to: {output_path}")
        
    except Exception as e:
        print(f"Error processing {input_path}: {e}")
        # Re-raise to let caller know
        raise e

def main():
    parser = argparse.ArgumentParser(description="Add text to the bottom-left of an image.")
    parser.add_argument("input_image", type=str, help="Path to the input image")
    parser.add_argument("--text", type=str, required=True, help="Text to write on the image")
    parser.add_argument("--output", type=str, default="output_images", help="Output directory")
    parser.add_argument("--fontsize", type=int, default=60, help="Font size")
    parser.add_argument("--font", type=str, default=None, help="Path to a custom .ttf font file")
    parser.add_argument("--padding_x", type=int, default=40, help="Horizontal padding")
    parser.add_argument("--padding_y", type=int, default=160, help="Vertical padding")

    args = parser.parse_args()

    add_text_to_image(args.input_image, args.text, args.output, args.fontsize, args.font, padding_y=args.padding_y, padding_x=args.padding_x)

if __name__ == "__main__":
    main()
