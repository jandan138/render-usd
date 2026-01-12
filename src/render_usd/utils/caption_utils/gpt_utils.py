import os
import time
import sys
from pathlib import Path
import json
from typing import List, Dict, Tuple
from natsort import natsorted
from openai import OpenAI

from render_usd.utils.common_utils.images_utils import encode_image
from render_usd.utils.caption_utils.qwen_utils import _compose_user_prompt, _get_image_paths

close_ai_proxy_url = os.getenv("close_ai_proxy_url")


# ----------------------------------------------------------------------------------------------------
#                                            JSONL UTILS  
# ----------------------------------------------------------------------------------------------------

# Function to split a JSONL file into multiple smaller files, each file is less than OPENAI's batch size limit
def split_jsonl_file(file_path: str, max_size_mb: int = 198) -> List[str]:
    max_size_bytes = max_size_mb * 1024 * 1024
    file_dir  = Path(file_path).parent
    file_name = Path(file_path).stem
    file_ext  = Path(file_path).suffix

    lines = open(file_path, 'r', encoding='utf-8').readlines()
    chunk_index = 0
    output_files = []
    current_line_index = 0
    all_lines_length = len(lines)

    while current_line_index < all_lines_length:
        batch = []
        current_size = 0
        while current_line_index < all_lines_length and current_size < max_size_bytes:
            line = lines[current_line_index]
            line_size = len(line.encode('utf-8'))
            
            if current_size == 0 and line_size > max_size_bytes:
                batch = [line]
                current_line_index += 1
                break
            
            if current_size + line_size > max_size_bytes:
                break
                
            batch.append(line)
            current_size += line_size
            current_line_index += 1

        if batch:
            chunk_index += 1
            output_path = file_dir / f"{file_name}-{chunk_index}{file_ext}"
            with open(output_path, 'w', encoding='utf-8') as out_f:
                out_f.writelines(batch)
            output_files.append(str(output_path))

    return output_files

# Function to merge multiple JSONL files into a single JSONL file, in order to merge the results of the split batch inference
def merge_jsonl_files(output_result_path: str, sub_output_paths: List[str], sorted_by_index: bool = True) -> None:

    if sorted_by_index:
        sub_output_paths = natsorted(sub_output_paths)

    print(f"[GRGenerator: GPT Utils.merge_jsonl_files] Merging {len(sub_output_paths)} JSONL files into: {output_result_path}")

    with open(output_result_path, 'w', encoding='utf-8') as final_out:
        for file_path in sub_output_paths:
            if not os.path.exists(file_path):
                continue
            with open(file_path, 'r', encoding='utf-8') as f_in:
                for line in f_in:
                    final_out.write(line)
            os.remove(file_path)
    

# Create jsonl file for batch job manager
def create_jsonl_file(batch_model_path: List[str], save_path: str, model_name: str = "gpt-4o", task_type: str = "caption"):
    for idx, model_path in enumerate(batch_model_path):
        image_paths = _get_image_paths(model_path, task_type)
        user_prompt = _compose_user_prompt(len(image_paths), task_type, image_merge=False)
        system_prompt = _compose_system_prompt(task_type)
        messages = process_multiple_images_messages(image_paths, user_prompt, system_prompt)

        jsonl_line = {
            "custom_id": str(idx),
            "method": "POST",
            "url": "/v1/chat/completions",
            "body": {
                "model": model_name,
                "messages": messages,
                "temperature": 0.26
            }
        }
        with open(save_path, "a") as f:
            f.write(json.dumps(jsonl_line) + "\n")

# save the batch results to a json file
def save_batch_results(results: List[Tuple[int, str]], object_names: List[str], save_path: str):
    data = {}
    for i, result in enumerate(results):
        model_id, result = result
        data[object_names[model_id]] = result
    with open(save_path, 'w') as f:
        json.dump(data, f, indent=4)

def save_batch_results_based_on_duplicate_dict(results: List[Tuple[int, str]], duplicate_dict: Dict[int, List[str]], save_path: str):
    data = {}
    for group_index, objects_list in duplicate_dict.items():
        for object_name in objects_list:
            data[object_name] = results[int(group_index)][1]
    with open(save_path, 'w') as f:
        json.dump(data, f, indent=4)

# ----------------------------------------------------------------------------------------------------
#                                            BATCH JOB UTILS  
# ----------------------------------------------------------------------------------------------------

class BatchJobManager:
    def __init__(self, api_key=None):
        switch_proxy(close_ai_proxy_url, mode="on")
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key)
        self.batch_ids = []  

    def upload_file(self, file_path: str) -> str:
        print("[GRGenerator: GPT Utils.BatchJobManager.upload_file] Uploading JSONL file containing request information...")
        file_object = self.client.files.create(file=Path(file_path), purpose="batch")
        print(f"[GRGenerator: GPT Utils.BatchJobManager.upload_file] File uploaded successfully. Received file ID: {file_object.id}\n")
        return file_object.id

    def create_batch_job(self, input_file_id: str, endpoint: str = "/v1/chat/completions", completion_window: str = "24h") -> str:
        print("[GRGenerator: GPT Utils.BatchJobManager.create_batch_job] Creating a Batch job based on the file ID...")
        batch = self.client.batches.create(
            input_file_id=input_file_id,
            endpoint=endpoint,
            completion_window=completion_window
        )
        print(f"[GRGenerator: GPT Utils.BatchJobManager.create_batch_job] Batch job created successfully. Received Batch job ID: {batch.id}\n")
        self.batch_ids.append(batch.id)
        return batch.id

    def submit_all_batches(self, file_path: str, endpoint: str = "/v1/chat/completions", completion_window: str = "24h") -> List[str]:

        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 198:
            print(f"[GRGenerator: GPT Utils.BatchJobManager.submit_all_batches] File size is {file_size_mb:.2f} MB, larger than 198 MB. Splitting into chunks...\n")
            split_files = split_jsonl_file(file_path)
        else:
            split_files = [file_path]

        for chunk_file in split_files:
            file_id = self.upload_file(chunk_file)
            batch_id = self.create_batch_job(file_id, endpoint, completion_window)

        print(f"[GRGenerator: GPT Utils.BatchJobManager.submit_all_batches] All batches submitted. Total jobs: {len(self.batch_ids)}")
        return self.batch_ids


    def check_job_status(self, batch_id):
        print("[GRGenerator: GPT Utils.BatchJobManager.check_job_status] Checking the status of the Batch job...")
        batch = self.client.batches.retrieve(batch_id=batch_id)
        print(f"[GRGenerator: GPT Utils.BatchJobManager.check_job_status] Batch job status: {batch.status}\n")
        return batch.status

    def get_output_id(self, batch_id):
        print("[GRGenerator: GPT Utils.BatchJobManager.get_output_id] Retrieving the output file ID of successful requests within the Batch job...")
        batch = self.client.batches.retrieve(batch_id=batch_id)
        output_file_id = batch.output_file_id
        print(f"[GRGenerator: GPT Utils.BatchJobManager.get_output_id] Output file ID: {output_file_id}\n")
        return output_file_id

    def get_error_id(self, batch_id):
        print("[GRGenerator: GPT Utils.BatchJobManager.get_error_id] Retrieving the output file ID of failed requests within the Batch job...")
        batch = self.client.batches.retrieve(batch_id=batch_id)
        error_file_id = batch.error_file_id
        print(f"[GRGenerator: GPT Utils.BatchJobManager.get_error_id] Error file ID: {error_file_id}\n")
        return error_file_id

    def get_error(self, batch_id):
        print("[GRGenerator: GPT Utils.BatchJobManager.get_error] Retrieving the error information of failed requests within the Batch job...")
        batch = self.client.batches.retrieve(batch_id=batch_id)
        error = batch.errors
        print(f"[GRGenerator: GPT Utils.BatchJobManager.get_error] Error information: {error}\n")
        return error

    def download_results(self, output_file_id, output_file_path="result.jsonl"):
        print("[GRGenerator: GPT Utils.BatchJobManager.download_results] Downloading the successful results of the Batch job...")
        content = self.client.files.content(output_file_id)
        content.write_to_file(output_file_path)
        print(f"[GRGenerator: GPT Utils.BatchJobManager.download_results]The complete output has been saved locally to the output file: {output_file_path}\n")

    def download_errors(self, error_file_id, error_file_path="error.jsonl"):
        print("[GRGenerator: GPT Utils.BatchJobManager.download_errors] Downloading the failure information of the Batch job...")
        content = self.client.files.content(error_file_id)
        content.write_to_file(error_file_path)
        print(f"[GRGenerator: GPT Utils.BatchJobManager.download_errors] The complete failure information has been saved locally to the error file: {error_file_path}\n")


# ----------------------------------------------------------------------------------------------------
#                                            PROXY UTILS  
# ----------------------------------------------------------------------------------------------------

# Function to set proxy
def switch_proxy(proxy_url: str, mode: str = "on") -> None:
    if mode == "on":
        print(f"[GRGenerator: GPT Utils.switch_proxy] Proxy is on.")
        os.environ['http_proxy'] = proxy_url
        os.environ['https_proxy'] = proxy_url
    elif mode == "off":
        print(f"[GRGenerator: GPT Utils.switch_proxy] Proxy is off.")
        if 'http_proxy' in os.environ:
            del os.environ['http_proxy']
        if 'https_proxy' in os.environ:
            del os.environ['https_proxy']
    else:
        print("[GRGenerator: GPT Utils.switch_proxy] Invalid proxy mode.")


# ----------------------------------------------------------------------------------------------------
#                                            PROMPT UTILS  
# ----------------------------------------------------------------------------------------------------
def _compose_system_prompt(task_type: str) -> str:
    # TODO: Add more system prompts for different tasks
    base_prompt = "You are a professional 3D asset annotation expert with extensive experience in 3D modeling and computer graphics. \
                   Please carefully analyze the provided image content based on your expertise and return accurate results strictly \
                   according to the specified format. \
                   Ensure your output is concise and clear, containing only the required valid value without any additional explanations or formatting."
    return base_prompt




# ----------------------------------------------------------------------------------------------------
#                                            INPUT MESSAGE UTILS  
# ----------------------------------------------------------------------------------------------------

# Function to get GPT API response for text only
def process_text_only(prompt: str, system_prompt: str = "You are a helpful assistant.") -> List[Dict]:
    messages_template = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    return messages_template


# Function to get GPT API response for a single image
def process_single_image(image_path: str, prompt: str, system_prompt: str) -> List[Dict]:
    try:
        base64_image = encode_image(image_path)
    except Exception as e:
        print(f"[GRGenerator: GPT Utils.process_single_image] Error encoding image: {e}")
        return None
    messages_template = [
        {
            "role": "system",
            "content": system_prompt  
        },
        {
            "role": "user", 
            "content": [
                {
                    "type": "text", 
                    "text": prompt
                },
                {
                    "type": "image_url", 
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}",
                        "detail": "low",
                    }
                }
            ]
        }
    ]
    return messages_template


# Function to get GPT API response for multiple images
def process_multiple_images_messages(image_paths: List[str], prompt: str, system_prompt: str) -> List[Dict]:
    base64_images = []
    try:
        for image_path in image_paths:
            base64_image = encode_image(image_path)
            base64_images.append(base64_image)
    except Exception as e:
        print(f"[GRGenerator: GPT Utils.process_multiple_images_messages] Error encoding images: {e}")
        return None
    
    content = [{"type": "text", "text": prompt}]
    for base64_image in base64_images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}",
                "detail": "low"
            }
        })
    messages_template = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": content
        }
    ]

    return messages_template


# ----------------------------------------------------------------------------------------------------
#                                            SINGLE API CALL UTILS  
# ----------------------------------------------------------------------------------------------------

# Function to get GPT API response
def get_gpt_response(messages_template: List[Dict], model_name: str = "gpt-4o") -> Tuple[bool, str]:
    switch_proxy(close_ai_proxy_url, mode="on")
    client = OpenAI()
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages_template,
            temperature=0.26 
        )
        response = response.choices[0].message.content
        return True, response
    except:
        print(f"[GRGenerator: GPT Utils.get_gpt_response] Error in request")
        return False, None


# Function to get GPT API response for multiple images using a specific GPT model
def gpt_pipeline(image_dir: str, gpt_model_name: str = "gpt-4o", task_type: str = "caption", max_retries: int = 3) -> str:
    gpt_api_key = os.getenv("OPENAI_API_KEY")
    proxy_url = os.getenv("close_ai_proxy_url")
    if not gpt_api_key or not proxy_url:
        print("[GRGenerator: GPT Utils.gpt_pipeline] Error: OPENAI_API_KEY or close_ai_proxy_url environment variable not set.")
        sys.exit(1)   

    images = os.listdir(image_dir)      
    images = natsorted(images)[:24]
    image_paths = [os.path.join(image_dir, image) for image in images]

    user_prompt = _compose_user_prompt(len(image_paths), task_type, image_merge=False)
    system_prompt = _compose_system_prompt(task_type)
    attempt = 0
    success = False
    response = None
    while attempt < max_retries and not success:
        messages = process_multiple_images_messages(image_paths, user_prompt, system_prompt)
        success, response = get_gpt_response(messages, model_name=gpt_model_name)
        if response is not None:
            if not response.isdigit():
                print(f"[GRGenerator: GPT Utils.gpt_pipeline] Return value: {response} is invaid. Try again.")
                success = False
        if success:
            break
        attempt += 1
        time.sleep(1.5)  
    if not success:
        print(f"[GRGenerator: GPT Utils.gpt_pipeline] Failed to get response after {max_retries} attempts")
    print(f"[GRGenerator: GPT Utils.gpt_pipeline] Response: {response}")
    return response


# ----------------------------------------------------------------------------------------------------
#                                            BATCH JOB MANAGER UTILS  
# ----------------------------------------------------------------------------------------------------


def submit_batch_job(input_jsonl_path: str, task_type: str = "caption") -> Dict:
    batch_manager = BatchJobManager()
    scene_idx = Path(input_jsonl_path).stem.split('_')[0]
    info = {}
    info['scene_index'] = scene_idx
    info['task_type'] = task_type
    batch_ids = batch_manager.submit_all_batches(input_jsonl_path)
    info['batch_ids'] = batch_ids
    return info

def retrieve_batch_job_result(scene_id, submit_info_path, output_result_path, error_result_path):
    output_basename = Path(output_result_path).stem
    error_basename = Path(error_result_path).stem
    jsonl_dir = Path(output_result_path).parent
    batch_manager = BatchJobManager()
    with open(submit_info_path, 'r', encoding='utf-8') as f:
        submit_info = json.load(f)
    all_sub_output_path = []
    all_sub_error_path = []
    for batch_info in submit_info:
        if scene_id in batch_info['scene_index'] :
            batch_ids = batch_info['batch_ids']
            for idx, batch_id in enumerate(batch_ids):
                output_index = f"{output_basename}_{idx}.jsonl"
                error_index = f"{error_basename}_{idx}.jsonl"
                sub_output_path = os.path.join(jsonl_dir, output_index)
                sub_error_path = os.path.join(jsonl_dir, error_index)
                all_sub_output_path.append(sub_output_path)
                all_sub_error_path.append(sub_error_path)

                status = batch_manager.check_job_status(batch_id)
                if status == "failed":
                    error = batch_manager.get_error(batch_id)
                    print(f"Batch task failed, error :{error}\n")
                    return 

                output_file_id = batch_manager.get_output_id(batch_id)
                if output_file_id:
                    batch_manager.download_results(output_file_id, sub_output_path)
                error_file_id = batch_manager.get_error_id(batch_id)
                if error_file_id:
                    batch_manager.download_errors(error_file_id, sub_error_path)

    merge_jsonl_files(output_result_path, all_sub_output_path)
    merge_jsonl_files(error_result_path, all_sub_error_path)

def extract_model_outputs(file_path) -> List[Tuple[int, str]]:
    outputs = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line.strip())
                content = (
                    data.get("response", {})
                    .get("body", {})
                    .get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                if content:
                    custom_id = data.get("custom_id", "")
                    # print(f"custom_id: {custom_id}, content: {content}")
                    outputs.append((int(custom_id), content))
            except Exception as e:
                print(f"Parsing line error: {e}")
                continue
    return outputs



def test():
    batch_id = "batch_684bccff00808190b7fbc947ca73b6aa"
    switch_proxy(close_ai_proxy_url, mode="on")
    client = OpenAI()
    # batch = client.batches.retrieve(batch_id)
    output_file_id='file-UZJXBrW2noVuHSoGKJ6kZa'
    content = client.files.content(output_file_id)
    print(content.text)


if __name__ == '__main__':
    input_jsonl_path = "/cpfs/user/caopeizhou/data/GRScenes/instances/part1/101_usd/0001/auto_annotation/batch_data/input_gpt-4o.jsonl"
    scene_idx = Path(input_jsonl_path).stem
    print(f"[DEBUG] Scene index: {scene_idx}")

    