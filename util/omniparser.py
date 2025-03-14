from util.utils import get_som_labeled_img, get_caption_model_processor, get_yolo_model, check_ocr_box
import torch
from PIL import Image
import io
import base64
from typing import Dict
import time

class Omniparser(object):
    def __init__(self, config: Dict):
        self.config = config
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.som_model = get_yolo_model(model_path=config['som_model_path'])
        self.caption_model_processor = get_caption_model_processor(model_name=config['caption_model_name'], model_name_or_path=config['caption_model_path'], device=device)
        print('Omniparser initialized!!!')

    def parse(self, image_base64: str):
        start_total = time.time()
        
        # Image decoding and setup
        start_decode = time.time()
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        print('image size:', image.size)
        
        box_overlay_ratio = max(image.size) / 3200
        draw_bbox_config = {
            'text_scale': 0.8 * box_overlay_ratio,
            'text_thickness': max(int(2 * box_overlay_ratio), 1),
            'text_padding': max(int(3 * box_overlay_ratio), 1),
            'thickness': max(int(3 * box_overlay_ratio), 1),
        }
        decode_time = time.time() - start_decode
        print(f"⏱️ PERF INTERNAL: Image decoding: {decode_time:.2f}s")

        # OCR processing
        start_ocr = time.time()
        (text, ocr_bbox), _ = check_ocr_box(image, display_img=False, output_bb_format='xyxy', easyocr_args={'text_threshold': 0.8}, use_paddleocr=False)
        ocr_time = time.time() - start_ocr
        print(f"⏱️ PERF INTERNAL: OCR processing: {ocr_time:.2f}s")
        
        # SOM model (combined detection and caption generation)
        start_som = time.time()
        dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
            image, 
            self.som_model, 
            BOX_TRESHOLD = self.config['BOX_TRESHOLD'], 
            output_coord_in_ratio=True, 
            ocr_bbox=ocr_bbox,
            draw_bbox_config=draw_bbox_config, 
            caption_model_processor=self.caption_model_processor, 
            ocr_text=text,
            use_local_semantics=True, 
            iou_threshold=0.7, 
            scale_img=False, 
            batch_size=128
        )
        som_time = time.time() - start_som
        print(f"⏱️ PERF INTERNAL: SOM model (detection + caption): {som_time:.2f}s")
        
        # Summary of timing
        total_time = time.time() - start_total
        print(f"⏱️ PERF INTERNAL: Total parsing breakdown:")
        print(f"⏱️ PERF INTERNAL:   - Image decoding: {decode_time:.2f}s ({decode_time/total_time*100:.1f}%)")
        print(f"⏱️ PERF INTERNAL:   - OCR processing: {ocr_time:.2f}s ({ocr_time/total_time*100:.1f}%)")
        print(f"⏱️ PERF INTERNAL:   - SOM model: {som_time:.2f}s ({som_time/total_time*100:.1f}%)")
        print(f"⏱️ PERF INTERNAL:   - Total: {total_time:.2f}s (100%)")
        
        return dino_labled_img, parsed_content_list