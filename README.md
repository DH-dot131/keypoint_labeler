# 키포인트 라벨러 (Keypoint Labeler)

의료 영상 및 일반 이미지에서 키포인트를 라벨링하기 위한 로컬 애플리케이션입니다.

## 주요 기능

- **다양한 파일 형식 지원**: DICOM(.dcm), JPG(.jpg/.jpeg), PNG(.png)
- **키포인트 편집**: 마우스 클릭으로 포인트 추가/이동, 키보드로 정밀 조정
- **순서 관리**: 드래그 앤 드롭으로 키포인트 순서 변경, 삽입/삭제/교환
- **DICOM 뷰어**: Window/Level 조정, 프리셋 지원, 인버트/회전/플립
- **자동 저장**: 이미지 전환 시 자동 저장, 백업 파일 생성
- **폴더 탐색**: 대량 이미지 처리, 자연 정렬 지원

## 설치 방법

### 1. Python 환경 설정

Python 3.8 이상이 필요합니다.

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate     # Windows
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 실행

```bash
python app.py
```

## 사용법

### 기본 조작

- **포인트 추가**: 이미지 영역 클릭
- **포인트 선택**: 기존 포인트 클릭
- **포인트 이동**: 선택된 포인트 드래그
- **포인트 삭제**: 포인트 선택 후 Delete 키
- **정밀 이동**: 포인트 선택 후 화살표 키 (Shift: 10px 단위)

### 마우스 모드

- **일반 모드**: 포인트 선택/추가
- **팬 모드**: Ctrl + 드래그
- **DICOM Window/Level**: Shift + 드래그 (DICOM 파일만)

### 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| Ctrl+O | 파일 열기 |
| Ctrl+Shift+O | 폴더 열기 |
| Ctrl+S | 저장 |
| Ctrl+Shift+S | 전체 저장 |
| Ctrl+Z | 실행 취소 |
| Ctrl+Y | 다시 실행 |
| Delete | 선택된 포인트 삭제 |
| Ctrl++ | 확대 |
| Ctrl+- | 축소 |
| Ctrl+0 | 창에 맞춤 |
| Ctrl+R | 90도 회전 |

### DICOM 뷰어 기능

- **Window/Level 조정**: 슬라이더 또는 마우스 드래그
- **프리셋**: Soft Tissue, Bone, Lung, General
- **인버트**: 이미지 반전
- **회전/플립**: 이미지 변환

## JSON 파일 형식

키포인트 데이터는 다음과 같은 JSON 형식으로 저장됩니다:

```json
{
  "coord": [
    [x1, y1],
    [x2, y2],
    ...
  ]
}
```

- 좌표는 정수 픽셀 단위
- 이미지 좌상단이 원점 (0, 0)
- 순서가 중요함 (인덱스 0부터 시작)

## 프로젝트 구조

```
keypoint_labeler/
├── app.py                 # 메인 애플리케이션
├── viewer/                # 뷰어 모듈
│   ├── __init__.py
│   ├── canvas.py          # 이미지 캔버스
│   ├── dicom_loader.py    # DICOM 파일 로더
│   ├── image_loader.py    # 일반 이미지 로더
│   ├── json_io.py         # JSON 입출력
│   └── tools.py           # 유틸리티 도구
├── assets/                # 리소스 파일
├── logs/                  # 로그 파일 (자동 생성)
├── settings.json          # 설정 파일 (자동 생성)
├── requirements.txt       # 의존성 목록
└── README.md             # 이 파일
```

## 빌드 방법

### PyInstaller를 사용한 단일 실행 파일 생성

```bash
# PyInstaller 설치
pip install pyinstaller

# Windows
pyinstaller --onefile --windowed --name keypoint_labeler app.py

# Linux/Mac
pyinstaller --onefile --name keypoint_labeler app.py
```

## 문제 해결

### 일반적인 문제

1. **DICOM 파일이 열리지 않음**
   - pydicom 패키지가 제대로 설치되었는지 확인
   - 파일이 손상되지 않았는지 확인

2. **이미지가 표시되지 않음**
   - PIL/Pillow 패키지 설치 확인
   - 파일 경로에 한글이 포함되어 있는지 확인

3. **메모리 부족 오류**
   - 대용량 이미지의 경우 메모리 사용량 확인
   - 이미지 크기 조정 고려

### 로그 확인

애플리케이션 실행 중 오류가 발생하면 `logs/app.log` 파일을 확인하세요.

## 개발 정보

- **Python 버전**: 3.8+
- **GUI 프레임워크**: PyQt5
- **이미지 처리**: PIL, NumPy
- **DICOM 처리**: pydicom
- **라이선스**: MIT

## 기여하기

버그 리포트나 기능 요청은 이슈를 통해 제출해 주세요.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.
