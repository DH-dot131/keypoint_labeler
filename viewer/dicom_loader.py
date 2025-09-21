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
    def _safe_float(value, default=1.0):
        """안전하게 float로 변환하는 함수"""
        if value is None:
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _safe_get_first_value(value, default=None):
        """리스트나 MultiValue에서 첫 번째 값을 안전하게 가져오는 함수"""
        if value is None:
            return default
        if isinstance(value, (list, pydicom.multival.MultiValue)):
            if len(value) > 0:
                return value[0]
            else:
                return default
        return value
    
    @staticmethod
    def preprocess_dicom(ds):
        """
        DICOM 파일을 보기 좋게 시각화하는 함수 (MONOCHROME + RGB 모두 대응)
        """
        pixel_array = ds.pixel_array

        # 1) signed pixel 처리 (PixelRepresentation == 1)
        try:
            pixel_representation = getattr(ds, 'PixelRepresentation', 0)
            bits_stored = getattr(ds, 'BitsStored', 16)
            
            if pixel_representation == 1:
                # BitsStored 비트로 signed 값이 들어옴
                signed_max = 2 ** (bits_stored - 1)
                pixel_array = pixel_array - signed_max
        except Exception as e:
            print(f"Signed pixel 처리 중 오류: {e}")
            
        # Apply VOI LUT (if available and MONOCHROME)
        if hasattr(ds, 'PhotometricInterpretation') and ds.PhotometricInterpretation.startswith('MONOCHROME'):
            
            # --- 기존 LUT, Windowing, Rescale 처리 ---
            
            if hasattr(ds, 'VOILUTSequence') and len(ds.VOILUTSequence) > 0:
                voi_lut = ds.VOILUTSequence[0]
                raw_bytes = voi_lut.LUTData               # b'\xc0\x00\xc0\x00...'
                lut_data = DICOMLoader._lutdata_to_array(raw_bytes)
                pixel_array = np.clip(pixel_array, 0, len(lut_data)-1)
                pixel_array = lut_data[pixel_array]
            
            # Rescale 처리 (개선된 None 처리)
            try:
                rescale_slope = getattr(ds, 'RescaleSlope', None)
                rescale_intercept = getattr(ds, 'RescaleIntercept', None)
                
                if rescale_slope is not None and rescale_intercept is not None:
                    slope = DICOMLoader._safe_float(rescale_slope, 1.0)
                    intercept = DICOMLoader._safe_float(rescale_intercept, 0.0)
                    print(f"Rescale 적용: slope={slope}, intercept={intercept}")
                    pixel_array = pixel_array * slope + intercept
                else:
                    print("Rescale 값이 없어서 Window/Level 처리로 넘어갑니다.")
            except Exception as e:
                print(f"Rescale 처리 중 오류: {e}")
                
            # Window/Level 처리 (개선된 None 처리)
            try:
                window_center = getattr(ds, 'WindowCenter', None)
                window_width = getattr(ds, 'WindowWidth', None)
                
                if window_center is not None and window_width is not None:
                    wc = DICOMLoader._safe_float(DICOMLoader._safe_get_first_value(window_center), None)
                    ww = DICOMLoader._safe_float(DICOMLoader._safe_get_first_value(window_width), None)
                    
                    if wc is not None and ww is not None:
                        print(f"Window/Level 적용: center={wc}, width={ww}")
                        pixel_array = np.clip(pixel_array, wc - ww / 2, wc + ww / 2)
                    else:
                        print("Window/Level 값이 유효하지 않습니다.")
                else:
                    print("Window/Level 값이 없습니다.")
            except Exception as e:
                print(f"Window/Level 처리 중 오류: {e}")
            
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
            # 먼저 기본 방법으로 시도
            self.dataset = pydicom.dcmread(self.file_path)
            self.original_pixel_array = self.dataset.pixel_array.copy()
            self.pixel_array = self.original_pixel_array.copy()
        except Exception as e:
            error_msg = str(e)
            if "unable to decompress" in error_msg.lower() and "jpeg" in error_msg.lower():
                # JPEG 압축 해제 에러인 경우 대안 방법 시도
                try:
                    # force=True로 강제 로드 시도
                    self.dataset = pydicom.dcmread(self.file_path, force=True)
                    # pixel_array 접근 시 에러가 발생할 수 있으므로 try-except로 감싸기
                    try:
                        self.original_pixel_array = self.dataset.pixel_array.copy()
                        self.pixel_array = self.original_pixel_array.copy()
                    except Exception as pixel_error:
                        # pixel_array 접근 실패 시 더 자세한 안내 메시지 제공
                        raise Exception(f"DICOM 파일 로드 실패: {error_msg}\n\n"
                                      f"해결 방법:\n"
                                      f"1. pip로 설치 가능한 라이브러리 (대부분의 JPEG Lossless 지원):\n"
                                      f"   pip install pylibjpeg>=2.0 pylibjpeg-libjpeg>=2.1\n"
                                      f"2. gdcm이 필요한 경우 (새 conda 환경에서):\n"
                                      f"   conda create -n dicom_env python=3.9\n"
                                      f"   conda activate dicom_env\n"
                                      f"   conda install -c conda-forge gdcm\n"
                                      f"3. 또는 requirements.txt 사용:\n"
                                      f"   pip install -r requirements.txt")
                except Exception as force_error:
                    # force=True로도 실패한 경우
                    raise Exception(f"DICOM 파일 로드 실패: {error_msg}\n\n"
                                  f"해결 방법:\n"
                                  f"1. pip로 설치 가능한 라이브러리 (대부분의 JPEG Lossless 지원):\n"
                                  f"   pip install pylibjpeg>=2.0 pylibjpeg-libjpeg>=2.1\n"
                                  f"2. gdcm이 필요한 경우 (새 conda 환경에서):\n"
                                  f"   conda create -n dicom_env python=3.9\n"
                                  f"   conda activate dicom_env\n"
                                  f"   conda install -c conda-forge gdcm\n"
                                  f"3. 또는 requirements.txt 사용:\n"
                                  f"   pip install -r requirements.txt")
            else:
                raise Exception(f"DICOM 파일 로드 실패: {error_msg}")
            
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
                window_center = getattr(self.dataset, 'WindowCenter', None)
                if window_center is not None:
                    first_value = DICOMLoader._safe_get_first_value(window_center)
                    if first_value is not None:
                        return int(DICOMLoader._safe_float(first_value, 128.0))
            # 히스토그램 기반 자동 계산
            if self.original_pixel_array is not None:
                return int(np.mean(self.original_pixel_array))
        except:
            pass
        return 0
            
    def get_default_window_width(self) -> int:
        """기본 Window Width 반환"""
        try:
            # DICOM 태그에서 Window Width 가져오기
            if hasattr(self.dataset, 'WindowWidth'):
                window_width = getattr(self.dataset, 'WindowWidth', None)
                if window_width is not None:
                    first_value = DICOMLoader._safe_get_first_value(window_width)
                    if first_value is not None:
                        return int(DICOMLoader._safe_float(first_value, 256.0))
            # 히스토그램 기반 자동 계산
            if self.original_pixel_array is not None:
                return int(np.std(self.original_pixel_array) * 2)
        except:
            pass
        return 255
            
    def apply_window_level(self, image: np.ndarray, window_level: int, window_width: int) -> np.ndarray:
        """Window/Level 적용"""
        if image is None:
            return None
            
        # Rescale slope/intercept 적용
        try:
            rescale_slope = getattr(self.dataset, 'RescaleSlope', None)
            rescale_intercept = getattr(self.dataset, 'RescaleIntercept', None)
            
            if rescale_slope is not None and rescale_intercept is not None:
                slope = DICOMLoader._safe_float(rescale_slope, 1.0)
                intercept = DICOMLoader._safe_float(rescale_intercept, 0.0)
                image = image * slope + intercept
        except Exception as e:
            print(f"Rescale 처리 중 오류: {e}")
            
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
                return (DICOMLoader._safe_float(spacing[0], 1.0), DICOMLoader._safe_float(spacing[1], 1.0))
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
                series_number = getattr(self.dataset, 'SeriesNumber', None)
                if series_number is not None:
                    try:
                        info['number'] = int(series_number)
                    except (ValueError, TypeError):
                        pass
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
                image_number = getattr(self.dataset, 'ImageNumber', None)
                if image_number is not None:
                    try:
                        info['number'] = int(image_number)
                    except (ValueError, TypeError):
                        pass
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
