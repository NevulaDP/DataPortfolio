from PIL import Image, ImageDraw, ImageFont
import os

def create_logo():
    # Create a 200x200 canvas
    size = (400, 400) # High res
    img = Image.new('RGBA', size, (255, 255, 255, 0)) # Transparent background
    draw = ImageDraw.Draw(img)

    # Draw a circle
    # Color: Streamlit Red/Pink #FF4B4B
    primary_color = "#FF4B4B"
    draw.ellipse([20, 20, 380, 380], fill=primary_color)

    # Draw Text "JD" (Junior Data)
    # Since we might not have custom fonts, we'll use a basic path or just simple shapes if needed.
    # But PIL default font is tiny. Let's try to load a system font or just draw simple shapes.
    # Drawing a simple "Bar Chart" icon instead of text to be safe and professional.

    # Bar 1
    draw.rectangle([100, 250, 150, 300], fill="white")
    # Bar 2
    draw.rectangle([175, 180, 225, 300], fill="white")
    # Bar 3
    draw.rectangle([250, 110, 300, 300], fill="white")

    img.save("logo.png", "PNG")
    print("Logo generated: logo.png")

if __name__ == "__main__":
    create_logo()
