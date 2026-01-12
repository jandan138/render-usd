import re
import json
from typing import List, Dict, Tuple, Union

def extract_qa_pairs(
    text: str,
    min_question_words: int = 3,
    min_answer_words: int = 1,
    allow_multiline: bool = True,
    output_format: str = "list"  # "list", "dict", 或 "text"
) -> List[Dict[str, str]] | List[Tuple[str, str]] | str:
    """
    通过识别Question和Answer的位置来提取完整的QA对，删除不完整的QA对。
    
    Args:
        text (str): 模型生成的原始输出文本
        min_question_words (int): Question 至少包含的单词数（防误匹配）
        min_answer_words (int): Answer 至少包含的单词数
        allow_multiline (bool): 是否允许 QA 跨行（推荐开启）
        output_format (str): 输出格式
            - "list": 返回 [(question, answer), ...]
            - "dict": 返回 [{"question": "...", "answer": "..."}, ...]
            - "text": 返回干净的字符串，每行一个 QA 对
    
    Returns:
        根据 output_format 返回不同格式的结果
    """
    if not text or not text.strip():
        return [] if output_format in ("list", "dict") else ""

    # 使用更灵活的方法：先找到所有可能的QA模式，然后进行智能匹配
    # 这个函数将使用多种策略来提取QA对
    
    def extract_qa_with_multiple_strategies(text_lines):
        qa_pairs = []
        
        # 策略1: 寻找同一行中的 Question: ... Answer: ... 模式
        for line in text_lines:
            line = line.strip()
            # 匹配同一行中的QA对，支持各种前缀
            same_line_patterns = [
                # *   Question: ... Answer: ...
                re.compile(r'^\s*\*\s+Question\s*:\s*(.+?)\s+Answer\s*:\s*(.+?)$', re.IGNORECASE),
                # -   Question: ... Answer: ...
                re.compile(r'^\s*-\s+Question\s*:\s*(.+?)\s+Answer\s*:\s*(.+?)$', re.IGNORECASE),
                # 1. Question: ... Answer: ...
                re.compile(r'^\s*\d+\.\s*Question\s*:\s*(.+?)\s+Answer\s*:\s*(.+?)$', re.IGNORECASE),
                # Question: ... Answer: ...
                re.compile(r'^\s*Question\s*:\s*(.+?)\s+Answer\s*:\s*(.+?)$', re.IGNORECASE),
            ]
            
            for pattern in same_line_patterns:
                match = pattern.match(line)
                if match:
                    question = match.group(1).strip()
                    answer = match.group(2).strip()
                    qa_pairs.append((question, answer, 'same_line'))
                    break
        
        # 策略2: 寻找分行的QA对
        i = 0
        while i < len(text_lines):
            line = text_lines[i].strip()
            
            # 各种Question模式
            question_patterns = [
                re.compile(r'^\s*\*\s+Question\s*:\s*(.+?)$', re.IGNORECASE),  # *   Question:
                re.compile(r'^\s*-\s+Question\s*:\s*(.+?)$', re.IGNORECASE),   # -   Question:
                re.compile(r'^\s*\d+\.\s*\*\*Question\s*:\*\*\s*(.+?)$', re.IGNORECASE),
                re.compile(r'^\s*\*\*Question\s*:\*\*\s*(.+?)$', re.IGNORECASE),
                re.compile(r'^\s*\d+\.\s*Question\s*:\s*(.+?)$', re.IGNORECASE),
                re.compile(r'^\s*Question\s*:\s*(.+?)$', re.IGNORECASE),
                re.compile(r'^\s*Q\s*:\s*(.+?)$', re.IGNORECASE),
            ]
            
            # 各种Answer模式
            answer_patterns = [
                re.compile(r'^\s*\*\s+Answer\s*:\s*(.+?)$', re.IGNORECASE),    # *   Answer:
                re.compile(r'^\s*-\s+Answer\s*:\s*(.+?)$', re.IGNORECASE),     # -   Answer:
                re.compile(r'^\s*\*\*Answer\s*:\*\*\s*(.+?)$', re.IGNORECASE),
                re.compile(r'^\s*Answer\s*:\s*(.+?)$', re.IGNORECASE),
                re.compile(r'^\s*A\s*:\s*(.+?)$', re.IGNORECASE),
            ]
            
            # 检查当前行是否是Question
            question_match = None
            for pattern in question_patterns:
                match = pattern.match(line)
                if match:
                    question_match = match
                    break
            
            if question_match:
                question = question_match.group(1).strip()
                
                # 寻找对应的Answer
                j = i + 1
                answer_found = False
                answer = ""
                
                while j < len(text_lines):
                    next_line = text_lines[j].strip()
                    
                    # 检查是否是Answer行
                    answer_match = None
                    for pattern in answer_patterns:
                        match = pattern.match(next_line)
                        if match:
                            answer_match = match
                            break
                    
                    if answer_match:
                        answer = answer_match.group(1).strip()
                        answer_found = True
                        
                        # 收集Answer的后续行（直到遇到下一个Question或Answer）
                        k = j + 1
                        while k < len(text_lines):
                            continuation_line = text_lines[k].strip()
                            if not continuation_line:
                                k += 1
                                continue
                            
                            # 检查是否是新的Question或Answer
                            is_new_qa = False
                            for pattern in question_patterns + answer_patterns:
                                if pattern.match(continuation_line):
                                    is_new_qa = True
                                    break
                            
                            if is_new_qa:
                                break
                            
                            # 过滤分隔符和无关内容
                            if not re.match(r'^[-=*#]{3,}$', continuation_line):
                                answer += " " + continuation_line
                            k += 1
                        
                        break
                    
                    # 如果遇到新的Question，停止寻找
                    is_new_question = False
                    for pattern in question_patterns:
                        if pattern.match(next_line):
                            is_new_question = True
                            break
                    
                    if is_new_question:
                        break
                    
                    j += 1
                
                if answer_found and question and answer:
                    qa_pairs.append((question, answer, 'separate_lines'))
                
                i = j if answer_found else i + 1
            else:
                i += 1
        
        return qa_pairs
    
    # 使用新的提取策略
    lines = text.strip().split('\n')
    extracted_pairs = extract_qa_with_multiple_strategies(lines)
    
    # 处理提取到的QA对
    qa_pairs = []
    
    for question, answer, source in extracted_pairs:
        # 清理内容
        question_content = re.sub(r'\s+', ' ', question.strip())
        answer_content = re.sub(r'\s+', ' ', answer.strip())
        
        # 检查长度要求
        q_words = question_content.split()
        a_words = answer_content.split()
        
        # 检查答案是否完整（以标点符号结尾）
        is_answer_complete = (
            answer_content.endswith('.') or 
            answer_content.endswith('!') or 
            answer_content.endswith('?') or
            answer_content.endswith('"') or
            answer_content.endswith("'") or
            answer_content.endswith(')') or
            answer_content.endswith(']') or
            answer_content.endswith('}')
        )
        
        # 检查问题是否完整（以问号结尾或包含疑问词）
        is_question_complete = (
            question_content.endswith('?') or
            any(word.lower() in question_content.lower() 
                for word in ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'whose', 'whom', 'does', 'is', 'are', 'can', 'will', 'would', 'could', 'should'])
        )
        
        if (len(q_words) >= min_question_words and 
            len(a_words) >= min_answer_words and
            is_answer_complete and 
            is_question_complete):
            
            qa_pairs.append({
                "question": question_content,
                "answer": answer_content
            })
    
    # 输出格式选择
    if output_format == "dict":
        return qa_pairs
    elif output_format == "list":
        return [(qa["question"], qa["answer"]) for qa in qa_pairs]
    elif output_format == "text":
        return "\n".join([f"Question: {qa['question']}\nAnswer: {qa['answer']}\n" for qa in qa_pairs])
    else:
        raise ValueError("output_format must be 'list', 'dict', or 'text'")

# TODO: Test more cases
def post_process_qa_data(qa_data_path: str):
    '''
    Save the processed qa data to a new json file.
    '''
    with open(qa_data_path, "r") as f:
        qa_data = json.load(f)
    processed_qa_data = {}
    all_qa_pairs_num = 0
    for object_name, qa in qa_data.items():
        qa_list = extract_qa_pairs(qa)
        if len(qa_list) == 0:
            print(f"No qa pairs for {object_name}")
            print(qa)
            print("-"*100)
            # continue
        qa_pairs_num = len(qa_list)
        all_qa_pairs_num += qa_pairs_num
        processed_qa_data[object_name] = qa_list
    qa_data_path_new = qa_data_path.replace(".json", "_processed.json")
    with open(qa_data_path_new, "w") as f:
        json.dump(processed_qa_data, f, indent=4)
    print(f"All qa pairs number: {all_qa_pairs_num}")
    return processed_qa_data

def split_bracket_content(text):
    """
    将形如 "[xxx] yyy" 的字符串拆分为括号内的内容和括号后的内容。
    
    参数:
        text (str): 输入字符串
    
    返回:
        tuple: (括号中的内容, 括号后的内容)，如果未匹配则为 (None, 原始文本) 或 (括号内容, "")
    """
    # 正则匹配：以 [ 开头，捕获中间任意字符（非贪婪），然后是 ]，后面是剩余内容
    match = re.match(r'^\[(.*?)\](.*)', text.strip())
    
    if match:
        in_bracket = match.group(1)   # [] 中的内容
        after_bracket = match.group(2).strip()  # [] 后的内容，去除首尾空格
        return in_bracket, after_bracket
    else:
        # 如果没有匹配到方括号格式，返回 None 和原字符串或空值
        return None, text.strip()

def create_conversation_data(question: str, answer: str):
    conversation = []
    conversation.append({"from": "human", "value": question})
    conversation.append({"from": "gpt",   "value": answer})
    return conversation

if __name__ == "__main__":
    # text = 'Certainly. Below is a series of detailed question-and-answer pairs about the object highlighted in the images. The object is a recessed ceiling light fixture, often referred to as a downlight or pot light.\n\n---\n\n**Question:** What is the primary function of the <object>?  \n**Answer:** The <object> is a lighting fixture designed to emit light downward from a ceiling, typically used for ambient or task lighting in indoor spaces.\n\n---\n\n**Question:** What is the shape of the <object>?  \n**Answer:** The <object> has a circular shape, with a central dark circle surrounded by concentric rings.\n\n---\n\n**Question:** What material does the <object> appear to be made of?  \n**Answer:** The <object> appears to be made of a combination of materials: the central lens or cover is likely glass or clear plastic, the ring surrounding it is metallic (possibly aluminum or stainless steel), and the outer casing is a matte, opaque material such as painted metal or plastic.\n\n---\n\n**Question:** How is the <object> positioned in relation to the ceiling?  \n**Answer:** The <object> is recessed into the ceiling, meaning its outer frame is flush with or slightly below the surface of the ceiling, and the light source is housed within the ceiling cavity.\n\n---\n\n**Question:** What is the color of the central part of the <object>?  \n**Answer:** The central part of the <object> is black, which likely serves as a light diffuser or lens.\n\n---\n\n**Question:** What is the color of the surrounding ring of the <object>?  \n**Answer:** The surrounding ring of the <object> is metallic silver or gray, with a reflective surface.\n\n---\n\n**Question:** What is the color of the outermost part of the <object>?  \n**Answer:** The outermost part of the <object> is a light gray or off-white, matching the typical color of a ceiling or a decorative trim.\n\n---\n\n**Question:** How does the <object> interact with the ceiling surface?  \n**Answer:** The <object> is installed flush with the ceiling surface, creating a seamless appearance when viewed from below, with no protruding parts.\n\n---\n\n**Question:** What is the size of the <object> relative to the surrounding ceiling area?  \n**Answer:** The <object> is relatively small compared to the overall ceiling area, indicating it is a single, individual light source rather than a large fixture.\n\n---\n\n**Question:** Does the <object> have any visible seams or joints?  \n**'
    # text = 'Question: What is the category of the <object>?  \nAnswer: The <object> appears to be a modular partition or a sliding door system, commonly used in interior design for space division.\n\nQuestion: What is the primary material of the <object>?  \nAnswer: The <object> seems to be made of glass or a transparent acrylic material with a dark metallic frame, likely aluminum or steel.\n\nQuestion: What is the shape of the <object>?  \nAnswer: The <object> consists of rectangular panels arranged in a linear, side-by-side configuration, forming a flat, elongated structure.\n\nQuestion: How many panels does the <object> have?  \nAnswer: The <object> has three distinct panels that are connected and aligned in a row.\n\nQuestion: What is the orientation of the <object> in the space?  \nAnswer: The <object> is positioned vertically, standing upright, and appears to be fixed in place rather than being mobile.\n\nQuestion: What is the surface texture of the <object>?  \nAnswer: The surface of the panels is smooth and reflective, with a slight sheen, suggesting a polished or coated finish.\n\nQuestion: Does the <object> have any visible patterns or textures on its surface?  \nAnswer: The panels appear uniform and plain, but one panel shows a subtle textured pattern along its edge, possibly for aesthetic or functional purposes.\n\nQuestion: What is the function of the <object>?  \nAnswer: The <object> is likely used to divide or separate spaces, offering privacy or sound insulation while maintaining visual openness due to its transparent nature.\n\nQuestion: How does the <object> interact with light?  \nAnswer: The <object> allows light to pass through partially, creating reflections and subtle shadows, indicating it is translucent or semi-transparent.\n\nQuestion: What is the relative position of the panels within the <object>?  \nAnswer: The panels are arranged in a linear sequence, with the middle panel slightly offset or overlapping the adjacent ones, suggesting a sliding or hinged mechanism.\n\nQuestion: Can the <object> be moved or adjusted?  \nAnswer: Yes, the <object> appears to be a sliding or folding system, allowing the panels to move relative to each other for space optimization.\n\nQuestion: What is the size of the <object> in relation to typical room dimensions?  \nAnswer: The <object> is large enough to serve as a room divider, likely spanning several feet in height and width, suitable for partitioning a medium to large space.\n\nQuestion: What is the color of the frame'
    # text = 'Here are a series of question pairs focusing on the object, which is a collection of black and white photographs.\n\n---\n\n**Question:** What type of object is the <object>?  \n**Answer:** The <object> is a collection of black and white photographs.\n\n---\n\n**Question:** How many individual photographs are visible within the <object>?  \n**Answer:** There are five individual photographs visible within the <object>.\n\n---\n\n**Question:** What is the primary color scheme of the <object>?  \n**Answer:** The primary color scheme of the <object> is monochromatic, consisting of black, white, and various shades of gray.\n\n---\n\n**Question:** What are the subjects depicted in the <object>?  \n**Answer:** The subjects depicted in the <object> are various outdoor scenes, including landscapes with trees, hills, and possibly buildings or structures.\n\n---\n\n**Question:** How are the photographs in the <object> arranged relative to each other?  \n**Answer:** The photographs in the <object> are arranged in a scattered, overlapping, and seemingly random manner, forming a collage.\n\n---\n\n**Question:** What is the shape and orientation of the individual photographs in the <object>?  \n**Answer:** The individual photographs are rectangular and are oriented at various angles, creating a dynamic and non-uniform composition.\n\n---\n\n**Question:** How does the <object> appear to be affixed to the surface it is on?  \n**Answer:** The <object> appears to be affixed to the surface with small, dark pins or tacks, which are visible at the corners and edges of some of the photographs.\n\n---\n\n**Question:** What is the spatial relationship between the <object> and the surrounding environment?  \n**Answer:** The <object> is mounted on a flat, light-colored wall, positioned at an angle that suggests it is viewed from a slightly elevated perspective.\n\n---\n\n**Question:** How does the size of the <object> compare to the size of the wall it is on?  \n**Answer:** The <object> occupies a small, central portion of the wall, indicating it is a relatively small collection compared to the overall wall space.\n\n---\n\n**Question:** What is the texture of the surface on which the <object> is mounted?  \n**Answer:** The surface on which the <object> is mounted appears to be smooth and flat, with a uniform, light gray color.\n\n---\n\n**Question:** What is the function of the <object>?  \n**Answer:** The function of the <object> is decorative, serving as a piece of'
    # text = "Certainly. Here is a series of detailed question pairs focusing on the object, which is a photograph of a woman, as highlighted by the red bounding box in the images.\n\n---\n\n**Question:** What is the primary subject of the <object>?  \n**Answer:** A smiling woman with blonde hair and a knitted scarf.\n\n---\n\n**Question:** Is the <object> in color or black and white?  \n**Answer:** The <object> is in black and white.\n\n---\n\n**Question:** What is the orientation of the <object> in the images?  \n**Answer:** The <object> is tilted diagonally, not aligned with the horizontal or vertical axes.\n\n---\n\n**Question:** How is the <object> being held or attached to the surface?  \n**Answer:** The <object> appears to be pinned or fastened to the surface with at least one white pushpin visible at the top right corner.\n\n---\n\n**Question:** What material does the <object> appear to be made of?  \n**Answer:** The <object> appears to be a printed photograph on a thin, rigid material, likely paper or cardstock.\n\n---\n\n**Question:** What is the size of the <object> relative to the surrounding area in the final image?  \n**Answer:** The <object> is relatively small compared to the surrounding environment, which includes other large prints and interior elements like a plant and furniture.\n\n---\n\n**Question:** How does the <object> relate spatially to the other photographs visible in the final image?  \n**Answer:** The <object> is one of several photographs displayed on a wall or surface. It is positioned below and to the left of a larger, landscape-oriented photograph and to the right of another partially visible print.\n\n---\n\n**Question:** What is the state of the <object>—is it flat against the surface or does it have any curvature?  \n**Answer:** The <object> appears to be flat against the surface, though slight shadows suggest a minimal thickness or a very slight angle.\n\n---\n\n**Question:** What is the dominant color scheme of the <object>?  \n**Answer:** The dominant color scheme is monochromatic, consisting of shades of black, white, and gray.\n\n---\n\n**Question:** Does the <object> have any visible texture on its surface?  \n**Answer:** The surface of the <object> appears smooth, consistent with a printed photograph, though the image itself shows texture in the woman's hair and scarf.\n\n---\n\n**Question:** What is the function of the <object> in the context of"
    # text = 'Here are a series of question pairs focusing on the <object>, prioritizing reasoning, spatial understanding, and detailed observation:\n\n1.  **Question:** What is the primary subject matter depicted within the <object>?  \n    **Answer:** The <object> contains a black and white photograph of a multi-story building with a distinctive gabled roof and arched windows.\n\n2.  **Question:** What is the material composition of the <object> and how does its surface appear?  \n    **Answer:** The <object> appears to be a flat, rigid object, likely made of paper or cardstock, with a smooth surface suitable for printing a photograph.\n\n3.  **Question:** How is the <object> oriented relative to the wall it is mounted on?  \n    **Answer:** The <object> is mounted at a significant tilt or angle, not perfectly parallel to the wall, creating a diagonal alignment.\n\n4.  **Question:** What is the spatial relationship between the <object> and the other photographic prints visible on the wall?  \n    **Answer:** The <object> is one of several similar photographic prints arranged on the wall, positioned vertically and surrounded by other prints at various angles, suggesting a curated display.\n\n5.  **Question:** What is the overall shape and size of the <object>?  \n    **Answer:** The <object> is a rectangular photograph, appearing to be a standard portrait or postcard size.\n\n6.  **Question:** How does the appearance of the <object> change when viewed from different angles, as seen in the first four images?  \n    **Answer:** The <object> appears to be a flat photograph, but its presentation in the first four images, which show it from different perspectives, creates an illusion of depth or curvature, suggesting it might be a physical print viewed against a background.\n\n7.  **Question:** What evidence suggests the <object> is a physical, three-dimensional object rather than a digital image on a screen?  \n    **Answer:** The presence of shadows, the visible texture of the wall, the physical arrangement of other prints, and the way the <object> is mounted (possibly with pins) indicate it is a tangible, three-dimensional object.\n\n8.  **Question:** What is the function of the <object> in the context of the surrounding environment?  \n    **Answer:** The <object> serves as a piece of wall art or a decorative photograph, contributing to the aesthetic of the space.\n\n9.  **Question:** What can be inferred about'
    # text = 'Certainly. Below is a comprehensive series of question-answer pairs focusing on the object enclosed in the red bounding box, based on the provided images. The object appears to be a flat, elongated, gray-colored structure, likely a shelf or a bracket, with a smooth surface and a slightly raised edge. The lighting and perspective vary across the images, revealing different aspects of its form and spatial relationship.\n\n---\n\n**Question:** What is the primary shape of the <object>?  \n**Answer:** The <object> has a long, rectangular shape with slightly rounded corners and a flat top surface.\n\n---\n\n**Question:** What is the material of the <object> likely to be?  \n**Answer:** The <object> appears to be made of a smooth, matte-finished material such as plastic, metal, or painted wood, suggested by its uniform color and lack of texture.\n\n---\n\n**Question:** What is the color of the <object>?  \n**Answer:** The <object> is primarily gray, with subtle variations in shade due to lighting and shadows.\n\n---\n\n**Question:** Does the <object> have any distinct features on its surface?  \n**Answer:** Yes, the <object> has a raised edge along its longer sides and a slight thickness, giving it a three-dimensional profile. It also casts soft shadows, indicating a solid structure.\n\n---\n\n**Question:** How does the <object> differ in orientation across the images?  \n**Answer:** The <object> is shown at various angles—initially flat and centered, then rotated and tilted, and finally viewed from a low angle, suggesting it is being observed from multiple perspectives.\n\n---\n\n**Question:** What is the apparent function of the <object>?  \n**Answer:** The <object> appears to be a shelf, a support bracket, or a structural component, likely designed to hold or support items.\n\n---\n\n**Question:** How does the <object> relate to the surrounding space in terms of size and scale?  \n**Answer:** The <object> is relatively small in scale compared to the overall background, suggesting it is a component or a model rather than a full-sized furniture piece.\n\n---\n\n**Question:** Is the <object> solid or hollow?  \n**Answer:** The <object> appears to be solid, as it casts a consistent shadow and has a uniform thickness, with no visible gaps or openings.\n\n---\n\n**Question:** What is the surface texture of the <object>?  \n**Answer:** The surface of the <object> is smooth and matte, with no visible grain, patterns, or'
    from natsort import natsorted
    import os
    qa_caption_dir = "/cpfs/user/caopeizhou/data/GRScenes/instances/part1"
    usd_list = natsorted([usd for usd in os.listdir(qa_caption_dir) if usd != "121_usd"])[:10]
    for usd in usd_list:
        scene_list = natsorted([scene for scene in os.listdir(os.path.join(qa_caption_dir, usd))])
        for scene in scene_list:
            # print(f"Processing {usd} {scene}")
            raw_qa_path = os.path.join(qa_caption_dir, usd, scene, "auto_annotation", "qa_result_by_Qwen3-VL-30B-A3B-Instruct.json")
            post_process_qa_data(raw_qa_path)
    # post_process_qa_data(raw_qa_path)

    # print(f"提取到 {len(qa_list)} 个QA对")
    
