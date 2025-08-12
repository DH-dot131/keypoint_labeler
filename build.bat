@echo off
echo 키포인트 라벨러 빌드 시작...

REM PyInstaller 설치 확인
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo PyInstaller 설치 중...
    pip install pyinstaller
)

REM 빌드 실행
echo 단일 실행 파일 생성 중...
pyinstaller --onefile --windowed --name keypoint_labeler --distpath ./dist --workpath ./build --specpath ./build app.py

if errorlevel 1 (
    echo 빌드 실패!
    pause
    exit /b 1
)

echo 빌드 완료!
echo 실행 파일 위치: dist/keypoint_labeler.exe
pause
