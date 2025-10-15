"""
GPT Discord Bot - 음악 재생 전용 봇
Siri 봇으로부터 명령을 받아 음악을 재생하는 실행 봇

작성일: 2025년 1월 15일
역할: Siri 봇의 명령을 받아 실제 음악 재생 수행
"""

import asyncio
import logging
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

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('gpt_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask 앱 생성 (API 서버)
app = Flask(__name__)

# 전역 봇 인스턴스
gpt_bot = None


class GPTBot(commands.Bot):
    """GPT 음악 재생 봇"""
    
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
        logger.info("GPT 봇 초기화 중...")
        
        # Cogs 로드
        try:
            await self.load_extension("cogs.music")
            logger.info("음악 시스템 로드 완료")
        except Exception as e:
            logger.error(f"음악 시스템 로드 실패: {e}")
        
        # 슬래시 명령어 동기화
        try:
            synced = await self.tree.sync()
            logger.info(f"슬래시 명령어 {len(synced)}개 동기화 완료")
        except Exception as e:
            logger.error(f"명령어 동기화 실패: {e}")
    
    async def on_ready(self):
        """봇 준비 완료 시"""
        logger.info(f'{self.user.name} GPT 봇이 준비되었습니다!')
        logger.info(f'연결된 서버: {len(self.guilds)}개')
        
        # 봇 상태 설정
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
        logger.error(f"명령어 오류: {error}")


# Flask API 엔드포인트
@app.route('/health', methods=['GET'])
def health_check():
    """헬스 체크"""
    return jsonify({
        "status": "healthy",
        "bot_ready": gpt_bot is not None and gpt_bot.is_ready()
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
        
        logger.info(f"재생 요청 받음: {query} (사용자: {user}, 길드: {guild_id})")
        
        # 비동기 작업을 동기적으로 실행
        result = asyncio.run_coroutine_threadsafe(
            handle_play_command(guild_id, channel_id, query, user),
            gpt_bot.loop
        ).result(timeout=30)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"재생 API 오류: {e}")
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
        logger.error(f"정지 API 오류: {e}")
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
        
        # MusicCog 가져오기
        music_cog = gpt_bot.get_cog("MusicCog")
        if not music_cog:
            return {"status": "error", "message": "음악 시스템이 로드되지 않았습니다"}
        
        player = music_cog.get_player(guild_id)
        
        # 이미 재생 중인지 확인
        if player.is_playing:
            return {
                "status": "error",
                "message": f"이미 재생 중입니다: {player.current_track.title if player.current_track else '알 수 없음'}"
            }
        
        # 음성 채널 연결
        if not await player.connect(channel):
            return {"status": "error", "message": "음성 채널 연결 실패"}
        
        # 음악 정보 추출
        track_info, error_message = await player.ytdl_source.extract_info(query)
        if not track_info:
            await player.disconnect()
            return {"status": "error", "message": error_message or "음악을 찾을 수 없습니다"}
        
        # 음악 재생
        success, play_error = await player.play_track(track_info)
        if success:
            logger.info(f"재생 시작: {track_info.title}")
            return {
                "status": "playing",
                "song": track_info.title,
                "uploader": track_info.uploader,
                "thumbnail": track_info.thumbnail
            }
        else:
            return {"status": "error", "message": play_error or "재생 실패"}
        
    except Exception as e:
        logger.error(f"재생 처리 중 오류: {e}")
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
        logger.error(f"정지 처리 중 오류: {e}")
        return {"status": "error", "message": str(e)}


def run_flask():
    """Flask 서버 실행 (별도 스레드)"""
    host = Config.get_gpt_api_host()
    port = Config.get_gpt_api_port()
    logger.info(f"Flask API 서버 시작: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


async def main():
    """메인 실행 함수"""
    global gpt_bot
    
    # 토큰 확인
    token = Config.get_gpt_bot_token()
    if not token:
        logger.error("GPT_BOT_TOKEN이 설정되지 않았습니다!")
        logger.error(".env 파일에서 GPT_BOT_TOKEN을 설정해주세요.")
        return
    
    # 봇 인스턴스 생성
    gpt_bot = GPTBot()
    
    # Flask 서버를 별도 스레드에서 실행
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # 봇 시작
    try:
        logger.info("GPT 봇 시작 중...")
        await gpt_bot.start(token)
    except KeyboardInterrupt:
        logger.info("GPT 봇 종료 중...")
        await gpt_bot.close()
    except Exception as e:
        logger.error(f"GPT 봇 실행 오류: {e}")
        await gpt_bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("프로그램 종료")
