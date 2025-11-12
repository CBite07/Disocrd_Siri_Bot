#!/usr/bin/env python3
"""
Siri Discord Bot 실행 스크립트
main.py를 실행하기 위한 간단한 래퍼 (환경 확인 + 실행)
"""

import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent  # DiscordSiri/src -> DiscordSiri

# 환경 변수 로드
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(ENV_PATH)

def check_requirements():
    """필수 조건 확인"""
    print("=" * 60)
    print("🔍 Siri Discord Bot - 환경 확인")
    print("=" * 60)
    
    # .env 파일 존재 확인
    if not ENV_PATH.exists():
        print(f"\n❌ .env 파일이 없습니다.")
        print(f"📍 필요한 위치: {ENV_PATH}")
        print("📝 .env.example을 참고하여 .env 파일을 생성하세요.\n")
        print("필수 환경 변수:")
        print("  - SIRI_BOT_TOKEN=your_discord_bot_token")
        return False
    
    # 필수 환경 변수 확인
    import os
    bot_token = os.getenv('SIRI_BOT_TOKEN') or os.getenv('BOT_TOKEN')
    if not bot_token:
        print(f"\n❌ SIRI_BOT_TOKEN이 .env 파일에 설정되지 않았습니다.")
        print(f"📍 파일 위치: {ENV_PATH}")
        return False
    
    # data 디렉토리 확인
    data_dir = SCRIPT_DIR / 'data'
    if not data_dir.exists():
        print(f"\n📁 data 디렉토리를 생성합니다: {data_dir}")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    # assets 디렉토리 확인 (TTS 음성 기능용)
    assets_dir = PROJECT_ROOT / 'assets'
    if not assets_dir.exists():
        print(f"📁 assets 디렉토리를 생성합니다: {assets_dir}")
        assets_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n✅ 환경 확인 완료!\n")
    return True

def main():
    """메인 실행 함수"""
    # 필수 조건 확인
    if not check_requirements():
        print("\n⚠️  환경 설정을 완료한 후 다시 실행해주세요.")
        sys.exit(1)
    
    # sys.path에 src 디렉토리 추가
    if str(SCRIPT_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPT_DIR))
    
    try:
        print("=" * 60)
        print("🚀 Siri Discord Bot 시작")
        print("=" * 60)
        print("\n💡 Ctrl+C를 눌러 안전하게 종료할 수 있습니다.\n")
        
        # main.py의 main() 함수 실행
        from main import main as bot_main
        asyncio.run(bot_main())
        
    except KeyboardInterrupt:
        print("\n\n⏹️  사용자가 종료했습니다.")
        print("✅ 봇이 안전하게 종료되었습니다.")
    except ImportError as e:
        print(f"\n❌ 모듈 import 오류: {e}")
        print("\n필요한 패키지를 설치하세요:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
