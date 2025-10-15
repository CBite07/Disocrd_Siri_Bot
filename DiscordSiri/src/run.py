#!/usr/bin/env python3
"""
Siri + GPT Discord Bot 통합 실행 스크립트
두 봇을 동시에 실행하기 위한 멀티프로세스 래퍼
"""

import sys
import asyncio
import signal
from pathlib import Path
from multiprocessing import Process
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent  # DiscordSiri/src -> DiscordSiri -> Disocrd_Siri_Bot

# 환경 변수 로드
load_dotenv(PROJECT_ROOT / ".env")

def check_requirements():
    """필수 조건 확인"""
    # .env 파일 존재 확인
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print("❌ .env 파일이 없습니다.")
        print(f"📍 찾는 위치: {env_path}")
        print("📝 .env.example을 참고하여 .env 파일을 생성하세요.")
        return False
    
    # data 디렉토리 확인
    data_dir = SCRIPT_DIR / 'data'
    if not data_dir.exists():
        print("📁 data 디렉토리를 생성합니다...")
        data_dir.mkdir(parents=True, exist_ok=True)
    
    return True

def run_siri_bot():
    """Siri 봇 실행 (별도 프로세스)"""
    try:
        print("🎤 Siri Bot 시작 중...")
        # main.py의 main() 함수를 직접 import하여 실행
        sys.path.insert(0, str(SCRIPT_DIR))
        from main import main as siri_main
        asyncio.run(siri_main())
    except KeyboardInterrupt:
        print("\n⏹️ Siri Bot 종료")
    except Exception as e:
        print(f"❌ Siri Bot 오류: {e}")
        raise

def run_gpt_bot():
    """GPT 봇 실행 (별도 프로세스)"""
    try:
        print("🤖 GPT Bot 시작 중...")
        # gpt_bot.py의 main() 함수를 직접 import하여 실행
        sys.path.insert(0, str(SCRIPT_DIR))
        from gpt_bot import main as gpt_main
        asyncio.run(gpt_main())
    except KeyboardInterrupt:
        print("\n⏹️ GPT Bot 종료")
    except Exception as e:
        print(f"❌ GPT Bot 오류: {e}")
        raise

def main():
    """메인 실행 함수 - 두 봇을 병렬 실행"""
    print("=" * 60)
    print("🚀 Siri + GPT Discord Bot 통합 런처")
    print("=" * 60)
    
    # 필수 조건 확인
    if not check_requirements():
        sys.exit(1)
    
    # 프로세스 생성
    siri_process = Process(target=run_siri_bot, name="SiriBot")
    gpt_process = Process(target=run_gpt_bot, name="GPTBot")
    
    try:
        # 두 봇 시작
        print("\n📡 Siri Bot 프로세스 시작...")
        siri_process.start()
        
        print("📡 GPT Bot 프로세스 시작...")
        gpt_process.start()
        
        print("\n✅ 두 봇이 실행 중입니다. Ctrl+C로 종료하세요.\n")
        print("-" * 60)
        
        # 프로세스가 종료될 때까지 대기
        siri_process.join()
        gpt_process.join()
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 종료 신호를 받았습니다. 봇들을 종료합니다...")
        
        # 안전하게 프로세스 종료
        if siri_process.is_alive():
            print("🛑 Siri Bot 종료 중...")
            siri_process.terminate()
            siri_process.join(timeout=5)
            if siri_process.is_alive():
                print("⚠️ Siri Bot 강제 종료...")
                siri_process.kill()
        
        if gpt_process.is_alive():
            print("🛑 GPT Bot 종료 중...")
            gpt_process.terminate()
            gpt_process.join(timeout=5)
            if gpt_process.is_alive():
                print("⚠️ GPT Bot 강제 종료...")
                gpt_process.kill()
        
        print("✅ 모든 봇이 안전하게 종료되었습니다.")
        
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류 발생: {e}")
        
        # 오류 발생 시 프로세스 정리
        if siri_process.is_alive():
            siri_process.terminate()
        if gpt_process.is_alive():
            gpt_process.terminate()
        
        sys.exit(1)

if __name__ == "__main__":
    main()
