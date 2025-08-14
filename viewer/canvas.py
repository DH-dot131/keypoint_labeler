"""
Image Canvas for Keypoint Labeler
키포인트 라벨링을 위한 이미지 캔버스
"""

import numpy as np
from typing import List, Tuple, Optional
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider
from PyQt5.QtCore import Qt, pyqtSignal, QRect, QPoint, QSize
from PyQt5.QtGui import QPixmap, QPainter, QPen, QBrush, QColor, QFont, QMouseEvent, QWheelEvent, QKeyEvent

from .dicom_loader import DICOMLoader
from .image_loader import ImageLoader


class ImageCanvas(QWidget):
    """이미지 표시 및 키포인트 편집 캔버스"""
    
    # 시그널 정의
    point_added = pyqtSignal(int, int, int)  # index, x, y
    point_moved = pyqtSignal(int, int, int)  # index, x, y
    point_selected = pyqtSignal(int)  # index
    zoom_changed = pyqtSignal(int)  # zoom percentage
    
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
        self.drag_start_position = None  # 드래그 시작 위치 저장
        
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
        
        # 실행 취소 기능
        self.undo_stack = []  # 실행 취소 스택
        self.max_undo_steps = 50  # 최대 실행 취소 단계
        self.last_added_point = -1  # 마지막으로 추가된 점의 인덱스
        
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
            
            # 디버깅: 이미지 정보 출력
            print(f"DICOM 로드 완료: {file_path}")
            print(f"이미지 shape: {self.image.shape}")
            print(f"이미지 dtype: {self.image.dtype}")
            print(f"이미지 min/max: {self.image.min()}/{self.image.max()}")
            
            # DICOM 윈도우/레벨 설정
            self.window_level = self.dicom_loader.get_default_window_level()
            self.window_width = self.dicom_loader.get_default_window_width()
            
            self.update_display()
        except Exception as e:
            print(f"DICOM 로드 오류: {e}")
            raise Exception(f"DICOM 로드 실패: {e}")
            
    def update_display(self):
        """화면 업데이트"""
        if self.image is None:
            print("이미지가 None입니다")
            return
            
        # 이미지를 QPixmap으로 변환
        if self.is_dicom:
            # DICOM 이미지는 이미 preprocess_dicom으로 처리됨
            print(f"DICOM 이미지 변환: shape={self.image.shape}, dtype={self.image.dtype}")
            self.pixmap = self.image_loader.numpy_to_qpixmap(self.image)
        else:
            # 일반 이미지
            self.pixmap = self.image_loader.numpy_to_qpixmap(self.image)
            
        print(f"QPixmap 생성 완료: {self.pixmap.width()}x{self.pixmap.height()}")
        self.update()
        
    def set_keypoints(self, keypoints: List[List[int]]):
        """키포인트 설정"""
        self.keypoints = keypoints
        self.selected_point = -1
        self.last_added_point = -1
        self.clear_undo_stack()  # 새로운 이미지 로드 시 실행 취소 스택 초기화
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
            # 줌 적용된 이미지 크기 계산
            base_size = self.size()
            zoomed_size = QSize(
                int(base_size.width() * self.zoom_factor),
                int(base_size.height() * self.zoom_factor)
            )
            
            # 이미지를 줌 크기에 맞춤
            scaled_pixmap = self.pixmap.scaled(
                zoomed_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # 중앙 정렬 (패닝 오프셋 적용)
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
            
            # 줌 레벨에 따른 크기 조정
            base_radius = 3
            base_cross_size = 6
            
            # 줌 팩터에 따라 크기 조정 (최소/최대 제한)
            zoom_radius = max(2, min(8, int(base_radius * self.zoom_factor)))
            zoom_cross_size = max(4, min(12, int(base_cross_size * self.zoom_factor)))
            
            # 원 그리기
            painter.drawEllipse(screen_x - zoom_radius, screen_y - zoom_radius, zoom_radius * 2, zoom_radius * 2)
            
            # 십자선 그리기
            painter.drawLine(screen_x - zoom_cross_size, screen_y, screen_x + zoom_cross_size, screen_y)
            painter.drawLine(screen_x, screen_y - zoom_cross_size, screen_x, screen_y + zoom_cross_size)
            
            # 라벨 그리기
            if self.show_labels:
                painter.setPen(QPen(QColor(255, 255, 255), 1))
                painter.setFont(QFont("Arial", 10))
                painter.drawText(screen_x + 10, screen_y - 10, str(i+1))
                
    def mousePressEvent(self, event: QMouseEvent):
        """마우스 클릭 이벤트"""
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.AltModifier:
                # Alt + 좌클릭: 패닝 모드
                self.mouse_mode = 'pan'
            else:
                # 일반 좌클릭: 포인트 선택/추가
                self.mouse_mode = 'select'
                
                # 먼저 포인트 클릭 처리 (선택 또는 추가)
                self.handle_point_click(event.pos())
                
                # 드래그 시작 위치 저장 (기존 점을 선택한 경우)
                image_pos = self.screen_to_image_coords(event.pos())
                if image_pos and self.selected_point >= 0:
                    # 선택된 점이 있고, 그 점 근처를 클릭한 경우
                    x, y = self.keypoints[self.selected_point]
                    distance = ((x - image_pos[0]) ** 2 + (y - image_pos[1]) ** 2) ** 0.5
                    base_min_distance = 20
                    min_distance = max(10, int(base_min_distance / self.zoom_factor))
                    
                    if distance < min_distance:
                        # 드래그 시작 - 현재 위치 저장
                        self.drag_start_position = [x, y]
                        self.dragging = True
                        print(f"드래그 시작: 점 {self.selected_point}, 위치: {self.drag_start_position}")
                    else:
                        self.drag_start_position = None
                        self.dragging = False
                else:
                    self.drag_start_position = None
                    self.dragging = False
        elif event.button() == Qt.RightButton:
            # 우클릭: 최근 추가된 점 삭제
            self.handle_right_click(event.pos())
                
        self.last_mouse_pos = event.pos()
        
    def mouseMoveEvent(self, event: QMouseEvent):
        """마우스 이동 이벤트"""
        if event.buttons() & Qt.LeftButton:
            if self.mouse_mode == 'select' and self.selected_point >= 0:
                # 포인트 드래그
                self.handle_point_drag(event.pos())
            elif self.mouse_mode == 'pan':
                # 이미지 패닝
                delta_x = event.pos().x() - self.last_mouse_pos.x()
                delta_y = event.pos().y() - self.last_mouse_pos.y()
                self.pan_offset.setX(self.pan_offset.x() + delta_x)
                self.pan_offset.setY(self.pan_offset.y() + delta_y)
                self.update()
            
        self.last_mouse_pos = event.pos()
        
    def mouseReleaseEvent(self, event: QMouseEvent):
        """마우스 릴리즈 이벤트"""
        if self.dragging and self.selected_point >= 0 and self.drag_start_position:
            # 드래그가 끝났을 때 실제로 이동했는지 확인
            current_position = self.keypoints[self.selected_point]
            # 실제로 위치가 변경된 경우만 저장 (좌표별 비교)
            if (self.drag_start_position[0] != current_position[0] or 
                self.drag_start_position[1] != current_position[1]):
                
                print(f"드래그 상태 저장: 점 {self.selected_point}, 시작: {self.drag_start_position}, 끝: {current_position}")
                self.save_state_for_undo('move', {
                    'index': self.selected_point,
                    'old_position': self.drag_start_position.copy(),
                    'new_position': current_position.copy()
                })
        
        self.mouse_mode = 'select'
        self.dragging = False
        self.drag_start_position = None
        
    def wheelEvent(self, event: QWheelEvent):
        """마우스 휠 이벤트 (줌)"""
        if event.modifiers() & Qt.ControlModifier:
            # Ctrl+휠: 마우스 포인터 중심 줌
            delta = event.angleDelta().y()
            zoom_factor_change = 1.1 if delta > 0 else 0.9
            
            # 마우스 포인터 위치 저장
            mouse_pos = event.pos()
            
            # 줌 팩터 업데이트
            old_zoom = self.zoom_factor
            self.zoom_factor *= zoom_factor_change
            
            # 줌 범위 제한 (0.1 ~ 10.0)
            self.zoom_factor = max(0.1, min(10.0, self.zoom_factor))
            
            # 마우스 포인터 위치를 중심으로 패닝 조정
            if self.zoom_factor != old_zoom:
                # 마우스 포인터가 이미지 내부에 있는지 확인
                image_rect = self.get_image_rect()
                if image_rect.contains(mouse_pos):
                    # 마우스 포인터 중심으로 줌
                    zoom_ratio = self.zoom_factor / old_zoom
                    new_pan_x = mouse_pos.x() - (mouse_pos.x() - self.pan_offset.x()) * zoom_ratio
                    new_pan_y = mouse_pos.y() - (mouse_pos.y() - self.pan_offset.y()) * zoom_ratio
                    self.pan_offset = QPoint(int(new_pan_x), int(new_pan_y))
            
            self.update()
            # 줌 변경 시그널 발생
            self.zoom_changed.emit(self.get_zoom_percentage())
        else:
            # 일반 휠: 수직 스크롤
            super().wheelEvent(event)
            
    def keyPressEvent(self, event: QKeyEvent):
        """키보드 이벤트"""
        # 실행 취소 (Ctrl+Z)
        if event.modifiers() & Qt.ControlModifier and event.key() == Qt.Key_Z:
            self.undo()
            return
            
        # 줌 단축키 처리
        if event.modifiers() & Qt.ControlModifier:
            key = event.key()
            if key in [Qt.Key_Plus, Qt.Key_Equal, 43, 61]:  # + 키 (Shift+= 또는 +)
                self.zoom_in()
                return
            elif key in [Qt.Key_Minus, 45]:  # - 키
                self.zoom_out()
                return
            elif key == Qt.Key_0:
                self.reset_view()
                return
        
        # 패닝 단축키 (Space + 방향키)
        if event.key() == Qt.Key_Space:
            self.mouse_mode = 'pan'
            return
            
        # 패닝 모드에서 방향키로 이미지 이동
        if self.mouse_mode == 'pan':
            pan_step = 20 if event.modifiers() & Qt.ShiftModifier else 10
            if event.key() == Qt.Key_Left:
                self.pan_offset.setX(self.pan_offset.x() + pan_step)
                self.update()
                return
            elif event.key() == Qt.Key_Right:
                self.pan_offset.setX(self.pan_offset.x() - pan_step)
                self.update()
                return
            elif event.key() == Qt.Key_Up:
                self.pan_offset.setY(self.pan_offset.y() + pan_step)
                self.update()
                return
            elif event.key() == Qt.Key_Down:
                self.pan_offset.setY(self.pan_offset.y() - pan_step)
                self.update()
                return
        
        # 포인트 이동 단축키
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
                
    def keyReleaseEvent(self, event: QKeyEvent):
        """키보드 릴리즈 이벤트"""
        if event.key() == Qt.Key_Space:
            self.mouse_mode = 'select'
                
    def handle_point_click(self, pos: QPoint):
        """포인트 클릭 처리"""
        # 화면 좌표를 이미지 좌표로 변환
        image_pos = self.screen_to_image_coords(pos)
        if image_pos is None:
            return
            
        # 기존 포인트와의 거리 확인 (줌 레벨에 따라 조정)
        base_min_distance = 20
        min_distance = max(10, int(base_min_distance / self.zoom_factor))
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
            # 새 포인트 추가 전에 상태 저장
            self.save_state_for_undo('add', {'position': image_pos})
            self.keypoints.append([image_pos[0], image_pos[1]])
            self.selected_point = len(self.keypoints) - 1
            self.last_added_point = self.selected_point
            self.point_added.emit(self.selected_point, image_pos[0], image_pos[1])
            
        self.update()
        
    def handle_right_click(self, pos: QPoint):
        """우클릭 처리 - 최근 추가된 점 삭제"""
        if self.last_added_point >= 0 and self.last_added_point < len(self.keypoints):
            # 삭제 전에 상태 저장
            deleted_point = self.keypoints[self.last_added_point]
            self.save_state_for_undo('delete', {'index': self.last_added_point, 'point': deleted_point})
            
            # 최근 추가된 점 삭제
            del self.keypoints[self.last_added_point]
            
            # 선택 상태 업데이트
            if self.selected_point == self.last_added_point:
                self.selected_point = -1
            elif self.selected_point > self.last_added_point:
                self.selected_point -= 1
                
            self.last_added_point = -1  # 리셋
            self.update()
            
            # 시그널 발생
            self.point_moved.emit(-1, 0, 0)  # UI 업데이트를 위한 시그널
        
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
            
        # 포인트 이동 (상태 저장은 이미 mousePressEvent에서 했으므로 여기서는 하지 않음)
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
        
        # 실행 취소를 위한 상태 저장 (이동 전 위치만 저장)
        old_position = self.keypoints[self.selected_point].copy()
        self.save_state_for_undo('move', {'index': self.selected_point, 'old_position': old_position, 'new_position': [new_x, new_y]})
        
        self.keypoints[self.selected_point] = [new_x, new_y]
        self.point_moved.emit(self.selected_point, new_x, new_y)
        self.update()
        
    def delete_selected_point(self):
        """선택된 포인트 삭제"""
        if self.selected_point >= 0 and self.selected_point < len(self.keypoints):
            # 실행 취소를 위한 상태 저장
            deleted_point = self.keypoints[self.selected_point]
            self.save_state_for_undo('delete', {'index': self.selected_point, 'point': deleted_point})
            
            del self.keypoints[self.selected_point]
            self.selected_point = -1
            self.update()
            
    def screen_to_image_coords(self, screen_pos: QPoint) -> Optional[Tuple[int, int]]:
        """화면 좌표를 이미지 좌표로 변환"""
        if not self.pixmap:
            return None
            
        # 줌 적용된 이미지 크기 계산
        base_size = self.size()
        zoomed_size = QSize(
            int(base_size.width() * self.zoom_factor),
            int(base_size.height() * self.zoom_factor)
        )
        
        # 이미지를 줌 크기에 맞춤
        scaled_pixmap = self.pixmap.scaled(
            zoomed_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # 이미지 영역 계산 (패닝 오프셋 포함)
        image_x = (self.width() - scaled_pixmap.width()) // 2 + self.pan_offset.x()
        image_y = (self.height() - scaled_pixmap.height()) // 2 + self.pan_offset.y()
        
        # 이미지 영역 내인지 확인
        if (image_x <= screen_pos.x() <= image_x + scaled_pixmap.width() and
            image_y <= screen_pos.y() <= image_y + scaled_pixmap.height()):
            
            # 상대 좌표 계산
            rel_x = (screen_pos.x() - image_x) / scaled_pixmap.width() * self.pixmap.width()
            rel_y = (screen_pos.y() - image_y) / scaled_pixmap.height() * self.pixmap.height()
            
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
        self.zoom_factor = min(10.0, self.zoom_factor)
        self.update()
        self.zoom_changed.emit(self.get_zoom_percentage())
        
    def zoom_out(self):
        """축소"""
        self.zoom_factor /= 1.2
        self.zoom_factor = max(0.1, self.zoom_factor)
        self.update()
        self.zoom_changed.emit(self.get_zoom_percentage())
        
    def get_image_rect(self) -> QRect:
        """현재 이미지의 화면상 위치와 크기 반환"""
        if not self.pixmap:
            return QRect()
            
        # 줌 적용된 이미지 크기 계산
        base_size = self.size()
        zoomed_size = QSize(
            int(base_size.width() * self.zoom_factor),
            int(base_size.height() * self.zoom_factor)
        )
        
        # 이미지를 줌 크기에 맞춤
        scaled_pixmap = self.pixmap.scaled(
            zoomed_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        
        # 이미지 위치 계산
        x = (self.width() - scaled_pixmap.width()) // 2 + self.pan_offset.x()
        y = (self.height() - scaled_pixmap.height()) // 2 + self.pan_offset.y()
        
        return QRect(x, y, scaled_pixmap.width(), scaled_pixmap.height())
        
    def get_zoom_percentage(self) -> int:
        """현재 줌 레벨을 퍼센트로 반환"""
        return int(self.zoom_factor * 100)
        
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
        self.zoom_changed.emit(self.get_zoom_percentage())
        

    def save_state_for_undo(self, action_type: str, data=None):
        """실행 취소를 위한 상태 저장"""
        # 모든 작업에 대해 전체 상태 저장
        state = {
            'action_type': action_type,
            'keypoints_before': [kp.copy() for kp in self.keypoints],  # 깊은 복사
            'selected_point_before': self.selected_point,
            'data': data
        }
        
        self.undo_stack.append(state)
        
        # 최대 단계 제한
        if len(self.undo_stack) > self.max_undo_steps:
            self.undo_stack.pop(0)
            
    def undo(self):
        """실행 취소"""
        if not self.undo_stack:
            print("실행 취소할 작업이 없습니다")
            return
        
        # 이전 상태 복원
        previous_state = self.undo_stack.pop()
        print(f"실행 취소: {previous_state['action_type']}, 스택 크기: {len(self.undo_stack)}")
        
        if previous_state['action_type'] == 'move':
            # 이동 취소: 해당 점의 위치만 복원
            data = previous_state['data']
            if data and 'index' in data and 'old_position' in data:
                index = data['index']
                old_position = data['old_position']
                if 0 <= index < len(self.keypoints):
                    self.keypoints[index] = old_position.copy()
                    self.selected_point = index
                    print(f"이동 취소: 점 {index}를 {old_position}로 복원")
        else:
            # 추가/삭제 취소: 전체 상태 복원
            self.keypoints = [kp.copy() for kp in previous_state['keypoints_before']]
            self.selected_point = previous_state['selected_point_before']
            
            # last_added_point 업데이트
            if previous_state['action_type'] == 'add':
                self.last_added_point = -1
            print(f"전체 상태 복원: {len(self.keypoints)}개 점")
        
        # UI 업데이트
        self.update()
        
        # 메인 앱에 변경사항 알림
        self.point_moved.emit(-1, 0, 0)
            
    def can_undo(self) -> bool:
        """실행 취소 가능 여부"""
        return len(self.undo_stack) > 0
        
    def clear_undo_stack(self):
        """실행 취소 스택 초기화"""
        self.undo_stack.clear()
        self.last_added_point = -1
