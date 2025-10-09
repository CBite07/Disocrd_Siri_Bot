#!/usr/bin/env python3
"""
Siri Discord Bot 실행 스크립트
봇을 안전하게 실행하기 위한 래퍼 스크립트
"""

import sys
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

def check_requirements():
    """필수 조건 확인"""
    # .env 파일 존재 확인
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print("❌ .env 파일이 없습니다.")
        print("📝 .env.example을 참고하여 .env 파일을 생성하세요.")
        return False
    
    # data 디렉토리 확인
    data_dir = SCRIPT_DIR / 'data'
    if not data_dir.exists():
        print("📁 data 디렉토리를 생성합니다...")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    return True

def main():
    """메인 실행 함수"""
    print("🤖 Siri Discord Bot 시작 중...")
    
    # 필수 조건 확인
    if not check_requirements():
        sys.exit(1)
    
    try:
        # 봇 실행
        main_path = SCRIPT_DIR / "main.py"
        subprocess.run([sys.executable, str(main_path)], check=True)
    except KeyboardInterrupt:
        print("\n⏹️ 봇이 안전하게 종료되었습니다.")
    except subprocess.CalledProcessError as e:
        print(f"❌ 봇 실행 중 오류 발생: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
