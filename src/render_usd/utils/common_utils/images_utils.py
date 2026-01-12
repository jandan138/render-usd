import numpy as np
from io import BytesIO
import base64
from PIL import Image
from typing import List, Tuple, Union
from pycocotools import mask as maskUtils
import json
import os



# semantic mask mapping tools
def colorize_instances(mask, colors=None):
    h, w = mask.shape
    color_mask = np.zeros((h, w, 3), dtype=np.uint8)
    instance_ids = np.unique(mask)
    if colors is None:
        np.random.seed(42)
        colors = np.random.randint(0, 256, size=(instance_ids.max() + 1, 3), dtype=np.uint8)
    for idx in instance_ids:
        if idx == 0: 
            continue
        color_mask[mask == idx] = colors[idx]
    return color_mask

def colorize_instance_mask_with_idlist(instance_mask, instance_id_list=None):
    h, w = instance_mask.shape
    color_mask = np.zeros((h, w, 3), dtype=np.uint8)
    instance_ids = np.unique(instance_mask)
    np.random.seed(42)
    colors = np.random.randint(0, 256, size=(instance_ids.max() + 1, 3), dtype=np.uint8)
    if instance_id_list is not None:
        valid_ids = set(instance_id_list)
        for idx in instance_ids:
            if idx == 0:
                color_mask[instance_mask == idx] = [255, 0, 0]
            if idx in valid_ids:
                color_mask[instance_mask == idx] = colors[idx]
            else:
                color_mask[instance_mask == idx] = [255, 255, 255]
    else:
        for idx in instance_ids:
            if idx == 0:
                continue
            color_mask[instance_mask == idx] = colors[idx]
    return color_mask


def encode_mask_to_coco_format_rle(instance_mask, instance_id):

    binary_mask = (instance_mask == instance_id).astype(np.uint8)
    binary_mask = np.asfortranarray(binary_mask)
    rle = maskUtils.encode(binary_mask)
    if isinstance(rle['counts'], bytes):
        rle['counts'] = rle['counts'].decode('utf-8')
    return rle

def visualize_RLE(rle_encoding, save_path):
    mask = decode_RLE(rle_encoding)
    if mask is None:
        return
    
    mask_img = (mask * 255).astype(np.uint8)
    os.makedirs(os.path.dirname(save_path) or '.', exist_ok=True)
    Image.fromarray(mask_img).save(save_path)
    
    if isinstance(rle_encoding, str):
        rle = json.loads(rle_encoding)
    else:
        rle = rle_encoding
    
    height, width = rle['size']
    foreground_pixels = np.sum(mask > 0)
    total_pixels = height * width
    
    print(f"Saved to: {save_path}")
    print(f"Size: {width} x {height}")
    print(f"Foreground: {foreground_pixels} ({foreground_pixels/total_pixels*100:.2f}%)")

def decode_RLE(rle_encoding):
    try:
        if isinstance(rle_encoding, str):
            rle = json.loads(rle_encoding)
        elif isinstance(rle_encoding, dict):
            rle = rle_encoding
        else:
            raise ValueError("RLE encoding must be dict or JSON string")
        
        if 'counts' not in rle or 'size' not in rle:
            raise ValueError("RLE must contain 'counts' and 'size' fields")
        
        if isinstance(rle['counts'], list):
            rle = maskUtils.frPyObjects(rle, rle['size'][0], rle['size'][1])
        
        mask = maskUtils.decode(rle)
        return mask
        
    except Exception as e:
        print(f"Failed to decode RLE: {e}")
        return None


# concatenate images into a single image
def concatenate_images(
    images_input: Union[List[str], List[Image.Image]], 
    row_number: int = 2
) -> Image.Image:

    if not images_input:
        raise ValueError("[GRGenerator: Images Utils.concatenate_images] Input list cannot be empty")
    
    # Convert input to PIL Images
    images = []
    first_item = images_input[0]
    
    if isinstance(first_item, str):
        # Input is a list of file paths
        for path in images_input:
            assert isinstance(path, str), "[GRGenerator: Images Utils.concatenate_images] All items must be strings when first item is a string"
            image = Image.open(path)
            images.append(image)
    elif isinstance(first_item, Image.Image):
        # Input is a list of PIL Images
        for img in images_input:
            assert isinstance(img, Image.Image), "[GRGenerator: Images Utils.concatenate_images] All items must be PIL Image objects when first item is an Image"
            images.append(img)
    else:
        raise TypeError(f"[GRGenerator: Images Utils.concatenate_images] Unsupported input type: {type(first_item)}. Expected str or PIL.Image.Image")
    
    # Validate that all images have the same size
    base_size = images[0].size
    print(f"[DEBUG] Base size: {base_size}")
    if any(img.size != base_size for img in images):
        raise ValueError("[GRGenerator: Images Utils.concatenate_images] All images must have the same size")
    
    # Calculate grid dimensions
    image_width, image_height = base_size
    num_images_per_row = len(images) // row_number + (len(images) % row_number > 0)
    
    new_image_width = image_width * num_images_per_row
    new_image_height = image_height * row_number

    # Create the output image
    new_image = Image.new('RGB', (new_image_width, new_image_height))
    
    # Place images in the grid
    for idx, image in enumerate(images):
        row = idx // num_images_per_row
        col = idx % num_images_per_row
        position = (col * image_width, row * image_height)
        new_image.paste(image, position)
        
    return new_image

# Function to encode image to base64
def encode_image(image_path):
    image = Image.open(image_path).convert('RGB')
    if image:
        img_resized = image.resize((256, 256))
        buffer = BytesIO()
        img_resized.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        return base64.b64encode(img_bytes).decode('utf-8')

def draw_bbox2d(image, bbox2d):
    image = np.array(image)
    x_min = int(bbox2d[1])
    y_min = int(bbox2d[2])
    x_max = int(bbox2d[3])
    y_max = int(bbox2d[4])
    image[y_min:y_min+2, x_min:x_max] = [255, 0, 0]
    image[y_max-2:y_max, x_min:x_max] = [255, 0, 0]
    image[y_min:y_max, x_min:x_min+2] = [255, 0, 0]
    image[y_min:y_max, x_max-2:x_max] = [255, 0, 0]
    return image