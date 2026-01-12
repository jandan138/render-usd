import os, json, sys
from PIL import Image, ImageDraw, ImageFont
from typing import Dict, Optional
from natsort import natsorted


from render_usd.utils.common_utils.images_utils import concatenate_images

def add_text_below_image(
    image: Image.Image, 
    text: str, 
    font_size: int = 24,
    text_color: tuple = (0, 0, 0),
    background_color: tuple = (255, 255, 255),
    padding: int = 10
) -> Image.Image:

    # Try to load a font, fall back to default if not available
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except (IOError, OSError):
        try:
            font = ImageFont.load_default()
        except:
            font = None
    
    # Calculate text dimensions
    if font:
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    else:
        # Fallback estimation if font loading fails
        text_width = len(text) * 10
        text_height = 16
    
    # Create a copy of the original image to modify
    new_image = image.copy()
    img_width, img_height = new_image.size
    
    # Draw text directly on the image at the bottom
    draw = ImageDraw.Draw(new_image)
    text_x = (img_width - text_width) // 2  # Center horizontally
    text_y = img_height - text_height - padding  # Position at bottom with padding
    
    # Draw background rectangle for text if needed
    if background_color != (255, 255, 255):
        rect_coords = [
            text_x - padding//2, 
            text_y - padding//2, 
            text_x + text_width + padding//2, 
            text_y + text_height + padding//2
        ]
        draw.rectangle(rect_coords, fill=background_color)
    
    # Add text
    if font:
        draw.text((text_x, text_y), text, fill=text_color, font=font)
    else:
        draw.text((text_x, text_y), text, fill=text_color)
    
    return new_image


def visualize_caption_result(
    category_result: Dict[str, str], 
    image_dir: str, 
    save_path: str,
    font_size: int = 24,
    row_number: int = 3,
    show_index: int = 0
) -> None:
    """
    Visualize caption results by adding category text below each image.
    
    Args:
        category_result: Dictionary mapping object names to categories
        image_dir: Directory containing object image folders
        save_path: Path to save the visualization results
        font_size: Font size for category text
        images_per_row: Number of images per row in the output
    """
    save_dir = os.path.dirname(save_path)
    os.makedirs(save_dir, exist_ok=True)
    
    images = []
    for object_name, category in category_result.items():
        object_images_dir = os.path.join(image_dir, object_name) 
        # Get all image files and sort them naturally
        image_files = os.listdir(object_images_dir)
        sorted_images = natsorted(image_files)
        
        # Process each image: add category text below
        show_text = f"{category}"
        show_image_path = os.path.join(object_images_dir, sorted_images[show_index])
        show_image = Image.open(show_image_path)
        show_image = add_text_below_image(show_image, show_text, font_size=font_size)
        
        images.append(show_image)
        
    # Save the result
    result_image = concatenate_images(images, row_number)
    result_image.save(save_path)
    print(f"[GRGenerator: Visualize Utils.visualize_caption_result] Saved visualization to {save_path}")


if __name__ == "__main__":
    category_result_path = "/cpfs/user/caopeizhou/data/GRScenes/instances/part1/101_usd/0001/auto_annotation/category_result_by_Qwen2.5-VL-72B-Instruct.json"
    image_dir = "/cpfs/user/caopeizhou/data/GRScenes/instances/part1/101_usd/0001/thumbnails/multi_views"
    save_path = "/cpfs/user/caopeizhou/data/GRScenes/instances/part1/101_usd/0001/auto_annotation/category_result_by_Qwen2.5-VL-72B-Instruct_visualization.png"
    with open(category_result_path, 'r') as f:
        category_result = json.load(f)
    visualize_caption_result(category_result, image_dir, save_path, row_number=10)