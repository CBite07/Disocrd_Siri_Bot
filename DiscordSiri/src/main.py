"""
Siri Discord Bot - 메인 실행 파일
디스코드 서버 커뮤니티 활성화를 위한 다기능 봇

핵심 기능:
- 출석 체크 및 레벨링 시스템
- 리더보드
- 공지 및 규칙 시스템
- 관리자 기능
"""

import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

from utils.database import DatabaseManager
from utils.config import Config

# 프로젝트 루트 경로 설정 (uv 구조)
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# 환경 변수 로드
load_dotenv(ENV_PATH)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('siri_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('siri_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

class SiriBot(commands.Bot):
    """
    Siri Discord Bot 메인 클래스
    소프트 코딩 원칙에 따른 모듈식 설계
    """
    
    def __init__(self):
        # 봇 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.voice_states = True  # 음성 상태 변경 감지
        
        super().__init__(
            command_prefix=Config.get_command_prefix(),
            intents=intents,
            help_command=None  # 사용자 정의 도움말 사용
        )
        
        # 데이터베이스 매니저 초기화
        self.db = None
        
    async def setup_hook(self):
        """봇 시작 시 초기 설정"""
        logger.info("Siri Bot 초기화 중...")
        
        # 데이터베이스 초기화
        self.db = DatabaseManager(Config.get_database_path())
        await self.db.init_database()
        
        # Cogs 로드
        await self.load_cogs()
        
        logger.info("Siri Bot 초기화 완료!")
    
    async def load_cogs(self):
        """모든 Cogs 로드"""
        cog_files = [
            'cogs.attendance',
            'cogs.leaderboard', 
            'cogs.admin',
            'cogs.announcement',
            'cogs.debug',
            'cogs.siri_music',  # Siri 음악 인터페이스 (GPT 봇에게 전달)
            'cogs.voice'   # Edge-TTS 음성 기능
        ]
        
        for cog in cog_files:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog {cog} 로드 완료")
            except Exception as e:
                logger.error(f"Cog {cog} 로드 실패: {e}")
    
    async def on_ready(self):
        """봇이 준비되었을 때"""
        logger.info(f'{self.user}가 {len(self.guilds)}개 서버에 연결되었습니다!')
        
        # 슬래시 명령어 동기화
        try:
            synced = await self.tree.sync()
            logger.info(f"슬래시 명령어 {len(synced)}개 동기화 완료")
        except Exception as e:
            logger.error(f"명령어 동기화 실패: {e}")
        
        # 봇 상태 설정
        activity = discord.Game(name="출석체크 /ㅊㅊ")
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """명령어 오류 처리"""
        if isinstance(error, commands.CommandNotFound):
            return  # 명령어를 찾을 수 없는 경우 무시
        
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 이 명령어를 사용할 권한이 없습니다.")
            
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ 쿨다운 중입니다. {error.retry_after:.1f}초 후에 다시 시도하세요.")
            
        else:
            logger.error(f"명령어 오류: {error}")
            await ctx.send("❌ 명령어 처리 중 오류가 발생했습니다.")
    
    @commands.command(name='sync')
    async def sync_commands(self, ctx):
        """슬래시 명령어 수동 동기화 (봇 소유자 전용)"""
        if ctx.author.id != 442959929900326913:  # 봇 소유자 ID로 변경하세요
            await ctx.send("❌ 이 명령어는 봇 소유자만 사용할 수 있습니다.")
            return
        
        try:
            synced = await self.tree.sync()
            await ctx.send(f"✅ 슬래시 명령어 {len(synced)}개 동기화 완료!")
            logger.info(f"수동 동기화: {len(synced)}개 명령어")
        except Exception as e:
            await ctx.send(f"❌ 동기화 실패: {e}")
            logger.error(f"수동 동기화 실패: {e}")

    async def close(self):
        """봇 종료 시 정리 작업"""
        logger.info("봇 종료 시작 - 정리 작업 수행 중...")
        
        # 음성 시스템 정리 (VoiceCog)
        voice_cog = self.get_cog('VoiceCog')
        if voice_cog:
            try:
                logger.info("음성 시스템 정리 시작...")
                # 모든 길드의 음성 연결 확인 및 정리
                for guild in self.guilds:
                    if guild.voice_client:
                        try:
                            # 현재 재생 중이면 중지
                            if guild.voice_client.is_playing():
                                guild.voice_client.stop()
                                logger.info(f"길드 {guild.name}: 재생 중인 오디오 중지")
                                # 재생 중지 후 짧은 대기
                                await asyncio.sleep(0.3)
                            
                            # 작별 인사 TTS (빠르게)
                            try:
                                tts_text = "잠시 후 돌아올게요"
                                audio_file = await voice_cog.generate_tts(tts_text)
                                audio_source = discord.FFmpegPCMAudio(audio_file)
                                
                                # 재생 완료를 기다리는 이벤트
                                done = asyncio.Event()
                                
                                def cleanup_after(error):
                                    try:
                                        if os.path.exists(audio_file):
                                            os.remove(audio_file)
                                    except:
                                        pass
                                    done.set()
                                
                                guild.voice_client.play(audio_source, after=cleanup_after)
                                
                                # 최대 3초 대기 (작별 인사 재생)
                                try:
                                    await asyncio.wait_for(done.wait(), timeout=3.0)
                                except asyncio.TimeoutError:
                                    guild.voice_client.stop()
                                
                            except Exception as e:
                                logger.warning(f"작별 인사 TTS 실패: {e}")
                            
                            # 음성 채널 연결 종료
                            await guild.voice_client.disconnect()
                            logger.info(f"길드 {guild.name}: 음성 채널 연결 종료")
                            
                        except Exception as e:
                            logger.error(f"길드 {guild.name} 음성 정리 중 오류: {e}")
                
                # VoiceCog의 임시 파일 정리
                try:
                    for file in voice_cog.temp_dir.glob("tts_*.mp3"):
                        file.unlink()
                    logger.info("임시 TTS 파일 정리 완료")
                except Exception as e:
                    logger.error(f"임시 파일 정리 중 오류: {e}")
                
                logger.info("음성 시스템 정리 완료")
            except Exception as e:
                logger.error(f"음성 시스템 정리 중 오류: {e}")
        
        # 음악 시스템 정리 (MusicCog)
        music_cog = self.get_cog('MusicCog')
        if music_cog:
            try:
                logger.info("음악 시스템 정리 시작...")
                await music_cog.cleanup_all_players()
                logger.info("음악 시스템 정리 완료")
            except Exception as e:
                logger.error(f"음악 시스템 정리 중 오류: {e}")
        
        # 데이터베이스 연결 종료
        if self.db:
            try:
                await self.db.close()
                logger.info("데이터베이스 연결 종료")
            except Exception as e:
                logger.error(f"데이터베이스 종료 중 오류: {e}")
        
        # 부모 클래스의 close 호출
        await super().close()
        logger.info("봇 정리 작업 완료")

async def main():
    """메인 실행 함수"""
    bot = SiriBot()
    
    try:
        logger.info("봇을 시작합니다...")
        
        # 시그널 핸들러 설정 (Unix 시스템에서)
        import signal
        import sys
        
        def signal_handler(signum, frame):
            logger.info(f"시그널 {signum} 수신 - 봇 종료 시작...")
            # 이벤트 루프에서 안전하게 종료
            asyncio.create_task(bot.close())
        
        if sys.platform != 'win32':  # Windows가 아닌 경우
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
        
        await bot.start(Config.get_bot_token())
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 봇이 종료됩니다...")
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}")
    finally:
        if not bot.is_closed():
            logger.info("봇 연결을 정리 중...")
            await bot.close()
        logger.info("봇이 안전하게 종료되었습니다.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 사용자에 의해 종료되었습니다.")
