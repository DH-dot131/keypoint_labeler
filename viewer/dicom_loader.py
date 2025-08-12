"""
DICOM Loader for Keypoint Labeler
DICOM 파일 로딩 및 처리
"""

import numpy as np
from typing import Tuple, Optional
import pydicom
from pydicom.dataset import FileDataset


class DICOMLoader:
    """DICOM 파일 로더"""
    
    def __init__(self, file_path: str):
        """DICOM 파일 로더 초기화"""
        self.file_path = file_path
        self.dataset = None
        self.pixel_array = None
        self.original_pixel_array = None
        
        self.load_dicom()
        
    def load_dicom(self):
        """DICOM 파일 로드"""
        try:
            self.dataset = pydicom.dcmread(self.file_path)
            self.original_pixel_array = self.dataset.pixel_array.copy()
            self.pixel_array = self.original_pixel_array.copy()
        except Exception as e:
            raise Exception(f"DICOM 파일 로드 실패: {e}")
            
    def get_image(self) -> np.ndarray:
        """처리된 이미지 반환"""
        return self.pixel_array
        
    def get_original_image(self) -> np.ndarray:
        """원본 이미지 반환"""
        return self.original_pixel_array
        
    def get_default_window_level(self) -> int:
        """기본 Window Level 반환"""
        try:
            # DICOM 태그에서 Window Center 가져오기
            if hasattr(self.dataset, 'WindowCenter'):
                if isinstance(self.dataset.WindowCenter, pydicom.multival.MultiValue):
                    return int(self.dataset.WindowCenter[0])
                else:
                    return int(self.dataset.WindowCenter)
            else:
                # 히스토그램 기반 자동 계산
                return int(np.mean(self.original_pixel_array))
        except:
            return 0
            
    def get_default_window_width(self) -> int:
        """기본 Window Width 반환"""
        try:
            # DICOM 태그에서 Window Width 가져오기
            if hasattr(self.dataset, 'WindowWidth'):
                if isinstance(self.dataset.WindowWidth, pydicom.multival.MultiValue):
                    return int(self.dataset.WindowWidth[0])
                else:
                    return int(self.dataset.WindowWidth)
            else:
                # 히스토그램 기반 자동 계산
                return int(np.std(self.original_pixel_array) * 2)
        except:
            return 255
            
    def apply_window_level(self, image: np.ndarray, window_level: int, window_width: int) -> np.ndarray:
        """Window/Level 적용"""
        if image is None:
            return None
            
        # Rescale slope/intercept 적용
        if hasattr(self.dataset, 'RescaleSlope') and hasattr(self.dataset, 'RescaleIntercept'):
            slope = float(self.dataset.RescaleSlope)
            intercept = float(self.dataset.RescaleIntercept)
            image = image * slope + intercept
            
        # Window/Level 적용
        min_val = window_level - window_width // 2
        max_val = window_level + window_width // 2
        
        # 클리핑
        image = np.clip(image, min_val, max_val)
        
        # 0-255 범위로 정규화
        if max_val > min_val:
            image = ((image - min_val) / (max_val - min_val) * 255).astype(np.uint8)
        else:
            image = np.zeros_like(image, dtype=np.uint8)
            
        return image
        
    def get_pixel_spacing(self) -> Optional[Tuple[float, float]]:
        """픽셀 간격 반환"""
        try:
            if hasattr(self.dataset, 'PixelSpacing'):
                spacing = self.dataset.PixelSpacing
                return (float(spacing[0]), float(spacing[1]))
        except:
            pass
        return None
        
    def get_image_orientation(self) -> Optional[str]:
        """이미지 방향 반환"""
        try:
            if hasattr(self.dataset, 'ImageOrientationPatient'):
                orientation = self.dataset.ImageOrientationPatient
                return str(orientation)
        except:
            pass
        return None
        
    def get_modality(self) -> Optional[str]:
        """모달리티 반환"""
        try:
            if hasattr(self.dataset, 'Modality'):
                return str(self.dataset.Modality)
        except:
            pass
        return None
        
    def get_patient_info(self) -> dict:
        """환자 정보 반환"""
        info = {}
        try:
            if hasattr(self.dataset, 'PatientName'):
                info['name'] = str(self.dataset.PatientName)
            if hasattr(self.dataset, 'PatientID'):
                info['id'] = str(self.dataset.PatientID)
            if hasattr(self.dataset, 'PatientBirthDate'):
                info['birth_date'] = str(self.dataset.PatientBirthDate)
            if hasattr(self.dataset, 'PatientSex'):
                info['sex'] = str(self.dataset.PatientSex)
        except:
            pass
        return info
        
    def get_study_info(self) -> dict:
        """스터디 정보 반환"""
        info = {}
        try:
            if hasattr(self.dataset, 'StudyDate'):
                info['date'] = str(self.dataset.StudyDate)
            if hasattr(self.dataset, 'StudyDescription'):
                info['description'] = str(self.dataset.StudyDescription)
            if hasattr(self.dataset, 'StudyInstanceUID'):
                info['uid'] = str(self.dataset.StudyInstanceUID)
        except:
            pass
        return info
        
    def get_series_info(self) -> dict:
        """시리즈 정보 반환"""
        info = {}
        try:
            if hasattr(self.dataset, 'SeriesNumber'):
                info['number'] = int(self.dataset.SeriesNumber)
            if hasattr(self.dataset, 'SeriesDescription'):
                info['description'] = str(self.dataset.SeriesDescription)
            if hasattr(self.dataset, 'SeriesInstanceUID'):
                info['uid'] = str(self.dataset.SeriesInstanceUID)
        except:
            pass
        return info
        
    def get_image_info(self) -> dict:
        """이미지 정보 반환"""
        info = {}
        try:
            if hasattr(self.dataset, 'ImageNumber'):
                info['number'] = int(self.dataset.ImageNumber)
            if hasattr(self.dataset, 'ImageComments'):
                info['comments'] = str(self.dataset.ImageComments)
            if hasattr(self.dataset, 'ImageType'):
                info['type'] = str(self.dataset.ImageType)
        except:
            pass
        return info
        
    def get_metadata(self) -> dict:
        """전체 메타데이터 반환"""
        return {
            'patient': self.get_patient_info(),
            'study': self.get_study_info(),
            'series': self.get_series_info(),
            'image': self.get_image_info(),
            'modality': self.get_modality(),
            'pixel_spacing': self.get_pixel_spacing(),
            'image_orientation': self.get_image_orientation(),
            'window_level': self.get_default_window_level(),
            'window_width': self.get_default_window_width()
        }
        
    def invert_image(self) -> np.ndarray:
        """이미지 반전"""
        if self.pixel_array is not None:
            self.pixel_array = 255 - self.pixel_array
            return self.pixel_array
        return None
        
    def flip_horizontal(self) -> np.ndarray:
        """좌우 반전"""
        if self.pixel_array is not None:
            self.pixel_array = np.fliplr(self.pixel_array)
            return self.pixel_array
        return None
        
    def flip_vertical(self) -> np.ndarray:
        """상하 반전"""
        if self.pixel_array is not None:
            self.pixel_array = np.flipud(self.pixel_array)
            return self.pixel_array
        return None
        
    def rotate_90_clockwise(self) -> np.ndarray:
        """90도 시계방향 회전"""
        if self.pixel_array is not None:
            self.pixel_array = np.rot90(self.pixel_array, k=-1)
            return self.pixel_array
        return None
        
    def rotate_90_counterclockwise(self) -> np.ndarray:
        """90도 반시계방향 회전"""
        if self.pixel_array is not None:
            self.pixel_array = np.rot90(self.pixel_array, k=1)
            return self.pixel_array
        return None
        
    def reset_image(self):
        """이미지 리셋"""
        if self.original_pixel_array is not None:
            self.pixel_array = self.original_pixel_array.copy()
            
    def get_histogram(self) -> Tuple[np.ndarray, np.ndarray]:
        """히스토그램 반환"""
        if self.original_pixel_array is not None:
            hist, bins = np.histogram(self.original_pixel_array.flatten(), bins=256, range=(0, 255))
            return hist, bins
        return None, None
