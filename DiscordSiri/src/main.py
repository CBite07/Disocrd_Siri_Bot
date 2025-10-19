"""
Siri Discord Bot - 통합 실행 파일
디스코드 서버 커뮤니티 활성화를 위한 다기능 봇 + 음악 재생 봇

핵심 기능:
- 출석 체크 및 레벨링 시스템
- 리더보드
- 공지 및 규칙 시스템
- 관리자 기능
- 음악 재생 (GPT 봇)
"""

import asyncio
import logging
import os
from pathlib import Path
from threading import Thread

import discord
from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask, request, jsonify

from utils.database import DatabaseManager
from utils.config import Config

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

# 환경 변수 로드
load_dotenv(ENV_PATH)

# 로깅 설정 - 통합된 단일 로그 파일 사용
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / 'discord_siri_bot.log'),  # 통합 로그 파일
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def preflight_check() -> bool:
    """실행 전 환경 및 디렉토리 점검.
    - .env 파일 존재 여부
    - 필수 환경변수(BOT_TOKEN)
    - 필요한 디렉토리 생성(src/data, assets)
    - 선택 환경변수(GPT_BOT_TOKEN) 안내
    """
    ok = True

    # .env 파일 확인
    if not ENV_PATH.exists():
        logging.error(f".env 파일을 찾을 수 없습니다: {ENV_PATH}")
        logging.error(".env.example을 참고해 .env 파일을 생성해 주세요.")
        return False

    # 필수 토큰 확인
    siri_bot_token = Config.get_bot_token()  # SIRI_BOT_TOKEN 확인
    if not siri_bot_token:
        logging.error("SIRI_BOT_TOKEN 환경 변수가 설정되어 있지 않습니다 (.env 파일 확인).")
        ok = False

    # 선택 토큰(GPT_BOT_TOKEN) 안내
    gpt_bot_token = Config.get_gpt_bot_token()
    if not gpt_bot_token:
        logging.warning("GPT_BOT_TOKEN이 설정되지 않았습니다. 음악 기능이 비활성화됩니다.")

    # 디렉토리 확인 및 생성
    try:
        data_dir = Path(__file__).parent / "data"  # DiscordSiri/src/data
        if not data_dir.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"data 디렉토리를 생성했습니다: {data_dir}")
    except Exception as e:
        logging.error(f"data 디렉토리 생성 중 오류: {e}")
        ok = False

    try:
        assets_dir = PROJECT_ROOT / "assets"
        if not assets_dir.exists():
            assets_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"assets 디렉토리를 생성했습니다: {assets_dir}")
    except Exception as e:
        logging.error(f"assets 디렉토리 생성 중 오류: {e}")
        ok = False

    return ok

# Flask 앱 생성 (GPT 봇 API 서버)
app = Flask(__name__)

# 전역 봇 인스턴스
siri_bot = None
gpt_bot = None


class SiriBot(commands.Bot):
    """
    Siri Discord Bot 메인 클래스
    출석, 레벨링, 관리 기능 담당
    """
    
    def __init__(self):
        # 봇 인텐트 설정
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix=Config.get_command_prefix(),
            intents=intents,
            help_command=None
        )
        
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
            'cogs.admin',  # debug 기능 포함
            'cogs.announcement',
            'cogs.voice'   # Edge-TTS 음성 기능
        ]
        
        for cog in cog_files:
            try:
                await self.load_extension(cog)
                logger.info(f"Siri Cog {cog} 로드 완료")
            except Exception as e:
                logger.error(f"Siri Cog {cog} 로드 실패: {e}")
    
    async def on_ready(self):
        """봇이 준비되었을 때"""
        logger.info(f'[Siri] {self.user}가 {len(self.guilds)}개 서버에 연결되었습니다!')
        
        # 슬래시 명령어 동기화
        try:
            synced = await self.tree.sync()
            logger.info(f"[Siri] 슬래시 명령어 {len(synced)}개 동기화 완료")
        except Exception as e:
            logger.error(f"[Siri] 명령어 동기화 실패: {e}")
        
        # 봇 상태 설정
        activity = discord.Game(name="출석체크 /ㅊㅊ")
        await self.change_presence(activity=activity)
    
    async def on_command_error(self, ctx, error):
        """명령어 오류 처리"""
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ 이 명령어를 사용할 권한이 없습니다.")
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f"⏰ 쿨다운 중입니다. {error.retry_after:.1f}초 후에 다시 시도하세요.")
        else:
            logger.error(f"[Siri] 명령어 오류: {error}")
            await ctx.send("❌ 명령어 처리 중 오류가 발생했습니다.")
    
    @commands.command(name='sync')
    async def sync_commands(self, ctx):
        """슬래시 명령어 수동 동기화 (봇 소유자 전용)"""
        if ctx.author.id != 442959929900326913:
            await ctx.send("❌ 이 명령어는 봇 소유자만 사용할 수 있습니다.")
            return
        
        try:
            synced = await self.tree.sync()
            await ctx.send(f"✅ 슬래시 명령어 {len(synced)}개 동기화 완료!")
            logger.info(f"[Siri] 수동 동기화: {len(synced)}개 명령어")
        except Exception as e:
            await ctx.send(f"❌ 동기화 실패: {e}")
            logger.error(f"[Siri] 수동 동기화 실패: {e}")

    async def close(self):
        """봇 종료 시 정리 작업"""
        logger.info("[Siri] 봇 종료 시작 - 정리 작업 수행 중...")
        
        # 음성 시스템 정리
        voice_cog = self.get_cog('VoiceCog')
        if voice_cog:
            try:
                logger.info("[Siri] 음성 시스템 정리 시작...")
                for guild in self.guilds:
                    if guild.voice_client:
                        try:
                            if guild.voice_client.is_playing():
                                guild.voice_client.stop()
                                await asyncio.sleep(0.3)
                            
                            try:
                                tts_text = "잠시 후 돌아올게요"
                                audio_file = await voice_cog.generate_tts(tts_text)
                                audio_source = discord.FFmpegPCMAudio(audio_file)
                                
                                done = asyncio.Event()
                                
                                def cleanup_after(error):
                                    try:
                                        if os.path.exists(audio_file):
                                            os.remove(audio_file)
                                    except:
                                        pass
                                    done.set()
                                
                                guild.voice_client.play(audio_source, after=cleanup_after)
                                
                                try:
                                    await asyncio.wait_for(done.wait(), timeout=3.0)
                                except asyncio.TimeoutError:
                                    guild.voice_client.stop()
                                
                            except Exception as e:
                                logger.warning(f"[Siri] 작별 인사 TTS 실패: {e}")
                            
                            await guild.voice_client.disconnect()
                            logger.info(f"[Siri] 길드 {guild.name}: 음성 채널 연결 종료")
                            
                        except Exception as e:
                            logger.error(f"[Siri] 길드 {guild.name} 음성 정리 중 오류: {e}")
                
                try:
                    for file in voice_cog.temp_dir.glob("tts_*.mp3"):
                        file.unlink()
                    logger.info("[Siri] 임시 TTS 파일 정리 완료")
                except Exception as e:
                    logger.error(f"[Siri] 임시 파일 정리 중 오류: {e}")
                
                logger.info("[Siri] 음성 시스템 정리 완료")
            except Exception as e:
                logger.error(f"[Siri] 음성 시스템 정리 중 오류: {e}")
        
        # 데이터베이스 연결 종료
        if self.db:
            try:
                await self.db.close()
                logger.info("[Siri] 데이터베이스 연결 종료")
            except Exception as e:
                logger.error(f"[Siri] 데이터베이스 종료 중 오류: {e}")
        
        await super().close()
        logger.info("[Siri] 봇 정리 작업 완료")


class GPTBot(commands.Bot):
    """GPT 음악 재생 전용 봇"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.voice_states = True
        intents.members = True
        
        super().__init__(
            command_prefix=Config.get_command_prefix(),
            intents=intents,
            help_command=None
        )
        
        self.db = DatabaseManager(Config.get_database_path())
        
    async def setup_hook(self):
        """봇 시작 시 실행되는 설정"""
        logger.info("[GPT] 음악 봇 초기화 중...")
        
        # 음악 Cog 로드
        try:
            await self.load_extension("cogs.music")
            logger.info("[GPT] 음악 시스템 로드 완료")
        except Exception as e:
            logger.error(f"[GPT] 음악 시스템 로드 실패: {e}")
        
        # 슬래시 명령어 동기화
        try:
            synced = await self.tree.sync()
            logger.info(f"[GPT] 슬래시 명령어 {len(synced)}개 동기화 완료")
        except Exception as e:
            logger.error(f"[GPT] 명령어 동기화 실패: {e}")
    
    async def on_ready(self):
        """봇 준비 완료 시"""
        logger.info(f'[GPT] {self.user.name} 음악 봇이 준비되었습니다!')
        logger.info(f'[GPT] 연결된 서버: {len(self.guilds)}개')
        
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name="Siri의 명령"
            )
        )
    
    async def on_command_error(self, ctx, error):
        """명령어 오류 처리"""
        if isinstance(error, commands.CommandNotFound):
            return
        logger.error(f"[GPT] 명령어 오류: {error}")
    
    async def close(self):
        """봇 종료 시 정리"""
        logger.info("[GPT] 음악 봇 종료 시작...")
        
        music_cog = self.get_cog('MusicCog')
        if music_cog:
            try:
                await music_cog.cleanup_all_players()
                logger.info("[GPT] 음악 시스템 정리 완료")
            except Exception as e:
                logger.error(f"[GPT] 음악 시스템 정리 중 오류: {e}")
        
        await super().close()
        logger.info("[GPT] 음악 봇 정리 완료")


# Flask API 엔드포인트
@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        "status": "healthy",
        "gpt_bot_ready": gpt_bot is not None and gpt_bot.is_ready()
    })


@app.route('/play', methods=['POST'])
def play_music():
    """음악 재생 API"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"status": "error", "message": "데이터가 없습니다"}), 400
        
        query = data.get('query')
        guild_id = data.get('guild_id')
        channel_id = data.get('channel_id')
        user = data.get('user', 'Unknown')
        
        if not query or not guild_id or not channel_id:
            return jsonify({
                "status": "error",
                "message": "필수 파라미터 누락 (query, guild_id, channel_id)"
            }), 400
        
        logger.info(f"[API] 재생 요청: {query} (사용자: {user}, 길드: {guild_id})")
        
        result = asyncio.run_coroutine_threadsafe(
            handle_play_command(guild_id, channel_id, query, user),
            gpt_bot.loop
        ).result(timeout=30)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[API] 재생 API 오류: {e}")
        return jsonify({
            "status": "error",
            "message": f"서버 오류: {str(e)}"
        }), 500


@app.route('/stop', methods=['POST'])
def stop_music():
    """음악 정지 API"""
    try:
        data = request.get_json()
        guild_id = data.get('guild_id')
        
        if not guild_id:
            return jsonify({"status": "error", "message": "guild_id 필요"}), 400
        
        result = asyncio.run_coroutine_threadsafe(
            handle_stop_command(guild_id),
            gpt_bot.loop
        ).result(timeout=10)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"[API] 정지 API 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


async def handle_play_command(guild_id: int, channel_id: int, query: str, user: str):
    """음악 재생 명령 처리"""
    try:
        guild = gpt_bot.get_guild(guild_id)
        if not guild:
            return {"status": "error", "message": "서버를 찾을 수 없습니다"}
        
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.VoiceChannel):
            return {"status": "error", "message": "음성 채널을 찾을 수 없습니다"}
        
        music_cog = gpt_bot.get_cog("MusicCog")
        if not music_cog:
            return {"status": "error", "message": "음악 시스템이 로드되지 않았습니다"}
        
        player = music_cog.get_player(guild_id)
        
        if player.is_playing:
            return {
                "status": "error",
                "message": f"이미 재생 중입니다: {player.current_track.title if player.current_track else '알 수 없음'}"
            }
        
        if not await player.connect(channel):
            return {"status": "error", "message": "음성 채널 연결 실패"}
        
        track_info, error_message = await player.ytdl_source.extract_info(query)
        if not track_info:
            await player.disconnect()
            return {"status": "error", "message": error_message or "음악을 찾을 수 없습니다"}
        
        success, play_error = await player.play_track(track_info)
        if success:
            logger.info(f"[음악] 재생 시작: {track_info.title}")
            return {
                "status": "playing",
                "song": track_info.title,
                "uploader": track_info.uploader,
                "thumbnail": track_info.thumbnail
            }
        else:
            return {"status": "error", "message": play_error or "재생 실패"}
        
    except Exception as e:
        logger.error(f"[음악] 재생 처리 중 오류: {e}")
        return {"status": "error", "message": f"처리 중 오류: {str(e)}"}


async def handle_stop_command(guild_id: int):
    """음악 정지 명령 처리"""
    try:
        music_cog = gpt_bot.get_cog("MusicCog")
        if not music_cog:
            return {"status": "error", "message": "음악 시스템이 로드되지 않았습니다"}
        
        player = music_cog.get_player(guild_id)
        await player.disconnect()
        
        return {"status": "stopped", "message": "재생이 중지되었습니다"}
        
    except Exception as e:
        logger.error(f"[음악] 정지 처리 중 오류: {e}")
        return {"status": "error", "message": str(e)}


def run_flask():
    """Flask 서버 실행 (별도 스레드)"""
    host = Config.get_gpt_api_host()
    port = Config.get_gpt_api_port()
    logger.info(f"[Flask] API 서버 시작: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


async def run_siri_bot():
    """Siri 봇 실행"""
    global siri_bot
    siri_bot = SiriBot()
    
    try:
        token = Config.get_bot_token()
        if not token:
            logger.error("[Siri] BOT_TOKEN이 설정되지 않았습니다!")
            return
        
        await siri_bot.start(token)
    except Exception as e:
        logger.error(f"[Siri] 봇 실행 오류: {e}")
    finally:
        if not siri_bot.is_closed():
            await siri_bot.close()


async def run_gpt_bot():
    """GPT 음악 봇 실행"""
    global gpt_bot
    
    token = Config.get_gpt_bot_token()
    if not token:
        logger.warning("[GPT] GPT_BOT_TOKEN이 설정되지 않았습니다. 음악 기능이 비활성화됩니다.")
        return
    
    gpt_bot = GPTBot()
    
    try:
        await gpt_bot.start(token)
    except Exception as e:
        logger.error(f"[GPT] 봇 실행 오류: {e}")
    finally:
        if not gpt_bot.is_closed():
            await gpt_bot.close()


async def main():
    """메인 실행 함수 - 두 봇을 동시에 실행"""
    logger.info("=" * 50)
    logger.info("Siri Discord Bot 통합 시스템 시작")
    logger.info("=" * 50)

    # 환경 및 디렉토리 사전 점검
    if not preflight_check():
        logger.error("사전 점검 실패로 실행을 중단합니다.")
        return
    
    # Flask API 서버 시작 (GPT 봇이 있을 경우에만)
    if Config.get_gpt_bot_token():
        flask_thread = Thread(target=run_flask, daemon=True)
        flask_thread.start()
    
    # 시그널 핸들러 설정
    import signal
    import sys
    
    async def shutdown():
        """안전한 종료"""
        logger.info("시스템 종료 시작...")
        tasks = []
        
        if siri_bot and not siri_bot.is_closed():
            tasks.append(siri_bot.close())
        
        if gpt_bot and not gpt_bot.is_closed():
            tasks.append(gpt_bot.close())
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info("시스템 종료 완료")
    
    def signal_handler(signum, frame):
        logger.info(f"시그널 {signum} 수신 - 종료 시작...")
        asyncio.create_task(shutdown())
    
    if sys.platform != 'win32':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    # 두 봇을 동시에 실행
    try:
        await asyncio.gather(
            run_siri_bot(),
            run_gpt_bot(),
            return_exceptions=True
        )
    except KeyboardInterrupt:
        logger.info("사용자에 의해 종료됩니다...")
        await shutdown()
    except Exception as e:
        logger.error(f"시스템 실행 중 오류: {e}")
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n프로그램이 종료되었습니다.")
