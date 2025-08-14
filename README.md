# 키포인트 라벨러 (Keypoint Labeler)

의료 영상 및 일반 이미지에서 키포인트를 라벨링하기 위한 로컬 애플리케이션입니다.

## 주요 기능

- **다양한 파일 형식 지원**: DICOM(.dcm), JPG(.jpg/.jpeg), PNG(.png)
- **직관적인 키포인트 편집**: 마우스 클릭으로 포인트 추가, 드래그로 이동
- **키포인트 순서 관리**: 드래그 앤 드롭으로 순서 변경, 삭제/교환 기능
- **이미지 줌 및 패닝**: 정밀한 라벨링을 위한 확대/축소 및 이미지 이동
- **자동 저장**: 이미지 전환 시 자동 저장, 원본 파일 보존
- **폴더 탐색**: 대량 이미지 처리, 자연 정렬 지원
- **단일 실행 파일**: PyInstaller로 빌드된 독립 실행 파일

## 설치 및 실행

### Python 환경 설정

Python 3.8 이상이 필요합니다.

```bash
# 가상환경 생성 (권장)
python -m venv keypoint_env

# 가상환경 활성화
# Windows
keypoint_env\Scripts\activate
# Linux/Mac
source keypoint_env/bin/activate
```

### 의존성 설치

```bash
pip install -r requirements.txt
```

### 실행

```bash
python app.py
```

### 실행 파일 빌드 (선택사항)

독립 실행 파일을 만들고 싶다면 아래 빌드 방법을 참고하세요:

#### Windows

```bash
# 가상환경에서 빌드 (권장)
python -m venv keypoint_env
keypoint_env\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
.\build.bat
```

#### Linux/Mac

```bash
# 가상환경에서 빌드 (권장)
python -m venv keypoint_env
source keypoint_env/bin/activate
pip install -r requirements.txt
pip install pyinstaller
./build.sh
```

#### 빌드 최적화

파일 크기를 줄이려면 가상환경을 사용하여 필요한 라이브러리만 포함하세요:

```bash
# 가상환경 사용 (파일 크기 최적화)
python -m venv keypoint_env
keypoint_env\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --exclude-module torch --exclude-module tensorflow --exclude-module sklearn --exclude-module matplotlib --exclude-module pandas --name keypoint_labeler app.py
```

## 사용법

### 기본 조작

- **포인트 추가**: 이미지 영역 클릭
- **포인트 선택**: 기존 포인트 클릭
- **포인트 이동**: 선택된 포인트 드래그
- **포인트 삭제**: 포인트 선택 후 "삭제" 버튼 또는 Delete 키
- **최근 점 삭제**: 마우스 우클릭 (마지막으로 추가된 점만)
- **실행 취소**: Ctrl + Z (최대 50단계)
- **정밀 이동**: 포인트 선택 후 화살표 키 (Shift: 10px 단위)

### 이미지 줌 및 패닝

- **줌 인/아웃**: Ctrl + 휠 또는 Ctrl + '+'/'-'
- **줌 리셋**: Ctrl + '0' 또는 사이드 패널의 "100%" 버튼
- **이미지 이동**: Alt + 마우스 드래그 또는 Space + 방향키
- **정밀 라벨링**: 높은 줌 레벨에서 더 정확한 키포인트 배치 가능

### 키포인트 관리

- **순서 변경**: 사이드 패널에서 드래그 앤 드롭
- **교환**: 두 개 포인트 선택 후 "교환" 버튼
- **전체 삭제**: "전체 삭제" 버튼
- **라벨 표시**: "라벨 표시" 체크박스로 번호 표시/숨김

### 키보드 단축키

| 단축키 | 기능 |
|--------|------|
| ←→↑↓ | 선택된 포인트 이동 (1px 단위) |
| Shift+←→↑↓ | 선택된 포인트 이동 (10px 단위) |
| Delete | 선택된 포인트 삭제 |
| **Ctrl + '+'** | 이미지 확대 |
| **Ctrl + '-'** | 이미지 축소 |
| **Ctrl + '0'** | 줌 리셋 (100%) |
| **Ctrl + 휠** | 마우스 포인터 중심 줌 |
| **Alt + 드래그** | 이미지 이동 (패닝) |
| **Space + 방향키** | 키보드로 이미지 이동 |
| **Space + Shift + 방향키** | 빠른 이미지 이동 |
| **Ctrl + Z** | 실행 취소 |
| **우클릭** | 최근 추가된 점 삭제 |

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
- UI에서는 1부터 시작하는 번호로 표시
- 원본 이미지와 동일한 폴더에 `.json` 확장자로 저장

## 프로젝트 구조

```
keypoint_labeler/
├── app.py                 # 메인 애플리케이션
├── viewer/                # 뷰어 모듈
│   ├── __init__.py
│   ├── canvas.py          # 이미지 캔버스 및 상호작용
│   ├── dicom_loader.py    # DICOM 파일 로더 (전처리 포함)
│   ├── image_loader.py    # 일반 이미지 로더
│   ├── json_io.py         # JSON 입출력
│   └── tools.py           # 유틸리티 도구
├── logs/                  # 로그 파일 (자동 생성)
├── settings.json          # 설정 파일 (자동 생성)
├── requirements.txt       # 의존성 목록
├── build.bat             # Windows 빌드 스크립트
├── build.sh              # Linux/Mac 빌드 스크립트
└── README.md             # 이 파일
```

## 빌드 방법

### Windows

```bash
# 가상환경에서 빌드 (권장)
python -m venv keypoint_env
keypoint_env\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
.\build.bat
```

### Linux/Mac

```bash
# 가상환경에서 빌드 (권장)
python -m venv keypoint_env
source keypoint_env/bin/activate
pip install -r requirements.txt
pip install pyinstaller
./build.sh
```

### 빌드 최적화

파일 크기를 줄이려면 가상환경을 사용하여 필요한 라이브러리만 포함하세요:

```bash
# 가상환경 사용 (파일 크기 최적화)
python -m venv keypoint_env
keypoint_env\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller
pyinstaller --onefile --windowed --exclude-module torch --exclude-module tensorflow --exclude-module sklearn --exclude-module matplotlib --exclude-module pandas --name keypoint_labeler app.py
```

## 문제 해결

### 일반적인 문제

1. **DICOM 파일이 검은 화면으로 표시됨**
   - 파일이 손상되지 않았는지 확인
   - 다른 DICOM 뷰어로 파일 확인

2. **이미지가 표시되지 않음**
   - 파일 경로에 한글이 포함되어 있는지 확인
   - 지원되는 파일 형식인지 확인 (.dcm, .jpg, .jpeg, .png)

3. **키포인트가 저장되지 않음**
   - 파일 쓰기 권한 확인
   - 디스크 공간 확인


### 로그 확인

애플리케이션 실행 중 오류가 발생하면 `logs/app.log` 파일을 확인하세요.

## 개발 정보

- **Python 버전**: 3.8+
- **GUI 프레임워크**: PyQt5
- **이미지 처리**: PIL, NumPy, OpenCV
- **DICOM 처리**: pydicom
- **빌드 도구**: PyInstaller
- **라이선스**: MIT

## 주요 변경사항

### v1.1 (현재)
- ✅ **이미지 줌 기능**: 마우스 휠 및 키보드 단축키로 확대/축소
- ✅ **이미지 패닝 기능**: Alt+드래그 및 Space+방향키로 이미지 이동
- ✅ **정밀 라벨링**: 높은 줌 레벨에서 더 정확한 키포인트 배치
- ✅ **줌 레벨 표시**: 사이드 패널에 실시간 줌 퍼센트 표시

### v1.0
- ✅ DICOM 자동 전처리 (CLAHE 적용)
- ✅ 직관적인 마우스 인터페이스
- ✅ 1-based 키포인트 인덱싱
- ✅ 드래그 앤 드롭 순서 변경
- ✅ 자동 저장 기능

## 기여하기

버그 리포트나 기능 요청은 이슈를 통해 제출해 주세요.

자세한 기여 가이드는 [CONTRIBUTING.md](CONTRIBUTING.md)를 참고하세요.

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## 변경 이력

프로젝트의 변경 이력은 [CHANGELOG.md](CHANGELOG.md)에서 확인할 수 있습니다.
