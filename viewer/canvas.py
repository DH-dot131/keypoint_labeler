"""
Image Canvas for Keypoint Labeler
키포인트 라벨링을 위한 이미지 캔버스
"""

import numpy as np
from typing import List, Tuple, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QWheelEvent, QKeyEvent

from .dicom_loader import DICOMLoader
from .image_loader import ImageLoader


class ImageCanvas(QWidget):
    """이미지 표시 및 키포인트 편집 캔버스"""
    
    # 시그널 정의
    point_added = pyqtSignal(int, int)  # x, y
    point_moved = pyqtSignal(int, int, int)  # index, x, y
    point_selected = pyqtSignal(int)  # index
    
    def __init__(self):
        super().__init__()
        self.image = None
        self.pixmap = None
        self.keypoints = []
        self.selected_point = -1
        self.dragging = False
        self.show_labels = True
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        
        # DICOM 관련
        self.dicom_loader = None
        self.window_level = 0
        self.window_width = 255
        self.is_dicom = False
        
        # 이미지 로더
        self.image_loader = ImageLoader()
        
        # UI 설정
        self.setMinimumSize(400, 300)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # 마우스 상태
        self.last_mouse_pos = QPoint()
        self.mouse_mode = 'select'  # 'select', 'pan', 'window_level'
        
    def load_image(self, file_path: str):
        """일반 이미지 파일 로드"""
        try:
            self.image = self.image_loader.load_image(file_path)
            self.is_dicom = False
            self.dicom_loader = None
            self.update_display()
        except Exception as e:
            raise Exception(f"이미지 로드 실패: {e}")
            
    def load_dicom(self, file_path: str):
        """DICOM 파일 로드"""
        try:
            self.dicom_loader = DICOMLoader(file_path)
            self.image = self.dicom_loader.get_image()
            self.is_dicom = True
            
            # DICOM 윈도우/레벨 설정
            self.window_level = self.dicom_loader.get_default_window_level()
            self.window_width = self.dicom_loader.get_default_window_width()
            
            self.update_display()
        except Exception as e:
            raise Exception(f"DICOM 로드 실패: {e}")
            
    def update_display(self):
        """화면 업데이트"""
        if self.image is None:
            return
            
        # 이미지를 QPixmap으로 변환
        if self.is_dicom:
            # DICOM 이미지 처리
            processed_image = self.dicom_loader.apply_window_level(
                self.image, self.window_level, self.window_width
            )
            self.pixmap = self.image_loader.numpy_to_qpixmap(processed_image)
        else:
            # 일반 이미지
            self.pixmap = self.image_loader.numpy_to_qpixmap(self.image)
            
        self.update()
        
    def set_keypoints(self, keypoints: List[List[int]]):
        """키포인트 설정"""
        self.keypoints = keypoints
        self.update()
        
    def select_keypoint(self, index: int):
        """키포인트 선택"""
        self.selected_point = index
        self.update()
        
    def set_show_labels(self, show: bool):
        """라벨 표시 설정"""
        self.show_labels = show
        self.update()
        
    def set_window_level(self, level: int):
        """DICOM Window Level 설정"""
        if self.is_dicom:
            self.window_level = level
            self.update_display()
            
    def set_window_width(self, width: int):
        """DICOM Window Width 설정"""
        if self.is_dicom:
            self.window_width = width
            self.update_display()
            
    def set_dicom_preset(self, preset: str):
        """DICOM 프리셋 설정"""
        if not self.is_dicom:
            return
            
        presets = {
            'Soft Tissue': (40, 400),
            'Bone': (300, 1500),
            'Lung': (-600, 1600),
            'General': (0, 255)
        }
        
        if preset in presets:
            level, width = presets[preset]
            self.window_level = level
            self.window_width = width
            self.update_display()
            
    def paintEvent(self, event):
        """그리기 이벤트"""
        if self.pixmap is None:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 배경 그리기
        painter.fillRect(self.rect(), QColor(50, 50, 50))
        
        # 이미지 그리기
        if self.pixmap:
            # 줌 및 팬 적용
            scaled_pixmap = self.pixmap.scaled(
                self.pixmap.size() * self.zoom_factor,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 중앙 정렬
            x = (self.width() - scaled_pixmap.width()) // 2 + self.pan_offset.x()
            y = (self.height() - scaled_pixmap.height()) // 2 + self.pan_offset.y()
            
            painter.drawPixmap(x, y, scaled_pixmap)
            
            # 키포인트 그리기
            self.draw_keypoints(painter, x, y, scaled_pixmap.size())
            
    def draw_keypoints(self, painter: QPainter, offset_x: int, offset_y: int, image_size):
        """키포인트 그리기"""
        if not self.keypoints:
            return
            
        # 좌표 변환 (이미지 좌표 → 화면 좌표)
        scale_x = image_size.width() / self.pixmap.width()
        scale_y = image_size.height() / self.pixmap.height()
        
        for i, (x, y) in enumerate(self.keypoints):
            # 화면 좌표로 변환
            screen_x = int(x * scale_x) + offset_x
            screen_y = int(y * scale_y) + offset_y
            
            # 색상 설정
            if i == self.selected_point:
                color = QColor(255, 255, 0)  # 노란색 (선택됨)
                pen_width = 3
            else:
                color = QColor(255, 0, 0)  # 빨간색
                pen_width = 2
                
            # 포인트 그리기
            painter.setPen(QPen(color, pen_width))
            painter.setBrush(QBrush(color))
            
            # 원 그리기
            radius = 6
            painter.drawEllipse(screen_x - radius, screen_y - radius, radius * 2, radius * 2)
            
            # 십자선 그리기
            cross_size = 8
            painter.drawLine(screen_x - cross_size, screen_y, screen_x + cross_size, screen_y)
            painter.drawLine(screen_x, screen_y - cross_size, screen_x, screen_y + cross_size)
            
            # 라벨 그리기
            if self.show_labels:
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.setFont(QFont("Arial", 10))
                painter.drawText(screen_x + 10, screen_y - 10, str(i))
                
    def mousePressEvent(self, event: QMouseEvent):
        """마우스 클릭 이벤트"""
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.ControlModifier:
                # Ctrl+클릭: 팬 모드
                self.mouse_mode = 'pan'
            elif self.is_dicom and event.modifiers() & Qt.ShiftModifier:
                # Shift+클릭: 윈도우/레벨 모드
                self.mouse_mode = 'window_level'
            else:
                # 일반 클릭: 포인트 선택/추가
                self.mouse_mode = 'select'
                self.handle_point_click(event.pos())
                
        self.last_mouse_pos = event.pos()
        
    def mouseMoveEvent(self, event: QMouseEvent):
        """마우스 이동 이벤트"""
        if self.mouse_mode == 'pan' and event.buttons() & Qt.LeftButton:
            # 팬 처리
            delta = event.pos() - self.last_mouse_pos
            self.pan_offset += delta
            self.update()
        elif self.mouse_mode == 'window_level' and event.buttons() & Qt.LeftButton and self.is_dicom:
            # 윈도우/레벨 처리
            delta = event.pos() - self.last_mouse_pos
            self.window_width += delta.x()
            self.window_level += delta.y()
            
            # 범위 제한
            self.window_width = max(1, min(4000, self.window_width))
            self.window_level = max(-2000, min(2000, self.window_level))
            
            self.update_display()
        elif self.mouse_mode == 'select' and event.buttons() & Qt.LeftButton and self.selected_point >= 0:
            # 포인트 드래그
            self.handle_point_drag(event.pos())
            
        self.last_mouse_pos = event.pos()
        
    def mouseReleaseEvent(self, event: QMouseEvent):
        """마우스 릴리즈 이벤트"""
        self.mouse_mode = 'select'
        
    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠 이벤트 (줌)"""
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl+휠: 줌
            delta = event.angleDelta().y()
            if delta > 0:
                self.zoom_factor *= 1.1
            else:
                self.zoom_factor /= 1.1
                
            # 줌 범위 제한
            self.zoom_factor = max(0.1, min(5.0, self.zoom_factor))
            self.update()
        else:
            # 일반 휠: 수직 스크롤
            super().wheelEvent(event)
            
    def keyPressEvent(self, event: QKeyEvent):
        """키보드 이벤트"""
        if self.selected_point >= 0:
            step = 10 if event.modifiers() & Qt.ShiftModifier else 1
            
            if event.key() == Qt.Key_Left:
                self.move_selected_point(-step, 0)
            elif event.key() == Qt.Key_Right:
                self.move_selected_point(step, 0)
            elif event.key() == Qt.Key_Up:
                self.move_selected_point(0, -step)
            elif event.key() == Qt.Key_Down:
                self.move_selected_point(0, step)
            elif event.key() == Qt.Key_Delete:
                self.delete_selected_point()
                
    def handle_point_click(self, pos: QPoint):
        """포인트 클릭 처리"""
        # 화면 좌표를 이미지 좌표로 변환
        image_pos = self.screen_to_image_coords(pos)
        if image_pos is None:
            return
            
        # 기존 포인트와의 거리 확인
        min_distance = 20
        closest_point = -1
        
        for i, (x, y) in enumerate(self.keypoints):
            distance = ((x - image_pos[0]) ** 2 + (y - image_pos[1]) ** 2) ** 0.5
            if distance < min_distance:
                min_distance = distance
                closest_point = i
                
        if closest_point >= 0:
            # 기존 포인트 선택
            self.selected_point = closest_point
            self.point_selected.emit(closest_point)
        else:
            # 새 포인트 추가
            self.keypoints.append([image_pos[0], image_pos[1]])
            self.selected_point = len(self.keypoints) - 1
            self.point_added.emit(image_pos[0], image_pos[1])
            
        self.update()
        
    def handle_point_drag(self, pos: QPoint):
        """포인트 드래그 처리"""
        if self.selected_point < 0:
            return
            
        # 화면 좌표를 이미지 좌표로 변환
        image_pos = self.screen_to_image_coords(pos)
        if image_pos is None:
            return
            
        # 좌표 범위 제한
        if self.pixmap:
            x = max(0, min(self.pixmap.width() - 1, image_pos[0]))
            y = max(0, min(self.pixmap.height() - 1, image_pos[1]))
        else:
            x, y = image_pos
            
        # 포인트 이동
        self.keypoints[self.selected_point] = [x, y]
        self.point_moved.emit(self.selected_point, x, y)
        self.update()
        
    def move_selected_point(self, dx: int, dy: int):
        """선택된 포인트 이동"""
        if self.selected_point < 0 or self.selected_point >= len(self.keypoints):
            return
            
        x, y = self.keypoints[self.selected_point]
        new_x = max(0, min(self.pixmap.width() - 1 if self.pixmap else 9999, x + dx))
        new_y = max(0, min(self.pixmap.height() - 1 if self.pixmap else 9999, y + dy))
        
        self.keypoints[self.selected_point] = [new_x, new_y]
        self.point_moved.emit(self.selected_point, new_x, new_y)
        self.update()
        
    def delete_selected_point(self):
        """선택된 포인트 삭제"""
        if self.selected_point >= 0 and self.selected_point < len(self.keypoints):
            del self.keypoints[self.selected_point]
            self.selected_point = -1
            self.update()
            
    def screen_to_image_coords(self, screen_pos: QPoint) -> Optional[Tuple[int, int]]:
        """화면 좌표를 이미지 좌표로 변환"""
        if not self.pixmap:
            return None
            
        # 이미지 영역 계산
        scaled_size = self.pixmap.size() * self.zoom_factor
        image_x = (self.width() - scaled_size.width()) // 2 + self.pan_offset.x()
        image_y = (self.height() - scaled_size.height()) // 2 + self.pan_offset.y()
        
        # 이미지 영역 내인지 확인
        if (image_x <= screen_pos.x() <= image_x + scaled_size.width() and
            image_y <= screen_pos.y() <= image_y + scaled_size.height()):
            
            # 상대 좌표 계산
            rel_x = (screen_pos.x() - image_x) / self.zoom_factor
            rel_y = (screen_pos.y() - image_y) / self.zoom_factor
            
            return (int(rel_x), int(rel_y))
            
        return None
        
    def fit_to_window(self):
        """창에 맞춤"""
        if self.pixmap:
            self.zoom_factor = 1.0
            self.pan_offset = QPoint(0, 0)
            self.update()
            
    def zoom_in(self):
        """확대"""
        self.zoom_factor *= 1.2
        self.zoom_factor = min(5.0, self.zoom_factor)
        self.update()
        
    def zoom_out(self):
        """축소"""
        self.zoom_factor /= 1.2
        self.zoom_factor = max(0.1, self.zoom_factor)
        self.update()
        
    def reset_view(self):
        """뷰 리셋"""
        self.zoom_factor = 1.0
        self.pan_offset = QPoint(0, 0)
        if self.is_dicom:
            self.window_level = self.dicom_loader.get_default_window_level()
            self.window_width = self.dicom_loader.get_default_window_width()
            self.update_display()
        else:
            self.update()
