import requests
import base64
from pathlib import Path
from tools.screen_capture import get_screenshot
from agent.llm_utils.utils import encode_image

OUTPUT_DIR = "./tmp/outputs"

class OmniParserClient:
    def __init__(self, 
                 url: str,
                 windows_host_url: str = 'localhost:5001') -> None:
        self.url = url
        self.windows_host_url = windows_host_url

    def __call__(self,):
        screenshot, screenshot_path = get_screenshot(windows_host_url=self.windows_host_url)
        screenshot_path = str(screenshot_path)
        image_base64 = encode_image(screenshot_path)
        response = requests.post(self.url, json={"base64_image": image_base64})
        response_json = response.json()
        
        # Print latency if available
        if 'latency' in response_json:
            print('omniparser latency:', response_json['latency'])
        else:
            print('omniparser latency: not available')

        # Handle missing som_image_base64 (might happen with simplified server)
        if 'som_image_base64' in response_json:
            som_image_data = base64.b64decode(response_json['som_image_base64'])
            screenshot_path_uuid = Path(screenshot_path).stem.replace("screenshot_", "")
            som_screenshot_path = f"{OUTPUT_DIR}/screenshot_som_{screenshot_path_uuid}.png"
            with open(som_screenshot_path, "wb") as f:
                f.write(som_image_data)
        else:
            print('Warning: som_image_base64 not found in response')
        
        # Add additional fields
        response_json['width'] = screenshot.size[0]
        response_json['height'] = screenshot.size[1]
        response_json['original_screenshot_base64'] = image_base64
        response_json['screenshot_uuid'] = Path(screenshot_path).stem.replace("screenshot_", "")
        
        # Make sure parsed_content_list exists
        if 'parsed_content_list' not in response_json:
            print('Warning: parsed_content_list not found in response, creating empty list')
            response_json['parsed_content_list'] = []
            
        # Reformat messages
        response_json = self.reformat_messages(response_json)
        return response_json
    
    def reformat_messages(self, response_json: dict):
        screen_info = ""
        for idx, element in enumerate(response_json["parsed_content_list"]):
            element['idx'] = idx
            if element['type'] == 'text':
                screen_info += f'ID: {idx}, Text: {element["content"]}\n'
            elif element['type'] == 'icon':
                screen_info += f'ID: {idx}, Icon: {element["content"]}\n'
        response_json['screen_info'] = screen_info
        return response_json