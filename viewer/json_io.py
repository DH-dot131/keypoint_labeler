"""
JSON I/O for Keypoint Labeler
키포인트 데이터 JSON 파일 입출력
"""

import json
import os
import shutil
from typing import List, Dict, Any, Optional
from pathlib import Path


class JSONIO:
    """JSON 파일 입출력 클래스"""
    
    @staticmethod
    def load_keypoints(file_path: str) -> List[List[int]]:
        """키포인트 JSON 파일 로드"""
        try:
            if not os.path.exists(file_path):
                return []
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # coord 필드 확인
            if 'coord' in data:
                coordinates = data['coord']
                # 유효성 검사
                if isinstance(coordinates, list):
                    # 각 좌표가 [x, y] 형태인지 확인
                    valid_coords = []
                    for coord in coordinates:
                        if isinstance(coord, list) and len(coord) == 2:
                            x, y = coord
                            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                                # 정수로 변환
                                valid_coords.append([int(round(x)), int(round(y))])
                    return valid_coords
                    
            return []
            
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return JSONIO._try_recover_keypoints(file_path)
        except Exception as e:
            print(f"파일 로드 오류: {e}")
            return []
            
    @staticmethod
    def save_keypoints(file_path: str, keypoints: List[List[int]], 
                      additional_data: Optional[Dict[str, Any]] = None) -> bool:
        """키포인트 JSON 파일 저장 (W, H 형식)"""
        try:
            # 백업 생성
            JSONIO._create_backup(file_path)
            
            # W, H 형식으로 변환
            w_h_keypoints = []
            for x, y in keypoints:
                w_h_keypoints.append([x, y])  # W=x, H=y
            
            # 데이터 준비
            data = {
                'coord': w_h_keypoints
            }
            
            # 추가 데이터가 있으면 병합
            if additional_data:
                data.update(additional_data)
                
            # 임시 파일에 저장
            temp_path = file_path + '.tmp'
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            # 원자적 교체
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(temp_path, file_path)
            
            return True
            
        except Exception as e:
            print(f"파일 저장 오류: {e}")
            # 임시 파일 정리
            if os.path.exists(temp_path):
                os.remove(temp_path)
            return False
            
    @staticmethod
    def load_with_metadata(file_path: str) -> Dict[str, Any]:
        """메타데이터와 함께 JSON 파일 로드"""
        try:
            if not os.path.exists(file_path):
                return {'coord': []}
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # coord 필드가 없으면 빈 배열로 초기화
            if 'coord' not in data:
                data['coord'] = []
                
            return data
            
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
            return {'coord': JSONIO._try_recover_keypoints(file_path)}
        except Exception as e:
            print(f"파일 로드 오류: {e}")
            return {'coord': []}
            
    @staticmethod
    def save_with_metadata(file_path: str, data: Dict[str, Any]) -> bool:
        """메타데이터와 함께 JSON 파일 저장"""
        try:
            # coord 필드가 있는지 확인
            if 'coord' not in data:
                data['coord'] = []
                
            return JSONIO.save_keypoints(file_path, data['coord'], data)
            
        except Exception as e:
            print(f"파일 저장 오류: {e}")
            return False
            
    @staticmethod
    def validate_keypoints(keypoints: List[List[int]]) -> bool:
        """키포인트 데이터 유효성 검사"""
        if not isinstance(keypoints, list):
            return False
            
        for coord in keypoints:
            if not isinstance(coord, list) or len(coord) != 2:
                return False
            x, y = coord
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                return False
                
        return True
        
    @staticmethod
    def export_to_coco(keypoints: List[List[int]], image_info: Dict[str, Any]) -> Dict[str, Any]:
        """COCO 형식으로 내보내기"""
        coco_data = {
            'images': [{
                'id': 1,
                'file_name': image_info.get('file_name', 'image.jpg'),
                'width': image_info.get('width', 0),
                'height': image_info.get('height', 0)
            }],
            'annotations': [{
                'id': 1,
                'image_id': 1,
                'category_id': 1,
                'keypoints': [],
                'num_keypoints': len(keypoints)
            }],
            'categories': [{
                'id': 1,
                'name': 'keypoints',
                'supercategory': 'keypoints'
            }]
        }
        
        # 키포인트를 COCO 형식으로 변환
        keypoints_flat = []
        for x, y in keypoints:
            keypoints_flat.extend([x, y, 2])  # 2는 visible 상태
            
        coco_data['annotations'][0]['keypoints'] = keypoints_flat
        
        return coco_data
        
    @staticmethod
    def import_from_coco(coco_data: Dict[str, Any]) -> List[List[int]]:
        """COCO 형식에서 키포인트 가져오기"""
        keypoints = []
        
        if 'annotations' in coco_data and len(coco_data['annotations']) > 0:
            annotation = coco_data['annotations'][0]
            if 'keypoints' in annotation:
                keypoints_flat = annotation['keypoints']
                # 3개씩 그룹화 (x, y, visibility)
                for i in range(0, len(keypoints_flat), 3):
                    if i + 1 < len(keypoints_flat):
                        x, y = keypoints_flat[i], keypoints_flat[i + 1]
                        keypoints.append([int(x), int(y)])
                        
        return keypoints
        
    @staticmethod
    def _try_recover_keypoints(file_path: str) -> List[List[int]]:
        """손상된 JSON 파일에서 키포인트 복구 시도"""
        try:
            # 백업 파일 확인
            backup_path = file_path + '.bak'
            if os.path.exists(backup_path):
                print(f"백업 파일에서 복구 시도: {backup_path}")
                return JSONIO.load_keypoints(backup_path)
                
            # 파일을 텍스트로 읽어서 coord 패턴 찾기
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 간단한 패턴 매칭으로 coord 배열 찾기
            import re
            coord_pattern = r'"coord"\s*:\s*\[(.*?)\]'
            match = re.search(coord_pattern, content, re.DOTALL)
            
            if match:
                coord_str = match.group(1)
                # 좌표 파싱
                coord_pattern = r'\[(\d+),\s*(\d+)\]'
                coords = re.findall(coord_pattern, coord_str)
                
                keypoints = []
                for x_str, y_str in coords:
                    keypoints.append([int(x_str), int(y_str)])
                    
                print(f"복구된 키포인트 {len(keypoints)}개")
                return keypoints
                
        except Exception as e:
            print(f"복구 시도 실패: {e}")
            
        return []
        
    @staticmethod
    def _create_backup(file_path: str):
        """백업 파일 생성"""
        if os.path.exists(file_path):
            backup_path = file_path + '.bak'
            try:
                shutil.copy2(file_path, backup_path)
            except Exception as e:
                print(f"백업 생성 실패: {e}")
                
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """JSON 파일 정보 반환"""
        info = {
            'exists': False,
            'size': 0,
            'modified_time': None,
            'keypoint_count': 0,
            'has_metadata': False
        }
        
        try:
            if os.path.exists(file_path):
                info['exists'] = True
                info['size'] = os.path.getsize(file_path)
                info['modified_time'] = os.path.getmtime(file_path)
                
                # 키포인트 개수 확인
                keypoints = JSONIO.load_keypoints(file_path)
                info['keypoint_count'] = len(keypoints)
                
                # 메타데이터 확인
                data = JSONIO.load_with_metadata(file_path)
                info['has_metadata'] = len(data) > 1  # coord 외에 다른 필드가 있으면
                
        except Exception as e:
            print(f"파일 정보 조회 오류: {e}")
            
        return info
        
    @staticmethod
    def cleanup_backups(directory: str, max_backups: int = 5):
        """백업 파일 정리"""
        try:
            backup_files = []
            for file_path in Path(directory).glob('*.json.bak'):
                backup_files.append((file_path, file_path.stat().st_mtime))
                
            # 수정 시간 기준으로 정렬
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # 최대 개수 초과분 삭제
            for file_path, _ in backup_files[max_backups:]:
                try:
                    file_path.unlink()
                    print(f"백업 파일 삭제: {file_path}")
                except Exception as e:
                    print(f"백업 파일 삭제 실패: {e}")
                    
        except Exception as e:
            print(f"백업 정리 오류: {e}")
