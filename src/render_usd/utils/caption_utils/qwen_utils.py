import os
from qwen_vl_utils import process_vision_info
from natsort import natsorted
from typing import List
from ..common_utils.images_utils import concatenate_images



# ------------------------------------------------------------------------------
#                           IMAGE PATH UTILS  
# ------------------------------------------------------------------------------

# Get image paths based on prompt type
def _get_image_paths(object_path: str, prompt_type: str) -> List[str]:
    if prompt_type == "find_canonical_front_view_prompt":
        interval = 1
        reverse_index = None
    elif prompt_type == "is_symmetric_object_prompt":
        interval = 4
        reverse_index = None
    elif prompt_type in ["classify_object_category_prompt", "describe_object_prompt_MMScan", "extract_object_attributes_prompt"]:
        interval = 8
        reverse_index = -3
    else:
        interval = 1
        reverse_index = None
        
    images = os.listdir(object_path)
    sorted_images = natsorted(images)
    # print(f"[DEBUG] Sorted images:{sorted_images}")
    images = sorted_images[:24:interval] + (sorted_images[reverse_index:] if reverse_index else [])
    image_paths = [os.path.join(object_path, image) for image in images]
    return image_paths

# Get merged image path based on single image path
def _get_merge_views_path(image_path: str) -> str:
    # Extract component paths
    object_name = os.path.basename(os.path.dirname(image_path))
    view_dir = os.path.dirname(os.path.dirname(image_path))
    
    # Create merged views directory if it doesn't exist
    merge_dir = os.path.join(os.path.dirname(view_dir), "merged_views")
    os.makedirs(merge_dir, exist_ok=True)
    
    # Construct final merged image path
    merged_path = os.path.join(merge_dir, f"{object_name}.png")
    return merged_path

# Process image paths based on merge setting
def _process_image_paths(image_paths: list[str], image_merge: bool) -> list[str]:
    if not image_merge:
        return image_paths
    
    # Get merged image path
    merge_image_path = _get_merge_views_path(image_paths[0])
    
    # Check if merged image already exists
    if os.path.exists(merge_image_path):
        print(f"[GRGenerator: Qwen Utils._process_images] Using existing merged image: {merge_image_path}")
        return [merge_image_path]
    
    # Create merged image
    print(f"[GRGenerator: Qwen Utils._process_images] Merging {len(image_paths)} images into: {merge_image_path}")
    try:
        merged_image = concatenate_images(image_paths)
        merged_image.save(merge_image_path)
        print(f"[GRGenerator: Qwen Utils._process_images] Successfully saved merged image to: {merge_image_path}")
        return [merge_image_path]
    except Exception as e:
        print(f"[GRGenerator: Qwen Utils._process_images] Failed to merge images: {e}")
        print(f"[GRGenerator: Qwen Utils._process_images] Falling back to original image paths")
        return image_paths


# ------------------------------------------------------------------------------
#                          CAPTION PROMPT UTILS
# ------------------------------------------------------------------------------

SUPPORTED_PROMPT_TYPES = [
    "find_canonical_front_view_prompt", 
    "is_symmetric_object_prompt", 
    "classify_object_category_without_background_prompt", 
    "classify_object_category_with_background_prompt", 
    "describe_object_with_background_prompt", 
    "describe_object_without_background_prompt", 
    "polish_description_prompt_MMScan", 
    "extract_object_attributes_prompt", 
    "object_cognition_QA_with_background_prompt", 
    "object_cognition_QA_without_background_prompt", 
]

# Text user prompt based on prompt type and number of images
def _compose_user_prompt(image_number: int, prompt_type: str, image_merge: bool=False, object_additional_info: List[str]=None) -> str:
    assert prompt_type in SUPPORTED_PROMPT_TYPES, \
    f"[GRGenerator: Qwen Utils._compose_user_prompt] Invalid prompt_type option: {prompt_type}, supported prompt types: {SUPPORTED_PROMPT_TYPES}"
    
    if   prompt_type == "find_canonical_front_view_prompt":
        user_prompt = (
            f"The 3D asset is represented by {image_number} separate images showing different views of the object.\n"
            f"Identify the canonical front view index (0-{image_number-1}) from these {image_number} orthogonal images.\n"
            "Using 3D modeling standards. Output only the integer with no additional text or formatting."
        )
    elif prompt_type == "is_symmetric_object_prompt":
        user_prompt = (
            # "Given a set of multi-view images about the same 3D object, please determine whether the object has a clear front side. If the object has a clear font side and the confidence is higher than 50%, return 1 without any other words, else return 0 without any other words."
            f"You are given {image_number} images showing a 360-degree rotation of the same object. Please analyze these images and determine:\n"
            "Does the object appear nearly identical from all angles — such as being spherical, cylindrical, or highly symmetric?\n"
            "Based on your analysis, output exactly one of the following:\n"
            "- '0': If the object appear nearly identical from all angles.\n"
            "- '1': Else.\n"
            "Do NOT provide any additional explanation. Only return one number: 0, 1"
        )
    elif prompt_type == "classify_object_category_without_background_prompt":
        multi_image_query = f"You are presented with {image_number} distinct rendered views of an indoor object captured against a neutral gray-white background."
        merge_image_query = "This composite image displays multiple rendered views of the same object from different perspectives."
        image_query = merge_image_query if image_merge else multi_image_query
        categories_query = "Analyze the object and classify it into a single, precise category based on its primary function and characteristics."
        output_query = "Provide ONLY the category name as your response - no additional text, explanation, or formatting."
        user_prompt = f"{image_query} {categories_query} {output_query}"
    elif prompt_type == "classify_object_category_with_background_prompt":
        user_prompt = []
        cad_model_prompt = "The following four images are the same object with a red bounding box which we need to describe."
        background_prompt = "The following images highlight the target object with a red bounding box which is the same as the first four images."
        task_prompt = "Analyze the object and classify it into a single, precise category based on its primary function and characteristics. \
                       Provide ONLY the category name as your response - no additional text, explanation, or formatting. \
                       If you output the wrong information you will be fired."
        user_prompt = [cad_model_prompt, background_prompt, task_prompt]
    elif prompt_type == "describe_object_without_background_prompt":
        multi_image_query = f"You are presented with {image_number} distinct rendered views of an indoor object captured against a neutral gray-white background."
        merge_image_query = "This composite image displays multiple rendered views of the same object from different perspectives."
        image_query = merge_image_query if image_merge else multi_image_query
        description_query = (
            "Provide a comprehensive description of this object using clear, detailed sentences. Focus on the following key aspects:\n"
            "- Physical appearance: precise shape, form, and predominant colors\n"
            "- Material properties: surface texture, material type, and finish quality\n" 
            "- Scale and proportions: relative size compared to typical objects of this type\n"
            "- Current state: configuration of movable components (doors, drawers, etc.)\n"
          # "- Spatial orientation: positioning and alignment in the scene\n"
            "- Functional purpose: primary intended use and operational characteristics\n"
            "- Design features: notable structural elements and distinctive details\n"
            "Ensure each sentence contains concrete, observable details rather than subjective interpretations."
        )
        output_query = "Generate 3-5 informative sentences with specific, factual descriptions. Use clear, objective language without bullet points or line breaks."
        user_prompt = f"{image_query} {description_query} {output_query}"
    elif prompt_type == "describe_object_with_background_prompt":
        user_prompt = []
        cad_model_prompt = "The following four images are the same object with a red bounding box which we need to describe."
        background_prompt = "The following images highlight the target object with a red bounding box which is the same as the first four images."
        task_prompt = (
            "Provide a comprehensive description of this object using clear, detailed sentences. Focus on the following key aspects:\n"
            "- Physical appearance: precise shape, form, and predominant colors\n"
            "- Material properties: surface texture, material type, and finish quality\n" 
            "- Scale and proportions: relative size compared to typical objects of this type\n"
            "- Current state: configuration of movable components (doors, drawers, etc.)\n"
            "- Spatial orientation: positioning and alignment in the scene\n"
            "- Functional purpose: primary intended use and operational characteristics\n"
            "- Design features: notable structural elements and distinctive details\n"
            "Ensure each sentence contains concrete, observable details rather than subjective interpretations. \
            Just output the information you are sure of, if you output the wrong information you will be fired. \
            The object in all images is the same; description should focus solely on it, without referencing specific images."
        )
        user_prompt = [cad_model_prompt, background_prompt, task_prompt]
    elif prompt_type == "polish_description_prompt_MMScan":
        user_prompt = (
            "Refine the given description by removing generic or commonplace details, focusing exclusively on the object's distinctive and unique characteristics. "
            "Restructure and enhance the retained content to create a natural, flowing narrative that avoids mechanical or formulaic language. "
            "Target approximately 150 words for the polished description."
        )
    elif prompt_type == "extract_object_attributes_prompt":
        object_in_scene_type = f"{object_additional_info[0]} scene"
        object_category = object_additional_info[-1]
        object_query = (
            f"You are provided with multiple views of a {object_category} object that is placed {object_in_scene_type}. "
        )
        attribute_query = (
            "Analyze the provided image and extract the following structured information. "
            "You MUST respond in strict JSON format with ALL fields required. Do not omit any field.\n\n"
            "Required JSON structure:\n"
            "{\n"
            '  "category": "object type (e.g., plate, cup, bottle)",\n'
            '  "description": "comprehensive description covering: physical appearance (shape, form, colors), material properties (surface texture, finish), scale and proportions, current state (e.g., open/closed components), functional purpose, and distinctive design features. Use concrete, observable details in 3-4 sentences.",\n'
            '  "material": "describe all materials present in the object in detail. For each material, specify which part of the object it applies to (e.g., \'metal handle\', \'ceramic body\', \'rubber base\'). List as many different materials as you can identify. Common materials include: plastic, metal, wood, fabric, ceramic, glass, rubber, stone, paper, foam, leather, cardboard, clay, resin, plaster, polyester, laminate, cotton, steel, aluminum, concrete, stainless steel, gold, silver, etc.",\n'
            '  "dimensions": "length * width * height in meters (e.g., 0.25 * 0.25 * 0.05). Estimate if exact values unknown.",\n'
            '  "mass": "mass in kilograms as a number (e.g., 0.5). Estimate if exact value unknown.",\n'
            '  "placement": "select one or more possible placements from the list: OnFloor, OnObject, OnWall, OnCeiling, OnTable. If multiple placements are possible, list them in descending order of likelihood (e.g., [\'OnTable\', \'OnFloor\', \'OnObject\'])"\n'
            "}\n\n"
            "Important: \n"
            "1. Return ONLY valid JSON, no additional text\n"
            "2. ALL fields are mandatory - provide best estimate if uncertain\n"
            "3. For 'material', describe all materials and their corresponding parts comprehensively\n"
            "4. For 'placement', provide one or more options as an array, ordered by likelihood (most likely first)\n"
            "5. Ensure proper JSON syntax with double quotes"
        )
        user_prompt = f"{object_query} {attribute_query}"
    elif prompt_type == "object_cognition_QA_with_background_prompt":     
        user_prompt = []
        cad_model_prompt = "The following four images are the same object with a red bounding box which we need to describe."
        background_prompt = "The following images highlight the target object with a red bounding box which is the same as the first four images."
        task_prompt = "I need you to generate a series of question pairs for me about this object, using <object> to represent the object in the question pairs. \
                       You can focus on its category, color, material, shape, state, position, function, surface detail, size and other information. \
                       \"Output example\" Question: What color is the <object>? Answer: Mainly red, with some blue as decoration. \
                       Notes: (1) The object in all images is the same; QA should focus solely on it, without referencing specific images. \
                       (2) Ask as many questions as needed—the more details, the better. \
                       (3) Prioritize reasoning and spatial understanding questions over simple ones. \
                       (4) You can ask questions about the target object by associating it with the surrounding objects (e.g., comparison, spatial relationship, functional relationship, quantitative relationship, etc.). \
                       (5) Only output the QA pairs, do not add any other additional responses."
        user_prompt = [cad_model_prompt, background_prompt, task_prompt]
    elif prompt_type == "object_cognition_QA_without_background_prompt":     
        cad_model_prompt = "The following four images are the same object with a red bounding box which we need to describe."
        task_prompt = "I need you to generate a series of question pairs for me about this object, using <object> to represent the object in the question pairs. \
                       You can focus on its category, color, material, shape, state, position, function, surface detail, size and other information. \
                       \"Output example\" Question: What color is the <object>? Answer: Mainly red, with some blue as decoration. \
                       Notes: (1) The object in all images is the same; QA should focus solely on it, without referencing specific images. \
                       (2) Ask as many questions as needed—the more details, the better. \
                       (3) Prioritize reasoning and spatial understanding questions over simple ones. \
                       (4) You can ask questions about the target object by associating it with the surrounding objects (e.g., comparison, spatial relationship, functional relationship, quantitative relationship, etc.). \
                       (5) Only output the QA pairs, do not add any other additional responses."
        user_prompt = f"{cad_model_prompt} {task_prompt}"
    else:
        print(f"Invalid prompt_type option: {prompt_type}")
        return None
    return user_prompt

# Compose referring QA user prompt based on qa list
def _compose_referring_qa_user_prompt(qa_list: List, num_complex_expressions: int = 5) -> str:

    # System instruction
    system_instruction = (
        "You are analyzing indoor objects. Given a series of QAs about a single object (marked as <object>), "
        f"use the information to generate ONE simple referring expression and {num_complex_expressions} diverse situational referring expressions that uniquely identify it.\n\n"
        "Requirements:\n"
        "• Simple referring expression: A concise description using observable attributes such as category, color, material, spatial location, or function.\n"
        f"• Situational referring expressions ({num_complex_expressions} required): Each should involve different aspects of contextual reasoning, "
        "such as functional scenarios, spatial relationships with surrounding objects, comparative reasoning, usage contexts, or interactive situations. "
        "Use diverse sentence structures including questions, conditional statements, and descriptive scenarios.\n\n"
    )
    
    # Format QA pairs
    qa_content = "Input:\n"
    for i, qa_pair in enumerate(qa_list, 1):
        question = qa_pair[0]
        answer = qa_pair[1]
        qa_content += f"Question: {question}\n"
        qa_content += f"Answer: {answer}\n"
        if i < len(qa_list):
            qa_content += "\n"
    
    # Output format instruction with multiple complex expressions
    complex_format = "\n".join([f"[complex expression {i}] <Your situational referring expression {i} here>" 
                                 for i in range(1, num_complex_expressions + 1)])
    
    output_instruction = (
        "\n\nOutput Format:\n"
        "[simple expression] <Your simple referring expression here>\n"
        f"{complex_format}\n\n"
        "Example:\n"
        "[simple expression] The cylindrical light brown pen holder on the top shelf of the desk.\n"
        "[complex expression 1] If I finish writing with a pencil, where is the best place to store it?\n"
        "[complex expression 2] What object on the desk is designed specifically for organizing writing instruments?\n"
        "[complex expression 3] Among all items on the desk, which one serves as a container for pens and has a wooden texture?\n"
        "[complex expression 4] The container that sits next to the laptop and holds multiple writing tools.\n"
        "[complex expression 5] If someone needs to quickly grab a pen for note-taking, which desktop item should they reach for?\n\n"
        "Notes:\n"
        "(1) The simple expression should be a concise, direct description combining key observable attributes.\n"
        f"(2) Generate exactly {num_complex_expressions} complex expressions, each exploring different reasoning aspects (function, spatial relation, comparison, usage scenario, etc.).\n"
        "(3) Each complex expression must be distinct and approach object identification from a different angle.\n"
        "(4) All expressions must uniquely identify the object based on the provided QA information.\n"
        "(5) Complex expressions should use varied sentence structures (questions, conditionals, descriptions, comparisons).\n"
        "(6) Only output the expressions in the specified format, do not add any other additional responses."
    )
    
    # Combine all parts
    user_prompt = system_instruction + qa_content + output_instruction
    
    return user_prompt

# ------------------------------------------------------------------------------
#                          PREPARE INPUTS UTILS
# ------------------------------------------------------------------------------

# Prepare inputs text and image
def _prepare_inputs_text_and_image(
    user_prompt: str, 
    image_paths: list[str], 
    image_merge: bool = False,
    prompt_type: str = "find_canonical_front_view_prompt",
) -> list[dict]:
    assert prompt_type in SUPPORTED_PROMPT_TYPES, \
    f"[GRGenerator: Qwen Utils._prepare_inputs_text_and_image] Invalid prompt_type option: {prompt_type}, supported prompt types: {SUPPORTED_PROMPT_TYPES}"
    # Validate inputs
    if not user_prompt:
        raise ValueError("User prompt cannot be empty")
    
    if not image_paths:
        raise ValueError("Image paths list cannot be empty")
    
    if "with_background" in prompt_type:
        assert isinstance(user_prompt, list), \
        "[Error: Qwen Utils._prepare_inputs_text_and_image] If 'with_background' in prompt type, user prompt must be a list"
        cad_model_prompt  = user_prompt[0]
        background_prompt = user_prompt[1]
        task_prompt       = user_prompt[2]
        
        cad_image_paths = natsorted([img_path for img_path in image_paths if "_with_bg" not in img_path])
        background_image_paths = natsorted([img_path for img_path in image_paths if "_with_bg" in img_path])
        
        # Build content with interleaved text and images
        content = []
        
        # Add CAD model prompt followed by CAD model images
        content.append({"type": "text", "text": cad_model_prompt.strip()})
        for image_path in cad_image_paths:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            content.append({
                "type": "image_url", 
                "image": image_path,
            })
        
        # Add background prompt followed by background images
        if len(background_image_paths) > 0:
            content.append({"type": "text", "text": background_prompt.strip()})
            for image_path in background_image_paths:
                if not os.path.exists(image_path):
                    raise FileNotFoundError(f"Image file not found: {image_path}")
                content.append({
                    "type": "image_url", 
                    "image": image_path,
                })
        
        # Add task prompt at the end
        content.append({"type": "text", "text": task_prompt.strip()})
    else:
        content = [{"type": "text", "text": user_prompt.strip()}]
        processed_image_paths = _process_image_paths(image_paths, image_merge)
        for image_path in processed_image_paths:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
                
            content.append({
                "type": "image_url", 
                "image": image_path,
                # Note: Resizing parameters are commented out but can be enabled if needed
                # "resized_height": 355,
                # "resized_width": 535
            })

    # Format as model input messages
    model_inputs = [{
        "role": "user",
        "content": content
    }]
    
    return model_inputs

def prepare_inputs_text_only(user_prompt):
    content = user_prompt.strip()
    # print(f"[DEBUG] Content: {content}")
    # Format as model input messages
    model_inputs = [{
        "role": "user",
        "content": content
    }]
    return model_inputs



# ------------------------------------------------------------------------------
#                          INFERENCE UTILS
# ------------------------------------------------------------------------------

def _qwen_inference(inputs_messages, qwen_model, processor) -> str:
    text = processor.apply_chat_template(
        inputs_messages, tokenize=False, add_generation_prompt=True
    )
    image_inputs, video_inputs = process_vision_info(inputs_messages)
    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to("cuda")

    # Inference
    generated_ids = qwen_model.generate(
                                **inputs, 
                                max_new_tokens=512,
                                temperature=0.8,        # Increased from 0.7
                              # top_k=50,               # Added top_k sampling
                              # top_p=0.95,             # Added nucleus sampling
                              # do_sample=True ,        # Enable sampling
                              # repetition_penalty=1.05,
                                )
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_text = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    print(f"[DEBUG] Output text: {output_text}")
    return output_text

def _qwen_inference_batch(inputs_messages: list[dict], qwen_model, processor):
    texts = [
        processor.apply_chat_template(msg, tokenize=False, add_generation_prompt=True)
        for msg in inputs_messages  
    ]
    image_inputs, video_inputs = process_vision_info(inputs_messages)
    inputs = processor(
        text=texts,
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt",
    )
    inputs = inputs.to("cuda")

    # Batch Inference
    generated_ids = qwen_model.generate(**inputs, max_new_tokens=512, temperature=0.8)
    generated_ids_trimmed = [
        out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
    ]
    output_texts = processor.batch_decode(
        generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
    )
    return output_texts

def _qwen_llm_inference(input_messages, llm_model, tokenizer):
    text = tokenizer.apply_chat_template(
        input_messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(llm_model.device)

    # conduct text completion
    generated_ids = llm_model.generate(
        **model_inputs,
        max_new_tokens=16384
    )
    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):].tolist()
    output_text = tokenizer.decode(output_ids, skip_special_tokens=True)
    return output_text

# ------------------------------------------------------------------------------
#                          QWEN PIPELINE UTILS
# ------------------------------------------------------------------------------


def qwen_vlm_pipeline(
    object_paths: list[str], 
    vlm_model, 
    processor, 
    image_merge: bool=False, 
    prompt_type: str="is_symmetric_object_prompt",
    object_additional_info: List[str]=None
) -> list[str]:
    if "with_background" in prompt_type:
        batch_image_paths = []
        for object_path in object_paths:
            multi_views_dir = object_path
            with_bg_dir = multi_views_dir.replace("multi_views", "multi_views_with_bg")
            # print(f"[DEBUG] multi_views_dir: {multi_views_dir}, with_bg_dir: {with_bg_dir}")
            multi_views_image_paths = _get_image_paths(multi_views_dir, prompt_type)
            with_bg_image_paths = _get_image_paths(with_bg_dir, prompt_type)
            image_paths = multi_views_image_paths + with_bg_image_paths
            batch_image_paths.append(image_paths)
            # print(image_paths)
    else:
        batch_image_paths = []
        for object_path in object_paths:
            image_paths = _get_image_paths(object_path, prompt_type)
            batch_image_paths.append(image_paths)
            # print(image_paths)

    batch_messages = []
    for image_paths in batch_image_paths:
        user_prompt = _compose_user_prompt(len(image_paths), prompt_type, image_merge, object_additional_info)
        message = _prepare_inputs_text_and_image(user_prompt, image_paths, image_merge=image_merge, prompt_type=prompt_type)
        batch_messages.append(message)

    response = _qwen_inference_batch(batch_messages, vlm_model, processor)
    return response

def qwen_llm_referring_qa_pipeline(
    qa_list: List,
    llm_model,
    tokenizer,
    num_complex_expressions: int = 5
) -> str:
    user_prompt = _compose_referring_qa_user_prompt(qa_list, num_complex_expressions)
    model_inputs = prepare_inputs_text_only(user_prompt)
    response = _qwen_llm_inference(model_inputs, llm_model, tokenizer)
    return response