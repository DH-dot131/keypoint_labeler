"""
DICOM Loader for Keypoint Labeler
DICOM 파일 로딩 및 처리
"""

import numpy as np
from typing import Tuple, Optional
import pydicom
from pydicom.dataset import FileDataset
import cv2


class DICOMLoader:
    """DICOM 파일 로더"""
    
    def __init__(self, file_path: str):
        """DICOM 파일 로더 초기화"""
        self.file_path = file_path
        self.dataset = None
        self.pixel_array = None
        self.original_pixel_array = None
        
        self.load_dicom()
        
    @staticmethod
    def _lutdata_to_array(raw_lut):
        """
        raw_lut 가 bytes/bytearray 인 경우에는 frombuffer 로,
        list 혹은 ndarray 인 경우에는 np.array 로 변환합니다.
        """
        # 1) bytes-like
        if isinstance(raw_lut, (bytes, bytearray)):
            return np.frombuffer(raw_lut, dtype=np.uint16)
        # 2) list 혹은 ndarray
        elif isinstance(raw_lut, (list, np.ndarray)):
            return np.array(raw_lut, dtype=np.uint16)
        # 3) 기타 예외 처리
        else:
            # 만약 struct 로 unpack 해야 하는 특정 케이스가 있다면 여기에 추가
            raise TypeError(f"Unsupported LUTData type: {type(raw_lut)}")
    
    @staticmethod
    def preprocess_dicom(ds):
        """
        DICOM 파일을 보기 좋게 시각화하는 함수 (MONOCHROME + RGB 모두 대응)
        """
        pixel_array = ds.pixel_array

        # 1) signed pixel 처리 (PixelRepresentation == 1)
        if getattr(ds, 'PixelRepresentation', 0) == 1:
            # BitsStored 비트로 signed 값이 들어옴
            signed_max = 2 ** (ds.BitsStored - 1)
            pixel_array = pixel_array - signed_max
            
        # Apply VOI LUT (if available and MONOCHROME)
        if hasattr(ds, 'PhotometricInterpretation') and ds.PhotometricInterpretation.startswith('MONOCHROME'):
            
            # --- 기존 LUT, Windowing, Rescale 처리 ---
            
            if hasattr(ds, 'VOILUTSequence') and len(ds.VOILUTSequence) > 0:
                voi_lut = ds.VOILUTSequence[0]
                raw_bytes = voi_lut.LUTData               # b'\xc0\x00\xc0\x00...'
                lut_data = DICOMLoader._lutdata_to_array(raw_bytes)
                pixel_array = np.clip(pixel_array, 0, len(lut_data)-1)
                pixel_array = lut_data[pixel_array]
            
            if hasattr(ds, 'RescaleSlope') and hasattr(ds, 'RescaleIntercept'):
                slope = float(ds.RescaleSlope)
                intercept = float(ds.RescaleIntercept)
                pixel_array = pixel_array * slope + intercept
                
            elif hasattr(ds, 'WindowCenter') and hasattr(ds, 'WindowWidth'):
                wc = float(ds.WindowCenter[0]) if isinstance(ds.WindowCenter, (list, pydicom.multival.MultiValue)) else float(ds.WindowCenter)
                ww = float(ds.WindowWidth[0]) if isinstance(ds.WindowWidth, (list, pydicom.multival.MultiValue)) else float(ds.WindowWidth)
                pixel_array = np.clip(pixel_array, wc - ww / 2, wc + ww / 2)
            
            # Normalize
            if np.max(pixel_array) != np.min(pixel_array):
                pixel_array = ((pixel_array - np.min(pixel_array)) * 255 / 
                              (np.max(pixel_array) - np.min(pixel_array)))

            pixel_array = pixel_array.astype(np.uint8)

            # Invert MONOCHROME1
            if ds.PhotometricInterpretation == 'MONOCHROME1':
                pixel_array = 255 - pixel_array

            # CLAHE (grayscale)
            try:
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                pixel_array = clahe.apply(pixel_array)
            except:
                pass

            return pixel_array

        # RGB 처리
        elif ds.PhotometricInterpretation == 'RGB':
            # 보통 uint8로 되어 있음
            if pixel_array.dtype != np.uint8:
                pixel_array = ((pixel_array - np.min(pixel_array)) * 255 / 
                              (np.max(pixel_array) - np.min(pixel_array))).astype(np.uint8)

            # CLAHE 채널별 적용
            try:
                enhanced_channels = []
                clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                for c in range(3):
                    enhanced = clahe.apply(pixel_array[:, :, c])
                    enhanced_channels.append(enhanced)
                pixel_array = np.stack(enhanced_channels, axis=-1)
            except:
                pass

            return pixel_array

        # 예상하지 못한 경우 → 기본 처리
        else:
            print(f"⚠️ Warning: Unknown PhotometricInterpretation: {ds.PhotometricInterpretation}")
            return pixel_array
        
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
        return self.preprocess_dicom(self.dataset)
        
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
