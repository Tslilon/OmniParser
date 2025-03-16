from util.utils import get_som_labeled_img, get_caption_model_processor, get_yolo_model, check_ocr_box
import torch
from PIL import Image
import io
import base64
from typing import Dict
import time

class Omniparser(object):
    _instance = None
    _is_initialized = False
    
    def __new__(cls, config: Dict):
        if cls._instance is None:
            cls._instance = super(Omniparser, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, config: Dict):
        if self._is_initialized:
            return
            
        self.config = config
        if 'device' in config:
            self.device = config['device']
        else:
            self.device = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
        print(f'Using device: {self.device}')

        # Set default dtype to float32 for consistency
        torch.set_default_dtype(torch.float32)
        
        # Initialize models with caching
        self._init_models()
        self._is_initialized = True
        print('Omniparser initialized!!!')
        
    def _init_models(self):
        # Initialize YOLO model with caching
        if not hasattr(self, 'som_model'):
            self.som_model = get_yolo_model(model_path=self.config['som_model_path'])
            self.som_model.to(self.device)
            self.som_model.eval()  # Ensure model is in eval mode
            
            # Only compile for CUDA devices
            if hasattr(torch, 'compile') and self.device == 'cuda':
                self.som_model = torch.compile(self.som_model)
        
        # Initialize caption model with caching and MPS optimization
        if not hasattr(self, 'caption_model_processor'):
            if self.device == 'mps':
                # First load on CPU to ensure proper initialization
                temp_cpu_device = torch.device('cpu')
                self.caption_model_processor = get_caption_model_processor(
                    model_name=self.config['caption_model_name'], 
                    model_name_or_path=self.config['caption_model_path'], 
                    device=temp_cpu_device
                )
                
                # Convert model parameters to float32 and move to MPS
                if isinstance(self.caption_model_processor, dict) and 'model' in self.caption_model_processor:
                    model = self.caption_model_processor['model']
                    model.eval()  # Ensure model is in eval mode
                    # Ensure all parameters are float32
                    for param in model.parameters():
                        param.data = param.data.to(dtype=torch.float32)
                    # Move to MPS after conversion
                    model = model.to(device=self.device)
                    self.caption_model_processor['model'] = model
            else:
                # For other devices, initialize normally
                self.caption_model_processor = get_caption_model_processor(
                    model_name=self.config['caption_model_name'], 
                    model_name_or_path=self.config['caption_model_path'], 
                    device=self.device
                )
                if isinstance(self.caption_model_processor, dict) and 'model' in self.caption_model_processor:
                    model = self.caption_model_processor['model']
                    model.eval()  # Ensure model is in eval mode
                    # Only compile for CUDA devices
                    if hasattr(torch, 'compile') and self.device == 'cuda':
                        self.caption_model_processor['model'] = torch.compile(model)

    def parse(self, image_base64: str):
        start_total = time.time()
        
        # Image decoding and setup - optimize with try/except and error handling
        try:
            start_decode = time.time()
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_bytes))
            print('image size:', image.size)
            
            # Calculate overlay ratio once and cache bbox config
            box_overlay_ratio = max(image.size) / 3200
            draw_bbox_config = {
                'text_scale': 0.8 * box_overlay_ratio,
                'text_thickness': max(int(2 * box_overlay_ratio), 1),
                'text_padding': max(int(3 * box_overlay_ratio), 1),
                'thickness': max(int(3 * box_overlay_ratio), 1),
            }
            decode_time = time.time() - start_decode
            print(f"⏱️ PERF INTERNAL: Image decoding: {decode_time:.2f}s")

            # OCR processing with error handling and caching
            start_ocr = time.time()
            try:
                (text, ocr_bbox), _ = check_ocr_box(
                    image, 
                    display_img=False, 
                    output_bb_format='xyxy', 
                    easyocr_args={'text_threshold': 0.8}, 
                    use_paddleocr=False
                )
            except Exception as e:
                print(f"OCR processing failed: {e}")
                text, ocr_bbox = [], []
                
            ocr_time = time.time() - start_ocr
            print(f"⏱️ PERF INTERNAL: OCR processing: {ocr_time:.2f}s")
            
            # SOM model with optimized batch processing
            start_som = time.time()
            
            # Ensure models are in eval mode
            self.som_model.eval()
            if isinstance(self.caption_model_processor, dict) and 'model' in self.caption_model_processor:
                self.caption_model_processor['model'].eval()
            
            # Use torch.inference_mode() for better performance
            with torch.inference_mode(), torch.backends.cudnn.flags(enabled=True, benchmark=True):
                # Pre-synchronize for accurate timing
                if self.device == 'mps' and hasattr(torch.mps, 'synchronize'):
                    torch.mps.synchronize()
                elif self.device == 'cuda':
                    torch.cuda.synchronize()
                    
                dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
                    image, 
                    self.som_model, 
                    BOX_TRESHOLD=self.config['BOX_TRESHOLD'], 
                    output_coord_in_ratio=True, 
                    ocr_bbox=ocr_bbox,
                    draw_bbox_config=draw_bbox_config, 
                    caption_model_processor=self.caption_model_processor, 
                    ocr_text=text,
                    use_local_semantics=True, 
                    iou_threshold=0.7, 
                    scale_img=False, 
                    batch_size=self.config.get('batch_size', 32)  # Reduced batch size
                )
                
                # Post-synchronize for accurate timing
                if self.device == 'mps' and hasattr(torch.mps, 'synchronize'):
                    torch.mps.synchronize()
                elif self.device == 'cuda':
                    torch.cuda.synchronize()
            
            som_time = time.time() - start_som
            print(f"⏱️ PERF INTERNAL: SOM model (detection + caption): {som_time:.2f}s")
            
            # Clean up GPU memory
            if self.device == 'mps':
                if hasattr(torch.mps, 'empty_cache'):
                    torch.mps.empty_cache()
            elif self.device == 'cuda':
                torch.cuda.empty_cache()
            
            # Summary of timing
            total_time = time.time() - start_total
            print(f"⏱️ PERF INTERNAL: Total parsing breakdown:")
            print(f"⏱️ PERF INTERNAL:   - Image decoding: {decode_time:.2f}s ({decode_time/total_time*100:.1f}%)")
            print(f"⏱️ PERF INTERNAL:   - OCR processing: {ocr_time:.2f}s ({ocr_time/total_time*100:.1f}%)")
            print(f"⏱️ PERF INTERNAL:   - SOM model: {som_time:.2f}s ({som_time/total_time*100:.1f}%)")
            print(f"⏱️ PERF INTERNAL:   - Total: {total_time:.2f}s (100%)")
            
            return dino_labled_img, parsed_content_list
            
        except Exception as e:
            print(f"Error in parse: {str(e)}")
            raise