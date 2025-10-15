"""
Siri Bot 초간단 음악 재생 시스템
핵심 기능만 포함: 재생, 일시정지/재생, 반복, 정지, 유휴 타임아웃

작성일: 2025년 9월 12일
목표: 안정적이고 단순한 음악 재생 (다음곡 버튼 제거)
"""

import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from typing import Dict, Optional
from enum import Enum
from dataclasses import dataclass
import yt_dlp
import random

from utils.config import Config
from utils.helpers import (
    create_error_embed
)

# 로깅 설정
logger = logging.getLogger('cogs.music')

@dataclass
class Track:
    """음악 트랙 정보 클래스"""
    title: str
    url: str
    uploader: str = "Unknown"
    thumbnail: Optional[str] = None

class RepeatMode(Enum):
    """반복 모드 열거형"""
    OFF = "끄기"
    TRACK = "한곡"

class YTDLPSource:
    """yt-dlp를 사용한 음악 소스 처리"""
    
    # 다양한 User-Agent 목록 (유튜브 차단 우회용)
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
    ]
    
    YTDL_OPTIONS = {
        'format': 'bestaudio[ext=webm]/bestaudio/best',
        'extractaudio': True,
        'audioformat': 'webm',
        'noplaylist': True,
        'nocheckcertificate': False,  # HTTPS 인증서 검증 활성화
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'ytsearch',
        'source_address': '0.0.0.0',
        'retries': 10,
        'fragment_retries': 10,
        'socket_timeout': 30,
        # HTTPS 우회를 위한 추가 옵션
        'prefer_insecure': False,  # HTTPS 선호
        'force_ssl': True,  # SSL/TLS 강제 사용
        'http_headers': {},  # 동적으로 설정됨
        # 프록시 설정 (필요시)
        'proxy': None,  # 'https://your-proxy-server:port' 형태로 설정 가능
        # 지역 우회를 위한 추가 옵션
        'geo_bypass': True,
        'geo_bypass_country': 'US',  # 미국 지역으로 우회
        'geo_bypass_ip_block': None,
        # 봇 차단 우회 (YouTube bot detection bypass)
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android'],  # iOS/Android 클라이언트로 위장
                'skip': ['hls', 'dash']  # HLS/DASH 스킵
            }
        },
    }
    
    FFMPEG_OPTIONS = {
        'before_options': (
            '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 '
            '-reconnect_at_eof 1 -reconnect_on_network_error 1 '
            '-reconnect_on_http_error 4xx,5xx -nostdin'
        ),
        'options': '-vn -filter:a "volume=0.5"'
    }
    
    def __init__(self):
        # 환경 변수에 따라 옵션 동적 설정
        options = self.YTDL_OPTIONS.copy()
        
        # 랜덤 User-Agent 설정
        user_agent = random.choice(self.USER_AGENTS)
        options['http_headers'] = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ko;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
        
        # 프록시 설정
        proxy_url = Config.get_music_proxy_url()
        if proxy_url:
            options['proxy'] = proxy_url
            logger.info(f"음악 프록시 설정: {proxy_url}")
        
        # HTTPS 설정
        if Config.get_music_use_https():
            options['prefer_insecure'] = False
            options['force_ssl'] = True
            logger.info("음악 서비스 HTTPS 모드 활성화")
        
        # 지역 우회 설정
        if Config.get_music_geo_bypass():
            options['geo_bypass'] = True
            options['geo_bypass_country'] = 'US'
            logger.info("음악 서비스 지역 우회 활성화")
        
        # YouTube 쿠키 파일 설정 (봇 차단 우회)
        cookies_path = Config.get_youtube_cookies_path()
        if cookies_path:
            import os
            if os.path.exists(cookies_path):
                options['cookiefile'] = cookies_path
                logger.info(f"YouTube 쿠키 파일 사용: {cookies_path}")
            else:
                logger.warning(f"쿠키 파일을 찾을 수 없음: {cookies_path}")
        
        logger.info(f"yt-dlp 초기화 완료 - User-Agent: {user_agent[:50]}...")
        self.ytdl = yt_dlp.YoutubeDL(options)
    
    def normalize_url(self, url: str) -> str:
        """URL 정규화 - Shorts를 일반 watch URL로 변환"""
        # YouTube Shorts URL을 일반 watch URL로 변환
        if 'shorts/' in url:
            url = url.replace('/shorts/', '/watch?v=')
            logger.info(f"Shorts URL을 일반 URL로 변환: {url}")
        return url
        
    async def extract_info(self, search: str) -> tuple[Optional[Track], Optional[str]]:
        """유튜브에서 음악 정보 추출 - 오류 메시지도 함께 반환"""
        max_retries = 3
        retry_delay = 2
        
        # 빈 검색어 확인
        if not search or not search.strip():
            return None, "검색어가 비어있습니다."
        
        # 너무 짧은 검색어 확인
        if len(search.strip()) < 2:
            return None, "검색어가 너무 짧습니다. (최소 2글자)"
        
        # URL 정규화 (Shorts → 일반 URL)
        search = self.normalize_url(search)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"음악 검색 시작 (시도 {attempt + 1}/{max_retries}): {search}")
                
                # 재시도 시 새로운 User-Agent 사용
                if attempt > 0:
                    new_user_agent = random.choice(self.USER_AGENTS)
                    self.ytdl.params['http_headers']['User-Agent'] = new_user_agent
                    logger.info(f"재시도 - 새 User-Agent 사용: {new_user_agent[:50]}...")
                    await asyncio.sleep(retry_delay * attempt)  # 점진적 지연
                
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self.ytdl.extract_info(search, download=False)
                )
                    
                if data is None:
                    if attempt < max_retries - 1:
                        continue
                    return None, "검색 결과를 찾을 수 없습니다."
                    
                # 검색 결과에서 첫 번째 항목 선택
                if 'entries' in data and data['entries']:
                    if not data['entries']:
                        if attempt < max_retries - 1:
                            continue
                        return None, "검색 결과가 비어있습니다."
                    data = data['entries'][0]
                
                # 데이터 유효성 검증
                if not data:
                    if attempt < max_retries - 1:
                        continue
                    return None, "유효하지 않은 검색 결과입니다."
                    
                if not data.get('url'):
                    if attempt < max_retries - 1:
                        continue
                    return None, "스트리밍 URL을 찾을 수 없습니다."
                
                # 제목 확인
                title = data.get('title', '').strip()
                if not title or title.lower() in ['private video', 'deleted video', '[private video]', '[deleted video]']:
                    return None, "비공개 또는 삭제된 동영상입니다."
                    
                track = Track(
                    title=title,
                    url=data.get('url'),
                    uploader=data.get('uploader', 'Unknown'),
                    thumbnail=data.get('thumbnail')
                )
                
                logger.info(f"음악 정보 추출 성공: {track.title}")
                return track, None
                
            except yt_dlp.utils.DownloadError as e:
                error_msg = str(e).lower()
                logger.warning(f"시도 {attempt + 1} 실패: {e}")
                
                # 재시도 가능한 오류인지 확인
                if attempt < max_retries - 1:
                    if any(keyword in error_msg for keyword in ['network', 'connection', 'timeout', '429', 'rate limit']):
                        logger.info(f"재시도 가능한 오류 - {retry_delay * (attempt + 1)}초 후 재시도")
                        continue
                
                # 최종 실패 또는 재시도 불가능한 오류
                if 'private' in error_msg or 'unavailable' in error_msg:
                    return None, "비공개 또는 사용할 수 없는 동영상입니다."
                elif 'not found' in error_msg or 'no video' in error_msg:
                    return None, "동영상을 찾을 수 없습니다. 검색어를 확인해주세요."
                elif 'network' in error_msg or 'connection' in error_msg:
                    return None, "네트워크 연결 문제가 발생했습니다. 잠시 후 다시 시도해주세요."
                else:
                    return None, f"동영상 처리 중 오류가 발생했습니다: {str(e)[:100]}"
                    
            except Exception as e:
                logger.error(f"음악 정보 추출 실패 (시도 {attempt + 1}): {e}")
                error_msg = str(e).lower()
                
                # 재시도 가능한 오류인지 확인
                if attempt < max_retries - 1:
                    if any(keyword in error_msg for keyword in ['timeout', 'connection', 'network']):
                        logger.info(f"일반 오류 재시도 - {retry_delay * (attempt + 1)}초 후 재시도")
                        continue
                
                # 최종 실패
                if 'timeout' in error_msg:
                    return None, "요청 시간이 초과되었습니다. 다시 시도해주세요."
                elif 'forbidden' in error_msg:
                    return None, "접근이 제한된 동영상입니다."
                else:
                    return None, "알 수 없는 오류가 발생했습니다. 다른 검색어로 시도해주세요."
        
        # 모든 재시도 실패
        return None, f"모든 재시도 실패 ({max_retries}회 시도). 잠시 후 다시 시도해주세요."
            
    def get_discord_source(self, url: str) -> discord.FFmpegPCMAudio:
        """Discord 재생을 위한 오디오 소스 생성"""
        return discord.FFmpegPCMAudio(url, **self.FFMPEG_OPTIONS)

class MusicPlayer:
    """초간단 음악 플레이어 클래스 - 한 곡씩만 재생"""
    
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.voice_client: Optional[discord.VoiceClient] = None
        self.current_track: Optional[Track] = None
        self.is_playing = False
        self.is_paused = False
        self.repeat_mode: RepeatMode = RepeatMode.OFF
        self.ytdl_source = YTDLPSource()
        self.idle_timeout_task: Optional[asyncio.Task] = None
        self.alone_timeout_task: Optional[asyncio.Task] = None  # 혼자 있을 때 타임아웃
        self.IDLE_TIMEOUT = 300  # 5분
        self.ALONE_TIMEOUT = 300  # 5분 (혼자 있을 때)
        self.current_message: Optional[discord.Message] = None

    async def connect(self, channel: discord.VoiceChannel) -> bool:
        """음성 채널에 연결"""
        try:
            self._cancel_idle_timeout()
            
            if self.voice_client and self.voice_client.is_connected():
                await self.voice_client.move_to(channel)
            else:
                self.voice_client = await channel.connect()
            return True
        except Exception as e:
            logger.error(f"음성 채널 연결 실패: {e}")
            return False
            
    async def disconnect(self):
        """음성 채널에서 연결 해제 및 정리"""
        logger.info("음성 채널 연결 해제 시작")
        
        self._cancel_idle_timeout()
        self._cancel_alone_timeout()
        await self._delete_current_message()
        
        if self.voice_client:
            if self.voice_client.is_playing():
                self.voice_client.stop()
            if self.voice_client.is_connected():
                await self.voice_client.disconnect()
            self.voice_client = None
            
        # 상태 완전 초기화
        self.is_playing = False
        self.is_paused = False
        self.current_track = None
        
        logger.info("음성 채널 연결 해제 완료")
        
    def _is_alone_in_channel(self) -> bool:
        """음성 채널에 봇만 혼자 있는지 확인"""
        if not self.voice_client or not self.voice_client.channel:
            return False
            
        # 봇을 제외한 실제 사용자 수 계산
        human_members = [
            member for member in self.voice_client.channel.members 
            if not member.bot
        ]
        
        return len(human_members) == 0
        
    def _cancel_alone_timeout(self):
        """혼자 있을 때 타임아웃 취소"""
        if self.alone_timeout_task and not self.alone_timeout_task.done():
            self.alone_timeout_task.cancel()
            self.alone_timeout_task = None
            logger.debug("혼자 있을 때 타임아웃 취소됨")
    
    def _start_alone_timeout(self):
        """혼자 있을 때 5분 후 자동 퇴장 시작"""
        if not self._is_alone_in_channel():
            return  # 혼자가 아니면 타임아웃 시작하지 않음
            
        self._cancel_alone_timeout()
        
        async def alone_timeout_disconnect():
            try:
                await asyncio.sleep(self.ALONE_TIMEOUT)
                if self._is_alone_in_channel():  # 5분 후에도 여전히 혼자인지 확인
                    logger.info(f"길드 {self.guild_id}: 5분간 혼자 있어서 자동 퇴장")
                    await self.disconnect()
                else:
                    logger.debug("타임아웃 중 사람이 들어와서 퇴장 취소")
            except asyncio.CancelledError:
                logger.debug("혼자 있을 때 타임아웃이 취소됨")
        
        self.alone_timeout_task = asyncio.create_task(alone_timeout_disconnect())
        logger.debug("5분 혼자 있을 때 타임아웃 시작")
        
    def _check_and_handle_alone_status(self):
        """현재 혼자 있는 상태를 확인하고 적절히 처리"""
        if self._is_alone_in_channel():
            # 혼자 있으면 혼자 있을 때 타임아웃 시작, 일반 유휴 타임아웃 취소
            self._cancel_idle_timeout()
            self._start_alone_timeout()
        else:
            # 혼자가 아니면 혼자 있을 때 타임아웃 취소
            self._cancel_alone_timeout()
            # 재생 중이 아니면 일반 유휴 타임아웃 시작
            if not self.is_playing:
                self._start_idle_timeout()
        
    async def _delete_current_message(self):
        """현재 재생 중인 메시지 삭제"""
        if self.current_message:
            try:
                await self.current_message.delete()
                logger.info("재생 중인 메시지 삭제 완료")
            except Exception as e:
                logger.warning(f"메시지 삭제 실패: {e}")
            finally:
                self.current_message = None
        
    def _cancel_idle_timeout(self):
        """유휴 타임아웃 취소"""
        if self.idle_timeout_task and not self.idle_timeout_task.done():
            self.idle_timeout_task.cancel()
            self.idle_timeout_task = None
            logger.debug("유휴 타임아웃 취소됨")
    
    def _start_idle_timeout(self):
        """유휴 타임아웃 시작 (5분 후 자동 퇴장) - 혼자가 아닐 때만"""
        if self._is_alone_in_channel():
            return  # 혼자 있으면 일반 유휴 타임아웃 대신 혼자 있을 때 타임아웃 사용
            
        self._cancel_idle_timeout()
        
        async def timeout_disconnect():
            try:
                await asyncio.sleep(self.IDLE_TIMEOUT)
                logger.info(f"길드 {self.guild_id}: 5분간 비활성으로 자동 퇴장")
                await self.disconnect()
            except asyncio.CancelledError:
                logger.debug("타임아웃이 취소됨")
        
        self.idle_timeout_task = asyncio.create_task(timeout_disconnect())
        logger.debug("5분 유휴 타임아웃 시작")
        
    async def play_track(self, track: Track) -> tuple[bool, Optional[str]]:
        """트랙 재생 - 성공/실패 여부와 오류 메시지 반환"""
        if not self.voice_client or not self.voice_client.is_connected():
            logger.warning("음성 클라이언트가 연결되어 있지 않음")
            return False, "음성 채널에 연결되어 있지 않습니다."
            
        if self.voice_client.is_playing():
            self.voice_client.stop()
            
        self._cancel_idle_timeout()
            
        try:
            logger.info(f"재생 시도: {track.title}")
            
            # FFmpeg 소스 생성 시도
            try:
                source = self.ytdl_source.get_discord_source(track.url)
            except Exception as e:
                logger.error(f"오디오 소스 생성 실패: {e}")
                await self.disconnect()  # 실패 시 자동 퇴장
                return False, "오디오 스트림을 생성할 수 없습니다. 다른 곡을 시도해주세요."
            
            def after_callback(error):
                if error:
                    logger.error(f"재생 콜백 오류: {error}")
                try:
                    if (hasattr(self, 'voice_client') and 
                        self.voice_client and 
                        hasattr(self.voice_client, 'bot') and
                        self.voice_client.bot and
                        hasattr(self.voice_client.bot, 'loop')):
                        
                        bot_loop = self.voice_client.bot.loop
                        if bot_loop and not bot_loop.is_closed():
                            asyncio.run_coroutine_threadsafe(
                                self._after_playing(error), 
                                bot_loop
                            )
                        else:
                            logger.warning("봇 이벤트 루프가 닫혀있음")
                    else:
                        logger.warning("봇 인스턴스에 접근할 수 없음")
                        self.is_playing = False
                        self.is_paused = False
                except Exception as e:
                    logger.warning(f"After 콜백 처리 중 오류: {e}")
                    self.is_playing = False
                    self.is_paused = False
            
            # 재생 시도
            try:
                self.voice_client.play(source, after=after_callback)
            except Exception as e:
                logger.error(f"Discord 재생 시작 실패: {e}")
                await self.disconnect()  # 실패 시 자동 퇴장
                return False, "음성 재생을 시작할 수 없습니다."
            
            # 재생이 실제로 시작되었는지 확인
            await asyncio.sleep(0.5)  # 잠시 대기
            if not self.voice_client.is_playing():
                logger.error("재생이 시작되지 않음")
                await self.disconnect()  # 실패 시 자동 퇴장
                return False, "재생을 시작할 수 없습니다. 스트림에 문제가 있을 수 있습니다."
            
            self.current_track = track
            self.is_playing = True
            self.is_paused = False
            
            # 재생 시작 시 혼자 있는 상태 체크
            self._check_and_handle_alone_status()
            
            logger.info(f"재생 시작 성공: {track.title}")
            return True, None
            
        except Exception as e:
            logger.error(f"재생 실패: {e}")
            await self.disconnect()  # 실패 시 자동 퇴장
            return False, f"재생 중 오류가 발생했습니다: {str(e)[:100]}"
            
    async def _after_playing(self, error):
        """재생 완료 후 호출되는 콜백"""
        try:
            if error:
                logger.error(f"재생 중 오류: {error}")
                # 재생 오류 발생 시 자동 퇴장
                self.is_playing = False
                self.is_paused = False
                self.current_track = None
                await self._delete_current_message()
                await self.disconnect()
                return
                
            if not self.voice_client or not self.voice_client.is_connected():
                logger.warning("음성 클라이언트가 연결되어 있지 않음")
                self.is_playing = False
                self.is_paused = False
                return
                
            # 반복 모드 확인
            if self.repeat_mode == RepeatMode.TRACK and self.current_track:
                # 한곡 반복: 같은 곡을 다시 재생
                logger.info("한곡 반복 - 같은 곡을 다시 재생")
                await asyncio.sleep(1)
                success, error_msg = await self.play_track(self.current_track)
                if not success:
                    logger.error(f"반복 재생 실패: {error_msg}")
                    # 반복 재생 실패 시에도 자동 퇴장
                    await self._delete_current_message()
                    await self.disconnect()
            else:
                # 반복 없음: 재생 종료
                logger.info("재생 완료 - 재생 메시지 삭제 후 상태별 타임아웃 시작")
                self.is_playing = False
                self.is_paused = False
                self.current_track = None
                await self._delete_current_message()
                self._check_and_handle_alone_status()  # 혼자 있는지 확인하고 적절한 타임아웃 시작
                
        except Exception as e:
            logger.error(f"_after_playing에서 예외 발생: {e}")
            self.is_playing = False
            self.is_paused = False
            # 예외 발생 시에도 안전하게 퇴장
            try:
                await self.disconnect()
            except Exception as disconnect_error:
                logger.error(f"퇴장 중 추가 오류: {disconnect_error}")

class MusicControlView(discord.ui.View):
    """간단한 음악 제어 UI - 3개 버튼: 일시정지/재생, 반복, 정지"""
    
    def __init__(self, music_player: MusicPlayer):
        super().__init__(timeout=300)
        self.music_player = music_player
        
    @discord.ui.button(label="⏸️", style=discord.ButtonStyle.secondary, row=0)
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """일시정지/재생 버튼"""
        if not self.music_player.voice_client:
            return
            
        if self.music_player.voice_client.is_playing():
            self.music_player.voice_client.pause()
            self.music_player.is_paused = True
            button.label = "▶️"
            await interaction.response.edit_message(view=self)
        elif self.music_player.voice_client.is_paused():
            self.music_player.voice_client.resume()
            self.music_player.is_paused = False
            button.label = "⏸️"
            await interaction.response.edit_message(view=self)
        else:
            await self.music_player._delete_current_message()
            await interaction.response.defer()
            
    @discord.ui.button(label="🔄", style=discord.ButtonStyle.secondary, row=0)
    async def repeat_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """반복 모드 버튼 - ON/OFF만"""
        if self.music_player.repeat_mode == RepeatMode.OFF:
            self.music_player.repeat_mode = RepeatMode.TRACK
            button.label = "🔂"  # 한곡 반복 ON
        else:
            self.music_player.repeat_mode = RepeatMode.OFF
            button.label = "🔄"  # 반복 OFF
            
        await interaction.response.edit_message(view=self)
            
    @discord.ui.button(label="⏹️", style=discord.ButtonStyle.danger, row=0)
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """정지 및 퇴장 버튼"""
        await self.music_player.disconnect()
        await interaction.response.defer()

class MusicCog(commands.Cog):
    """간단한 Siri Bot 음악 시스템"""
    
    def __init__(self, bot):
        self.bot = bot
        self.players: Dict[int, MusicPlayer] = {}
        
    async def cog_unload(self):
        """Cog 언로드 시 모든 음성 연결 정리"""
        logger.info("음악 시스템 종료 - 모든 연결 정리 중...")
        for player in self.players.values():
            try:
                await player.disconnect()
            except Exception as e:
                logger.error(f"플레이어 정리 중 오류: {e}")
        self.players.clear()
        
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """음성 채널 상태 변화 감지 - 사람이 들어오거나 나갈 때 타임아웃 관리"""
        # 봇 자신의 상태 변화는 무시
        if member.bot:
            return
            
        # 봇이 있는 길드에서만 처리
        if member.guild.id not in self.players:
            return
            
        player = self.players[member.guild.id]
        
        # 봇이 음성 채널에 연결되어 있지 않으면 무시
        if not player.voice_client or not player.voice_client.channel:
            return
            
        bot_channel = player.voice_client.channel
        
        # 봇이 있는 채널과 관련된 변화만 처리
        channel_related = (
            (before.channel and before.channel.id == bot_channel.id) or
            (after.channel and after.channel.id == bot_channel.id)
        )
        
        if not channel_related:
            return
            
        # 상태 변화 로깅
        if before.channel != after.channel:
            if after.channel and after.channel.id == bot_channel.id:
                logger.info(f"사용자 {member.display_name}이 봇의 음성 채널에 입장")
            elif before.channel and before.channel.id == bot_channel.id:
                logger.info(f"사용자 {member.display_name}이 봇의 음성 채널에서 퇴장")
        
        # 현재 채널 상태를 확인하고 타임아웃 관리
        player._check_and_handle_alone_status()
        
    def get_player(self, guild_id: int) -> MusicPlayer:
        """길드별 음악 플레이어 가져오기"""
        if guild_id not in self.players:
            self.players[guild_id] = MusicPlayer(guild_id)
        return self.players[guild_id]
        
    async def _delete_message_after_delay(self, message: discord.Message, delay: int):
        """지정된 시간 후 메시지 삭제"""
        try:
            await asyncio.sleep(delay)
            await message.delete()
        except Exception as e:
            logger.warning(f"메시지 삭제 실패: {e}")
        
    @app_commands.command(name="재생", description="유튜브 음악을 재생합니다")
    @app_commands.describe(검색어="유튜브 URL 또는 검색할 곡 이름")
    async def play_music(self, interaction: discord.Interaction, 검색어: str):
        """음악 재생 명령어"""
        await interaction.response.defer()
        
        # 사용자가 음성 채널에 있는지 확인
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = create_error_embed(
                "❌ 음성 채널 없음",
                "음성 채널에 먼저 참여해주세요!"
            )
            message = await interaction.followup.send(embed=embed)
            asyncio.create_task(self._delete_message_after_delay(message, 5))
            return
            
        player = self.get_player(interaction.guild.id)
        
        # 이미 음악이 재생 중인지 확인
        if player.is_playing:
            await interaction.followup.send(
                "이미 노래가 재생중입니다",
                ephemeral=True
            )
            return
            
        player._cancel_idle_timeout()
        
        # 음성 채널 연결
        if not await player.connect(interaction.user.voice.channel):
            embed = create_error_embed(
                "❌ 연결 실패",
                "음성 채널에 연결할 수 없습니다."
            )
            message = await interaction.followup.send(embed=embed)
            asyncio.create_task(self._delete_message_after_delay(message, 10))
            return
            
        # 음악 정보 추출
        track_info, error_message = await player.ytdl_source.extract_info(검색어)
        if not track_info:
            await player.disconnect()  # 검색 실패 시 자동 퇴장
            embed = create_error_embed(
                "❌ 검색 실패",
                error_message or f"'{검색어}'에 대한 결과를 찾을 수 없습니다."
            )
            message = await interaction.followup.send(embed=embed)
            asyncio.create_task(self._delete_message_after_delay(message, 10))
            return
            
        # 단일 트랙 재생
        success, play_error = await player.play_track(track_info)
        if success:
            # 간단한 재생 임베드
            embed = discord.Embed(
                title="🎵 재생 중",
                description=f"**{track_info.title}**",
                color=Config.COLORS['success']
            )
            
            if track_info.thumbnail:
                embed.set_image(url=track_info.thumbnail)  # 큰 이미지로 변경
                
            embed.add_field(
                name="🎤 아티스트",
                value=track_info.uploader,
                inline=False
            )
                
            embed.set_footer(text="Siri Bot Music Player")
            
            view = MusicControlView(player)
            message = await interaction.followup.send(embed=embed, view=view)
            player.current_message = message
        else:
            # 재생 실패 - player.play_track에서 이미 disconnect 됨
            embed = create_error_embed(
                "❌ 재생 실패",
                play_error or "음악을 재생할 수 없습니다."
            )
            message = await interaction.followup.send(embed=embed)
            asyncio.create_task(self._delete_message_after_delay(message, 10))

async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(MusicCog(bot))
    logger.info("간단한 음악 시스템 로드 완료")