"""
Tools for Keypoint Labeler
키포인트 라벨러 유틸리티 도구
"""

import os
import re
import math
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path


class Tools:
    """유틸리티 도구 클래스"""
    
    @staticmethod
    def natural_sort_key(text: str) -> List:
        """자연 정렬을 위한 키 함수"""
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]
        
    @staticmethod
    def get_supported_files(directory: str) -> List[str]:
        """지원하는 이미지 파일 목록 반환"""
        supported_extensions = {'.dcm', '.jpg', '.jpeg', '.png'}
        
        files = []
        try:
            for file_path in Path(directory).iterdir():
                if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                    files.append(str(file_path))
        except Exception as e:
            print(f"파일 목록 조회 오류: {e}")
            
        # 자연 정렬
        files.sort(key=Tools.natural_sort_key)
        return files
        
    @staticmethod
    def calculate_distance(point1: List[int], point2: List[int]) -> float:
        """두 점 사이의 거리 계산"""
        if len(point1) != 2 or len(point2) != 2:
            return float('inf')
            
        dx = point1[0] - point2[0]
        dy = point1[1] - point2[1]
        return math.sqrt(dx * dx + dy * dy)
        
    @staticmethod
    def find_closest_point(target: List[int], points: List[List[int]]) -> Tuple[int, float]:
        """가장 가까운 점 찾기"""
        if not points:
            return -1, float('inf')
            
        min_distance = float('inf')
        closest_index = -1
        
        for i, point in enumerate(points):
            distance = Tools.calculate_distance(target, point)
            if distance < min_distance:
                min_distance = distance
                closest_index = i
                
        return closest_index, min_distance
        
    @staticmethod
    def validate_coordinates(x: int, y: int, image_width: int, image_height: int) -> Tuple[int, int]:
        """좌표 유효성 검사 및 클리핑"""
        x = max(0, min(image_width - 1, x))
        y = max(0, min(image_height - 1, y))
        return x, y
        
    @staticmethod
    def format_coordinates(keypoints: List[List[int]]) -> str:
        """좌표를 문자열로 포맷팅"""
        if not keypoints:
            return "좌표 없음"
            
        formatted = []
        for i, (x, y) in enumerate(keypoints):
            formatted.append(f"{i}: ({x}, {y})")
            
        return "\n".join(formatted)
        
    @staticmethod
    def parse_coordinates(text: str) -> List[List[int]]:
        """문자열에서 좌표 파싱"""
        keypoints = []
        
        # "0: (x, y)" 형식 파싱
        pattern = r'(\d+):\s*\((\d+),\s*(\d+)\)'
        matches = re.findall(pattern, text)
        
        for match in matches:
            try:
                index = int(match[0])
                x = int(match[1])
                y = int(match[2])
                keypoints.append([x, y])
            except ValueError:
                continue
                
        return keypoints
        
    @staticmethod
    def calculate_centroid(points: List[List[int]]) -> Optional[List[int]]:
        """점들의 중심점 계산"""
        if not points:
            return None
            
        sum_x = sum(point[0] for point in points)
        sum_y = sum(point[1] for point in points)
        
        return [int(sum_x / len(points)), int(sum_y / len(points))]
        
    @staticmethod
    def calculate_bounding_box(points: List[List[int]]) -> Optional[Tuple[int, int, int, int]]:
        """점들의 경계 상자 계산"""
        if not points:
            return None
            
        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        min_y = min(point[1] for point in points)
        max_y = max(point[1] for point in points)
        
        return (min_x, min_y, max_x - min_x, max_y - min_y)
        
    @staticmethod
    def calculate_angle(point1: List[int], point2: List[int], point3: List[int]) -> float:
        """세 점으로 이루어진 각도 계산"""
        if len(point1) != 2 or len(point2) != 2 or len(point3) != 2:
            return 0.0
            
        # 벡터 계산
        v1 = [point1[0] - point2[0], point1[1] - point2[1]]
        v2 = [point3[0] - point2[0], point3[1] - point2[1]]
        
        # 내적 계산
        dot_product = v1[0] * v2[0] + v1[1] * v2[1]
        
        # 벡터 크기 계산
        mag1 = math.sqrt(v1[0] * v1[0] + v1[1] * v1[1])
        mag2 = math.sqrt(v2[0] * v2[0] + v2[1] * v2[1])
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
            
        # 각도 계산 (라디안)
        cos_angle = dot_product / (mag1 * mag2)
        cos_angle = max(-1.0, min(1.0, cos_angle))  # 클리핑
        angle_rad = math.acos(cos_angle)
        
        # 도로 변환
        return math.degrees(angle_rad)
        
    @staticmethod
    def calculate_distance_between_points(points: List[List[int]]) -> List[float]:
        """연속된 점들 사이의 거리 계산"""
        distances = []
        
        for i in range(len(points) - 1):
            distance = Tools.calculate_distance(points[i], points[i + 1])
            distances.append(distance)
            
        return distances
        
    @staticmethod
    def calculate_total_distance(points: List[List[int]]) -> float:
        """전체 경로 거리 계산"""
        if len(points) < 2:
            return 0.0
            
        total_distance = 0.0
        for i in range(len(points) - 1):
            total_distance += Tools.calculate_distance(points[i], points[i + 1])
            
        return total_distance
        
    @staticmethod
    def smooth_keypoints(points: List[List[int]], window_size: int = 3) -> List[List[int]]:
        """키포인트 스무딩"""
        if len(points) < window_size:
            return points.copy()
            
        smoothed = []
        
        for i in range(len(points)):
            # 윈도우 범위 계산
            start = max(0, i - window_size // 2)
            end = min(len(points), i + window_size // 2 + 1)
            
            # 평균 계산
            window_points = points[start:end]
            avg_x = sum(p[0] for p in window_points) / len(window_points)
            avg_y = sum(p[1] for p in window_points) / len(window_points)
            
            smoothed.append([int(avg_x), int(avg_y)])
            
        return smoothed
        
    @staticmethod
    def interpolate_keypoints(points: List[List[int]], num_points: int) -> List[List[int]]:
        """키포인트 보간"""
        if len(points) < 2:
            return points.copy()
            
        interpolated = []
        
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            
            # 현재 구간의 점들 추가
            for j in range(num_points):
                t = j / num_points
                x = int(p1[0] + t * (p2[0] - p1[0]))
                y = int(p1[1] + t * (p2[1] - p1[1]))
                interpolated.append([x, y])
                
        # 마지막 점 추가
        interpolated.append(points[-1])
        
        return interpolated
        
    @staticmethod
    def export_statistics(keypoints: List[List[int]]) -> Dict[str, Any]:
        """키포인트 통계 내보내기"""
        if not keypoints:
            return {}
            
        stats = {
            'total_points': len(keypoints),
            'centroid': Tools.calculate_centroid(keypoints),
            'bounding_box': Tools.calculate_bounding_box(keypoints),
            'total_distance': Tools.calculate_total_distance(keypoints),
            'average_distance': 0.0,
            'min_distance': float('inf'),
            'max_distance': 0.0
        }
        
        if len(keypoints) > 1:
            distances = Tools.calculate_distance_between_points(keypoints)
            stats['average_distance'] = sum(distances) / len(distances)
            stats['min_distance'] = min(distances)
            stats['max_distance'] = max(distances)
            
        return stats
        
    @staticmethod
    def create_backup_directory(base_path: str) -> str:
        """백업 디렉터리 생성"""
        backup_dir = Path(base_path) / "backups"
        backup_dir.mkdir(exist_ok=True)
        return str(backup_dir)
        
    @staticmethod
    def get_file_size_mb(file_path: str) -> float:
        """파일 크기를 MB 단위로 반환"""
        try:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except:
            return 0.0
            
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """파일 크기를 읽기 쉬운 형태로 포맷팅"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
            
    @staticmethod
    def get_image_dimensions(file_path: str) -> Optional[Tuple[int, int]]:
        """이미지 파일의 크기 반환"""
        try:
            from PIL import Image
            with Image.open(file_path) as img:
                return img.size
        except:
            return None
            
    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """파일 경로 유효성 검사"""
        try:
            path = Path(file_path)
            return path.exists() and path.is_file()
        except:
            return False
            
    @staticmethod
    def get_relative_path(base_path: str, file_path: str) -> str:
        """상대 경로 반환"""
        try:
            base = Path(base_path).resolve()
            file = Path(file_path).resolve()
            return str(file.relative_to(base))
        except:
            return file_path
