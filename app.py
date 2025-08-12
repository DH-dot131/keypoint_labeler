#!/usr/bin/env python3
"""
Keypoint Labeler Application
키포인트 라벨링을 위한 로컬 애플리케이션

지원 파일 형식: DICOM(.dcm), JPG(.jpg/.jpeg), PNG(.png)
결과 저장: JSON 형식 (coord 배열)
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QFileDialog, QMessageBox, QAction, QMenuBar,
    QToolBar, QStatusBar, QSplitter, QListWidget, QLabel,
    QSlider, QPushButton, QCheckBox, QSpinBox, QComboBox,
    QGroupBox, QGridLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPen, QBrush, QColor, QFont

from viewer.canvas import ImageCanvas
from viewer.dicom_loader import DICOMLoader
from viewer.image_loader import ImageLoader
from viewer.json_io import JSONIO
from viewer.tools import Tools

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 로그 디렉터리 생성
os.makedirs('logs', exist_ok=True)


class KeypointLabeler(QMainWindow):
    """키포인트 라벨링 메인 윈도우"""
    
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.current_folder = None
        self.folder_files = []
        self.current_index = -1
        self.keypoints = []
        self.auto_save = True
        self.settings = self.load_settings()
        
        self.init_ui()
        self.setup_connections()
        self.load_recent_folder()
        
    def init_ui(self):
        """UI 초기화"""
        self.setWindowTitle("키포인트 라벨러 v1.0")
        self.setGeometry(100, 100, 1400, 900)
        
        # 중앙 위젯
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 메인 레이아웃
        main_layout = QHBoxLayout(central_widget)
        
        # 스플리터 생성
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)
        
        # 캔버스 영역
        self.canvas = ImageCanvas()
        splitter.addWidget(self.canvas)
        
        # 사이드 패널
        self.create_side_panel()
        splitter.addWidget(self.side_panel)
        
        # 스플리터 비율 설정
        splitter.setSizes([1000, 400])
        
        # 메뉴바 생성
        self.create_menu_bar()
        
        # 툴바 생성
        self.create_toolbar()
        
        # 상태바 생성
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("준비됨")
        
    def create_side_panel(self):
        """사이드 패널 생성"""
        self.side_panel = QWidget()
        layout = QVBoxLayout(self.side_panel)
        
        # 키포인트 리스트
        keypoint_group = QGroupBox("키포인트 목록")
        keypoint_layout = QVBoxLayout(keypoint_group)
        
        self.keypoint_list = QListWidget()
        self.keypoint_list.setDragDropMode(QListWidget.InternalMove)
        keypoint_layout.addWidget(self.keypoint_list)
        
        # 키포인트 버튼들
        button_layout = QHBoxLayout()
        self.add_point_btn = QPushButton("추가")
        self.delete_point_btn = QPushButton("삭제")
        self.clear_all_btn = QPushButton("전체 삭제")
        self.swap_points_btn = QPushButton("교환")
        
        button_layout.addWidget(self.add_point_btn)
        button_layout.addWidget(self.delete_point_btn)
        button_layout.addWidget(self.clear_all_btn)
        button_layout.addWidget(self.swap_points_btn)
        keypoint_layout.addLayout(button_layout)
        
        layout.addWidget(keypoint_group)
        
        # 뷰어 컨트롤
        viewer_group = QGroupBox("뷰어 설정")
        viewer_layout = QGridLayout(viewer_group)
        
        self.show_labels_cb = QCheckBox("라벨 표시")
        self.show_labels_cb.setChecked(True)
        viewer_layout.addWidget(self.show_labels_cb, 0, 0)
        
        self.auto_save_cb = QCheckBox("자동 저장")
        self.auto_save_cb.setChecked(self.auto_save)
        viewer_layout.addWidget(self.auto_save_cb, 0, 1)
        
        # DICOM 컨트롤 (초기에는 숨김)
        self.dicom_group = QGroupBox("DICOM 설정")
        self.dicom_layout = QGridLayout(self.dicom_group)
        
        self.window_level_slider = QSlider(Qt.Horizontal)
        self.window_width_slider = QSlider(Qt.Horizontal)
        self.window_level_label = QLabel("Window Level: 0")
        self.window_width_label = QLabel("Window Width: 0")
        
        self.dicom_layout.addWidget(self.window_level_label, 0, 0)
        self.dicom_layout.addWidget(self.window_level_slider, 0, 1)
        self.dicom_layout.addWidget(self.window_width_label, 1, 0)
        self.dicom_layout.addWidget(self.window_width_slider, 1, 1)
        
        self.dicom_preset_combo = QComboBox()
        self.dicom_preset_combo.addItems(["Soft Tissue", "Bone", "Lung", "General"])
        self.dicom_layout.addWidget(QLabel("프리셋:"), 2, 0)
        self.dicom_layout.addWidget(self.dicom_preset_combo, 2, 1)
        
        self.dicom_group.setVisible(False)
        layout.addWidget(self.dicom_group)
        
        # 파일 네비게이션
        nav_group = QGroupBox("파일 탐색")
        nav_layout = QHBoxLayout(nav_group)
        
        self.prev_btn = QPushButton("이전")
        self.next_btn = QPushButton("다음")
        self.file_info_label = QLabel("파일 없음")
        
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.file_info_label)
        nav_layout.addWidget(self.next_btn)
        
        layout.addWidget(nav_group)
        
        # 스페이서 추가
        layout.addStretch()
        
    def create_menu_bar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        
        # 파일 메뉴
        file_menu = menubar.addMenu('파일(&F)')
        
        open_file_action = QAction('파일 열기(&O)', self)
        open_file_action.setShortcut('Ctrl+O')
        open_file_action.triggered.connect(self.open_file)
        file_menu.addAction(open_file_action)
        
        open_folder_action = QAction('폴더 열기(&F)', self)
        open_folder_action.setShortcut('Ctrl+Shift+O')
        open_folder_action.triggered.connect(self.open_folder)
        file_menu.addAction(open_folder_action)
        
        file_menu.addSeparator()
        
        save_action = QAction('저장(&S)', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_current)
        file_menu.addAction(save_action)
        
        save_all_action = QAction('전체 저장(&A)', self)
        save_all_action.setShortcut('Ctrl+Shift+S')
        save_all_action.triggered.connect(self.save_all)
        file_menu.addAction(save_all_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('종료(&X)', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 편집 메뉴
        edit_menu = menubar.addMenu('편집(&E)')
        
        undo_action = QAction('실행 취소(&U)', self)
        undo_action.setShortcut('Ctrl+Z')
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('다시 실행(&R)', self)
        redo_action.setShortcut('Ctrl+Y')
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        delete_point_action = QAction('포인트 삭제(&D)', self)
        delete_point_action.setShortcut('Delete')
        delete_point_action.triggered.connect(self.delete_selected_point)
        edit_menu.addAction(delete_point_action)
        
        # 보기 메뉴
        view_menu = menubar.addMenu('보기(&V)')
        
        zoom_in_action = QAction('확대(&I)', self)
        zoom_in_action.setShortcut('Ctrl++')
        view_menu.addAction(zoom_in_action)
        
        zoom_out_action = QAction('축소(&O)', self)
        zoom_out_action.setShortcut('Ctrl+-')
        view_menu.addAction(zoom_out_action)
        
        fit_window_action = QAction('창에 맞춤(&F)', self)
        fit_window_action.setShortcut('Ctrl+0')
        view_menu.addAction(fit_window_action)
        
        view_menu.addSeparator()
        
        flip_h_action = QAction('좌우 반전(&H)', self)
        view_menu.addAction(flip_h_action)
        
        flip_v_action = QAction('상하 반전(&V)', self)
        view_menu.addAction(flip_v_action)
        
        rotate_action = QAction('90도 회전(&R)', self)
        rotate_action.setShortcut('Ctrl+R')
        view_menu.addAction(rotate_action)
        
    def create_toolbar(self):
        """툴바 생성"""
        toolbar = self.addToolBar('메인 툴바')
        
        # 파일 관련
        open_file_action = QAction('파일 열기', self)
        open_file_action.triggered.connect(self.open_file)
        toolbar.addAction(open_file_action)
        
        open_folder_action = QAction('폴더 열기', self)
        open_folder_action.triggered.connect(self.open_folder)
        toolbar.addAction(open_folder_action)
        
        toolbar.addSeparator()
        
        # 저장 관련
        save_action = QAction('저장', self)
        save_action.triggered.connect(self.save_current)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # 네비게이션
        prev_action = QAction('이전', self)
        prev_action.triggered.connect(self.prev_file)
        toolbar.addAction(prev_action)
        
        next_action = QAction('다음', self)
        next_action.triggered.connect(self.next_file)
        toolbar.addAction(next_action)
        
    def setup_connections(self):
        """시그널 연결"""
        # 캔버스 시그널
        self.canvas.point_added.connect(self.add_keypoint)
        self.canvas.point_moved.connect(self.move_keypoint)
        self.canvas.point_selected.connect(self.select_keypoint)
        
        # 사이드 패널 시그널
        self.keypoint_list.itemSelectionChanged.connect(self.on_keypoint_selection_changed)
        self.keypoint_list.model().rowsMoved.connect(self.on_keypoint_order_changed)
        
        self.add_point_btn.clicked.connect(self.add_keypoint_manual)
        self.delete_point_btn.clicked.connect(self.delete_selected_point)
        self.clear_all_btn.clicked.connect(self.clear_all_keypoints)
        self.swap_points_btn.clicked.connect(self.swap_selected_points)
        
        self.show_labels_cb.toggled.connect(self.canvas.set_show_labels)
        self.auto_save_cb.toggled.connect(self.set_auto_save)
        
        # DICOM 컨트롤 시그널
        self.window_level_slider.valueChanged.connect(self.on_window_level_changed)
        self.window_width_slider.valueChanged.connect(self.on_window_width_changed)
        self.dicom_preset_combo.currentTextChanged.connect(self.on_dicom_preset_changed)
        
        # 네비게이션 시그널
        self.prev_btn.clicked.connect(self.prev_file)
        self.next_btn.clicked.connect(self.next_file)
        
    def open_file(self):
        """파일 열기"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "파일 열기", "",
            "이미지 파일 (*.dcm *.jpg *.jpeg *.png);;DICOM 파일 (*.dcm);;이미지 파일 (*.jpg *.jpeg *.png);;모든 파일 (*)"
        )
        
        if file_path:
            self.load_file(file_path)
            
    def open_folder(self):
        """폴더 열기"""
        folder_path = QFileDialog.getExistingDirectory(self, "폴더 열기")
        
        if folder_path:
            self.load_folder(folder_path)
            
    def load_file(self, file_path: str):
        """파일 로드"""
        try:
            file_path = Path(file_path)
            
            # 이미지 로드
            if file_path.suffix.lower() == '.dcm':
                self.canvas.load_dicom(str(file_path))
                self.dicom_group.setVisible(True)
            else:
                self.canvas.load_image(str(file_path))
                self.dicom_group.setVisible(False)
            
            # JSON 로드
            json_path = file_path.with_suffix('.json')
            if json_path.exists():
                self.keypoints = JSONIO.load_keypoints(str(json_path))
            else:
                self.keypoints = []
            
            self.current_file = str(file_path)
            self.update_keypoint_list()
            self.canvas.set_keypoints(self.keypoints)
            self.update_status()
            
            # 최근 폴더 저장
            self.save_recent_folder(str(file_path.parent))
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"파일을 로드할 수 없습니다: {str(e)}")
            logger.error(f"파일 로드 오류: {e}")
            
    def load_folder(self, folder_path: str):
        """폴더 로드"""
        try:
            folder_path = Path(folder_path)
            self.current_folder = str(folder_path)
            
            # 지원 파일 확장자
            extensions = {'.dcm', '.jpg', '.jpeg', '.png'}
            
            # 파일 목록 생성
            self.folder_files = [
                str(f) for f in folder_path.iterdir()
                if f.is_file() and f.suffix.lower() in extensions
            ]
            
            # 자연 정렬
            self.folder_files.sort(key=lambda x: [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', x)])
            
            if self.folder_files:
                self.current_index = 0
                self.load_file(self.folder_files[0])
            else:
                QMessageBox.information(self, "알림", "지원하는 이미지 파일이 없습니다.")
                
            # 최근 폴더 저장
            self.save_recent_folder(folder_path)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"폴더를 로드할 수 없습니다: {str(e)}")
            logger.error(f"폴더 로드 오류: {e}")
            
    def prev_file(self):
        """이전 파일"""
        if self.folder_files and self.current_index > 0:
            self.save_current_if_needed()
            self.current_index -= 1
            self.load_file(self.folder_files[self.current_index])
            
    def next_file(self):
        """다음 파일"""
        if self.folder_files and self.current_index < len(self.folder_files) - 1:
            self.save_current_if_needed()
            self.current_index += 1
            self.load_file(self.folder_files[self.current_index])
            
    def save_current_if_needed(self):
        """필요시 현재 파일 저장"""
        if self.auto_save and self.current_file and self.keypoints:
            self.save_current()
            
    def save_current(self):
        """현재 파일 저장"""
        if not self.current_file:
            return
            
        try:
            json_path = Path(self.current_file).with_suffix('.json')
            JSONIO.save_keypoints(str(json_path), self.keypoints)
            self.status_bar.showMessage(f"저장됨: {json_path.name}", 3000)
            
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장할 수 없습니다: {str(e)}")
            logger.error(f"저장 오류: {e}")
            
    def save_all(self):
        """전체 파일 저장"""
        if not self.folder_files:
            return
            
        saved_count = 0
        for file_path in self.folder_files:
            try:
                json_path = Path(file_path).with_suffix('.json')
                # 각 파일의 키포인트를 로드하여 저장
                if json_path.exists():
                    keypoints = JSONIO.load_keypoints(str(json_path))
                    JSONIO.save_keypoints(str(json_path), keypoints)
                    saved_count += 1
            except Exception as e:
                logger.error(f"파일 저장 오류 {file_path}: {e}")
                
        self.status_bar.showMessage(f"{saved_count}개 파일 저장됨", 3000)
        
    def add_keypoint(self, x: int, y: int):
        """키포인트 추가"""
        self.keypoints.append([x, y])
        self.update_keypoint_list()
        self.canvas.set_keypoints(self.keypoints)
        
    def add_keypoint_manual(self):
        """수동으로 키포인트 추가"""
        # 캔버스 중앙에 추가
        center_x = self.canvas.width() // 2
        center_y = self.canvas.height() // 2
        self.add_keypoint(center_x, center_y)
        
    def move_keypoint(self, index: int, x: int, y: int):
        """키포인트 이동"""
        if 0 <= index < len(self.keypoints):
            self.keypoints[index] = [x, y]
            self.update_keypoint_list()
            
    def select_keypoint(self, index: int):
        """키포인트 선택"""
        if 0 <= index < self.keypoint_list.count():
            self.keypoint_list.setCurrentRow(index)
            
    def delete_selected_point(self):
        """선택된 포인트 삭제"""
        current_row = self.keypoint_list.currentRow()
        if current_row >= 0:
            del self.keypoints[current_row]
            self.update_keypoint_list()
            self.canvas.set_keypoints(self.keypoints)
            
    def clear_all_keypoints(self):
        """모든 키포인트 삭제"""
        self.keypoints.clear()
        self.update_keypoint_list()
        self.canvas.set_keypoints(self.keypoints)
        
    def swap_selected_points(self):
        """선택된 두 포인트 교환"""
        selected_rows = [item.row() for item in self.keypoint_list.selectedItems()]
        if len(selected_rows) == 2:
            i, j = selected_rows
            self.keypoints[i], self.keypoints[j] = self.keypoints[j], self.keypoints[i]
            self.update_keypoint_list()
            self.canvas.set_keypoints(self.keypoints)
            
    def update_keypoint_list(self):
        """키포인트 리스트 업데이트"""
        self.keypoint_list.clear()
        for i, (x, y) in enumerate(self.keypoints):
            self.keypoint_list.addItem(f"{i}: ({x}, {y})")
            
    def on_keypoint_selection_changed(self):
        """키포인트 선택 변경"""
        current_row = self.keypoint_list.currentRow()
        if current_row >= 0:
            self.canvas.select_keypoint(current_row)
            
    def on_keypoint_order_changed(self):
        """키포인트 순서 변경"""
        # 리스트에서 새로운 순서로 키포인트 재정렬
        new_keypoints = []
        for i in range(self.keypoint_list.count()):
            item_text = self.keypoint_list.item(i).text()
            # "0: (x, y)" 형식에서 좌표 추출
            coord_str = item_text.split(': ')[1].strip('()')
            x, y = map(int, coord_str.split(', '))
            new_keypoints.append([x, y])
            
        self.keypoints = new_keypoints
        self.canvas.set_keypoints(self.keypoints)
        
    def set_auto_save(self, enabled: bool):
        """자동 저장 설정"""
        self.auto_save = enabled
        
    def on_window_level_changed(self, value: int):
        """DICOM Window Level 변경"""
        if hasattr(self.canvas, 'set_window_level'):
            self.canvas.set_window_level(value)
            self.window_level_label.setText(f"Window Level: {value}")
            
    def on_window_width_changed(self, value: int):
        """DICOM Window Width 변경"""
        if hasattr(self.canvas, 'set_window_width'):
            self.canvas.set_window_width(value)
            self.window_width_label.setText(f"Window Width: {value}")
            
    def on_dicom_preset_changed(self, preset: str):
        """DICOM 프리셋 변경"""
        if hasattr(self.canvas, 'set_dicom_preset'):
            self.canvas.set_dicom_preset(preset)
            
    def update_status(self):
        """상태바 업데이트"""
        if self.current_file:
            filename = Path(self.current_file).name
            if self.folder_files:
                self.file_info_label.setText(f"{self.current_index + 1}/{len(self.folder_files)}: {filename}")
            else:
                self.file_info_label.setText(filename)
        else:
            self.file_info_label.setText("파일 없음")
            
    def load_settings(self) -> Dict[str, Any]:
        """설정 로드"""
        try:
            if os.path.exists('settings.json'):
                with open('settings.json', 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"설정 로드 오류: {e}")
        return {}
        
    def save_settings(self):
        """설정 저장"""
        try:
            settings = {
                'recent_folder': self.current_folder,
                'auto_save': self.auto_save,
                'window_geometry': {
                    'x': self.geometry().x(),
                    'y': self.geometry().y(),
                    'width': self.geometry().width(),
                    'height': self.geometry().height()
                }
            }
            
            with open('settings.json', 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"설정 저장 오류: {e}")
            
    def load_recent_folder(self):
        """최근 폴더 로드"""
        recent_folder = self.settings.get('recent_folder')
        if recent_folder and os.path.exists(recent_folder):
            self.load_folder(recent_folder)
            
    def save_recent_folder(self, folder_path: str):
        """최근 폴더 저장"""
        self.current_folder = folder_path
        self.save_settings()
        
    def closeEvent(self, event):
        """앱 종료 시 이벤트"""
        self.save_current_if_needed()
        self.save_settings()
        event.accept()


def main():
    """메인 함수"""
    app = QApplication(sys.argv)
    app.setApplicationName("Keypoint Labeler")
    app.setApplicationVersion("1.0")
    
    # 스타일 설정
    app.setStyle('Fusion')
    
    window = KeypointLabeler()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == '__main__':
    import re
    main()
