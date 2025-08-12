#!/bin/bash

echo "키포인트 라벨러 빌드 시작..."

# PyInstaller 설치 확인
if ! pip show pyinstaller > /dev/null 2>&1; then
    echo "PyInstaller 설치 중..."
    pip install pyinstaller
fi

# 빌드 실행
echo "단일 실행 파일 생성 중..."
pyinstaller --onefile --name keypoint_labeler --distpath ./dist --workpath ./build --specpath ./build app.py

if [ $? -eq 0 ]; then
    echo "빌드 완료!"
    echo "실행 파일 위치: dist/keypoint_labeler"
    chmod +x dist/keypoint_labeler
else
    echo "빌드 실패!"
    exit 1
fi
