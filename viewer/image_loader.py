"""
Image Loader for Keypoint Labeler
일반 이미지 파일 로딩 및 처리
"""

import numpy as np
from typing import Optional
from PIL import Image
from PyQt5.QtGui import QPixmap, QImage


class ImageLoader:
    """이미지 파일 로더"""
    
    def __init__(self):
        """이미지 로더 초기화"""
        pass
        
    def load_image(self, file_path: str) -> np.ndarray:
        """이미지 파일 로드"""
        try:
            # PIL을 사용하여 이미지 로드
            pil_image = Image.open(file_path)
            
            # RGB로 변환 (그레이스케일인 경우)
            if pil_image.mode == 'L':
                pil_image = pil_image.convert('RGB')
            elif pil_image.mode == 'RGBA':
                pil_image = pil_image.convert('RGB')
                
            # NumPy 배열로 변환
            image_array = np.array(pil_image)
            
            # 그레이스케일로 변환 (단일 채널)
            if len(image_array.shape) == 3:
                # RGB를 그레이스케일로 변환
                gray = np.dot(image_array[..., :3], [0.299, 0.587, 0.114])
                return gray.astype(np.uint8)
            else:
                return image_array.astype(np.uint8)
                
        except Exception as e:
            raise Exception(f"이미지 로드 실패: {e}")
            
    def numpy_to_qpixmap(self, image_array: np.ndarray) -> QPixmap:
        """NumPy 배열을 QPixmap으로 변환"""
        if image_array is None:
            return None
            
        # 이미지 형태 확인 및 변환
        if len(image_array.shape) == 2:
            # 그레이스케일 이미지
            height, width = image_array.shape
            bytes_per_line = width
            
            # QImage 생성
            q_image = QImage(
                image_array.data,
                width,
                height,
                bytes_per_line,
                QImage.Format_Grayscale8
            )
        elif len(image_array.shape) == 3:
            # 컬러 이미지
            height, width, channels = image_array.shape
            bytes_per_line = channels * width
            
            if channels == 3:
                # RGB 이미지
                q_image = QImage(
                    image_array.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format_RGB888
                )
            elif channels == 4:
                # RGBA 이미지
                q_image = QImage(
                    image_array.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format_RGBA8888
                )
            else:
                raise ValueError(f"지원하지 않는 채널 수: {channels}")
        else:
            raise ValueError(f"지원하지 않는 이미지 형태: {image_array.shape}")
            
        # QPixmap으로 변환
        return QPixmap.fromImage(q_image)
        
    def qpixmap_to_numpy(self, pixmap: QPixmap) -> np.ndarray:
        """QPixmap을 NumPy 배열로 변환"""
        if pixmap is None:
            return None
            
        # QImage로 변환
        q_image = pixmap.toImage()
        
        # 이미지 정보 가져오기
        width = q_image.width()
        height = q_image.height()
        
        # 바이트 배열로 변환
        ptr = q_image.bits()
        ptr.setsize(height * width * 4)  # RGBA
        arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
        
        # RGBA를 그레이스케일로 변환
        gray = np.dot(arr[..., :3], [0.299, 0.587, 0.114])
        return gray.astype(np.uint8)
        
    def resize_image(self, image_array: np.ndarray, width: int, height: int) -> np.ndarray:
        """이미지 크기 조정"""
        if image_array is None:
            return None
            
        pil_image = Image.fromarray(image_array)
        resized_image = pil_image.resize((width, height), Image.LANCZOS)
        return np.array(resized_image)
        
    def crop_image(self, image_array: np.ndarray, x: int, y: int, width: int, height: int) -> np.ndarray:
        """이미지 크롭"""
        if image_array is None:
            return None
            
        return image_array[y:y+height, x:x+width]
        
    def rotate_image(self, image_array: np.ndarray, angle: float) -> np.ndarray:
        """이미지 회전"""
        if image_array is None:
            return None
            
        pil_image = Image.fromarray(image_array)
        rotated_image = pil_image.rotate(angle, expand=True)
        return np.array(rotated_image)
        
    def flip_image(self, image_array: np.ndarray, horizontal: bool = True) -> np.ndarray:
        """이미지 반전"""
        if image_array is None:
            return None
            
        if horizontal:
            return np.fliplr(image_array)
        else:
            return np.flipud(image_array)
            
    def adjust_brightness(self, image_array: np.ndarray, factor: float) -> np.ndarray:
        """밝기 조정"""
        if image_array is None:
            return None
            
        adjusted = image_array * factor
        return np.clip(adjusted, 0, 255).astype(np.uint8)
        
    def adjust_contrast(self, image_array: np.ndarray, factor: float) -> np.ndarray:
        """대비 조정"""
        if image_array is None:
            return None
            
        mean = np.mean(image_array)
        adjusted = (image_array - mean) * factor + mean
        return np.clip(adjusted, 0, 255).astype(np.uint8)
        
    def apply_gaussian_blur(self, image_array: np.ndarray, sigma: float) -> np.ndarray:
        """가우시안 블러 적용"""
        if image_array is None:
            return None
            
        from scipy.ndimage import gaussian_filter
        return gaussian_filter(image_array, sigma=sigma).astype(np.uint8)
        
    def apply_histogram_equalization(self, image_array: np.ndarray) -> np.ndarray:
        """히스토그램 평활화"""
        if image_array is None:
            return None
            
        from skimage import exposure
        return exposure.equalize_hist(image_array).astype(np.uint8)
        
    def get_image_info(self, image_array: np.ndarray) -> dict:
        """이미지 정보 반환"""
        if image_array is None:
            return {}
            
        info = {
            'shape': image_array.shape,
            'dtype': str(image_array.dtype),
            'min_value': float(np.min(image_array)),
            'max_value': float(np.max(image_array)),
            'mean_value': float(np.mean(image_array)),
            'std_value': float(np.std(image_array))
        }
        
        if len(image_array.shape) == 2:
            info['channels'] = 1
            info['type'] = 'grayscale'
        elif len(image_array.shape) == 3:
            info['channels'] = image_array.shape[2]
            if info['channels'] == 3:
                info['type'] = 'RGB'
            elif info['channels'] == 4:
                info['type'] = 'RGBA'
            else:
                info['type'] = f'{info["channels"]}-channel'
                
        return info
        
    def save_image(self, image_array: np.ndarray, file_path: str, format: str = 'PNG') -> bool:
        """이미지 저장"""
        try:
            if image_array is None:
                return False
                
            pil_image = Image.fromarray(image_array)
            pil_image.save(file_path, format=format)
            return True
        except Exception as e:
            print(f"이미지 저장 실패: {e}")
            return False
            
    def create_thumbnail(self, image_array: np.ndarray, max_size: int = 100) -> np.ndarray:
        """썸네일 생성"""
        if image_array is None:
            return None
            
        pil_image = Image.fromarray(image_array)
        pil_image.thumbnail((max_size, max_size), Image.LANCZOS)
        return np.array(pil_image)
