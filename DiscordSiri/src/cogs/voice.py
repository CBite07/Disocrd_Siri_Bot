"""
Edge-TTS 음성 기능 Cog
디스코드 음성 채널에 자동으로 참여하고 TTS를 통해 인사하는 기능

핵심 기능:
- /자동참여: 자동 참여 모드 ON/OFF (관리자 전용)
- /시리야: 음성 채널에 참여
- /퇴장해: 음성 채널에서 나가기
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
import edge_tts
import asyncio
import os
from pathlib import Path
import tempfile
import re

from utils.config import Config
from utils.helpers import has_admin_permissions

logger = logging.getLogger(__name__)

class VoiceCog(commands.Cog):
    """Edge-TTS 음성 기능"""
    
    def __init__(self, bot):
        self.bot = bot
        # 서버별 자동 참여 설정 저장 (길드 ID: bool)
        self.auto_join_settings = {}
        # TTS 음성 설정 (한국어 여성 음성)
        self.voice = "ko-KR-SunHiNeural"
        # 임시 파일 저장 경로
        self.temp_dir = Path(tempfile.gettempdir()) / "siri_tts"
        self.temp_dir.mkdir(exist_ok=True)
        
        # 이모티콘 매핑 (디스코드 커스텀 이모티콘 및 유니코드 이모티콘)
        self.emoji_mapping = {
            '😀': '웃음', '😁': '활짝 웃음', '😂': '크게 웃음', '🤣': '바닥 구름',
            '😃': '웃는 얼굴', '😄': '미소', '😅': '식은땀', '😆': '껄껄',
            '😊': '미소', '😇': '천사', '🙂': '미소', '🙃': '거꾸로 미소',
            '😉': '윙크', '😌': '안도', '😍': '하트 눈', '🥰': '하트',
            '😘': '키스', '😗': '뽀뽀', '😙': '키스', '😚': '뽀뽀',
            '😋': '맛있어', '😛': '메롱', '😝': '메롱', '😜': '윙크 메롱',
            '🤪': '신남', '🤨': '의심', '🧐': '관찰', '🤓': '공부',
            '😎': '멋짐', '🤩': '놀람', '🥳': '파티', '😏': '음흉',
            '😒': '무표정', '😞': '실망', '😔': '슬픔', '😟': '걱정',
            '😕': '혼란', '🙁': '슬픔', '☹️': '슬픔', '😣': '괴로움',
            '😖': '고통', '😫': '피곤', '😩': '지침', '🥺': '애원',
            '😢': '눈물', '😭': '엉엉', '😤': '화남', '😠': '화남',
            '😡': '분노', '🤬': '욕', '🤯': '폭발', '😳': '당황',
            '🥵': '더워', '🥶': '추워', '😱': '비명', '😨': '놀람',
            '😰': '땀', '😥': '안타까움', '😓': '식은땀', '🤗': '포옹',
            '🤔': '생각', '🤭': '킥킥', '🤫': '쉿', '🤥': '거짓말',
            '😶': '무언', '😐': '무표정', '😑': '무표정', '😬': '이빨',
            '🙄': '눈동자', '😯': '놀람', '😦': '놀람', '😧': '고뇌',
            '😮': '놀람', '😲': '놀람', '🥱': '하품', '😴': '졸림',
            '🤤': '침', '😪': '졸림', '😵': '어지러움', '🤐': '침묵',
            '🥴': '어질어질', '🤢': '구역질', '🤮': '토함', '🤧': '재채기',
            '😷': '마스크', '🤒': '아픔', '🤕': '다침', '🤑': '돈',
            '🤠': '카우보이', '👍': '좋아요', '👎': '싫어요', '👏': '박수',
            '🙌': '만세', '👌': '오케이', '✌️': '브이', '🤞': '행운',
            '🤟': '사랑해', '🤘': '락', '🤙': '전화', '👋': '안녕',
            '🤚': '손', '✋': '손바닥', '🖐️': '다섯손가락', '🖖': '스팍',
            '👊': '주먹', '✊': '주먹', '🤛': '주먹', '🤜': '주먹',
            '🙏': '기도', '💪': '힘', '🦵': '다리', '🦶': '발',
            '❤️': '하트', '🧡': '주황하트', '💛': '노랑하트', '💚': '초록하트',
            '💙': '파랑하트', '💜': '보라하트', '🖤': '검정하트', '🤍': '하얀하트',
            '🤎': '갈색하트', '💔': '상한하트', '❣️': '하트', '💕': '하트',
            '💞': '하트', '💓': '하트', '💗': '하트', '💖': '하트',
            '💘': '하트화살', '💝': '하트리본', '💟': '하트장식', '🔥': '불',
            '💯': '백점', '💢': '화남', '💥': '충돌', '💫': '어지러움',
            '💦': '물방울', '💨': '바람', '🕳️': '구멍', '💬': '말풍선',
            '👀': '눈', '👁️': '눈', '🧠': '뇌', '🫀': '심장',
            '🎵': '음표', '🎶': '음악', '🎤': '마이크', '🎧': '헤드폰',
            '📱': '휴대폰', '💻': '노트북', '⌨️': '키보드', '🖥️': '컴퓨터',
            '🎮': '게임', '🕹️': '조이스틱', '🎲': '주사위', '🎯': '과녁',
            '🎰': '슬롯', '🎳': '볼링', '⚽': '축구공', '🏀': '농구공',
            '🏈': '미식축구공', '⚾': '야구공', '🥎': '소프트볼', '🎾': '테니스공',
            '🏐': '배구공', '🏉': '럭비공', '🥏': '프리스비', '🎱': '당구공',
            '🏓': '탁구', '🏸': '배드민턴', '🏒': '하키', '🏑': '필드하키',
            '🥍': '라크로스', '🏏': '크리켓', '🥅': '골대', '⛳': '골프',
            '🍕': '피자', '🍔': '햄버거', '🍟': '감자튀김', '🌭': '핫도그',
            '🍿': '팝콘', '🧂': '소금', '🥗': '샐러드', '🍝': '스파게티',
            '🍜': '라면', '🍲': '음식', '🍛': '카레', '🍣': '초밥',
            '🍱': '도시락', '🥟': '만두', '🦪': '굴', '🍤': '새우튀김',
            '🍙': '주먹밥', '🍚': '밥', '🍘': '센베이', '🍥': '어묵',
            '🥠': '포춘쿠키', '🥮': '월병', '🍢': '꼬치', '🍡': '경단',
            '🍧': '빙수', '🍨': '아이스크림', '🍦': '소프트아이스크림', '🥧': '파이',
            '🧁': '컵케이크', '🍰': '케이크', '🎂': '생일케이크', '🍮': '푸딩',
            '🍭': '막대사탕', '🍬': '사탕', '🍫': '초콜릿', '🍿': '팝콘',
            '🍩': '도넛', '🍪': '쿠키', '🌰': '밤', '🥜': '땅콩',
            '☕': '커피', '🍵': '차', '🧃': '주스', '🥤': '음료',
            '🧋': '버블티', '🍶': '술', '🍺': '맥주', '🍻': '건배',
            '🥂': '샴페인', '🍷': '와인', '🥃': '위스키', '🍸': '칵테일',
            '🍹': '트로피컬', '🧉': '마테', '🚗': '자동차', '🚕': '택시',
            '🚙': '에스유브이', '🚌': '버스', '🚎': '트롤리', '🏎️': '레이싱카',
            '🚓': '경찰차', '🚑': '구급차', '🚒': '소방차', '🚐': '미니버스',
            '🛻': '픽업트럭', '🚚': '트럭', '🚛': '트럭', '🚜': '트랙터',
            '🏍️': '오토바이', '🛵': '스쿠터', '🚲': '자전거', '🛴': '킥보드',
            '✈️': '비행기', '🚁': '헬기', '🛶': '카누', '⛵': '요트',
            '🚤': '모터보트', '🛥️': '보트', '⛴️': '페리', '🚢': '배',
        }
        
        # 반복 문자 패턴 매핑
        self.repeat_char_mapping = {
            'ㅋ': '크크크',
            'ㅎ': '흐흐흐',
            'ㄷ': '덜덜덜',
            'ㅠ': '흑흑흑',
            'ㅜ': '흑흑흑',
        }
    
    def process_message_for_tts(self, text: str) -> str:
        """
        TTS를 위한 메시지 전처리
        
        - 이모티콘을 한글 단어로 변환
        - 반복 문자 패턴 처리 (ㅋㅋㅋ, ㅎㅎㅎ 등)
        - 디스코드 커스텀 이모티콘 제거
        - URL 제거
        
        Args:
            text: 원본 메시지
            
        Returns:
            처리된 텍스트
        """
        # 디스코드 커스텀 이모티콘 제거 (<:이름:ID> 또는 <a:이름:ID> 형식)
        text = re.sub(r'<a?:\w+:\d+>', '', text)
        
        # URL 제거 (http:// 또는 https://)
        text = re.sub(r'https?://\S+', '링크', text)
        
        # 유니코드 이모티콘을 한글로 변환
        for emoji, korean in self.emoji_mapping.items():
            text = text.replace(emoji, f' {korean} ')
        
        # 반복되는 자음/모음 패턴 처리 (ㅋㅋㅋ, ㅎㅎㅎ 등)
        for char, replacement in self.repeat_char_mapping.items():
            # 2개 이상 반복되는 패턴을 찾아서 변환
            pattern = f'{char}{{2,}}'
            if re.search(pattern, text):
                # 반복 횟수에 따라 다르게 처리
                matches = re.finditer(pattern, text)
                for match in matches:
                    repeat_count = len(match.group())
                    if repeat_count <= 3:
                        tts_text = replacement
                    elif repeat_count <= 6:
                        tts_text = replacement + ' ' + replacement
                    else:
                        tts_text = replacement + ' ' + replacement + ' ' + replacement
                    text = text.replace(match.group(), tts_text, 1)
        
        # 여러 공백을 하나로
        text = re.sub(r'\s+', ' ', text)
        
        # 앞뒤 공백 제거
        text = text.strip()
        
        return text
    
    async def generate_tts(self, text: str) -> str:
        """
        Edge-TTS를 사용하여 음성 파일 생성
        
        Args:
            text: 변환할 텍스트
            
        Returns:
            생성된 오디오 파일의 경로
        """
        try:
            # 임시 파일 경로 생성
            temp_file = self.temp_dir / f"tts_{asyncio.current_task().get_name()}_{id(text)}.mp3"
            
            # Edge-TTS로 음성 생성
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(temp_file))
            
            logger.info(f"TTS 파일 생성 완료: {temp_file}")
            return str(temp_file)
            
        except Exception as e:
            logger.error(f"TTS 생성 중 오류 발생: {e}")
            raise
    
    async def play_tts(self, voice_client: discord.VoiceClient, text: str):
        """
        음성 채널에서 TTS 재생
        
        Args:
            voice_client: 음성 클라이언트
            text: 재생할 텍스트
        """
        try:
            # TTS 파일 생성
            audio_file = await self.generate_tts(text)
            
            # 오디오 소스 생성
            audio_source = discord.FFmpegPCMAudio(audio_file)
            
            # 재생 완료를 기다리기 위한 이벤트
            done = asyncio.Event()
            
            def after_playing(error):
                if error:
                    logger.error(f"재생 중 오류: {error}")
                # 파일 삭제
                try:
                    os.remove(audio_file)
                    logger.info(f"임시 파일 삭제: {audio_file}")
                except Exception as e:
                    logger.error(f"임시 파일 삭제 실패: {e}")
                done.set()
            
            # 음성 재생
            voice_client.play(audio_source, after=after_playing)
            
            # 재생 완료 대기 (최대 10초)
            try:
                await asyncio.wait_for(done.wait(), timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("TTS 재생 타임아웃")
                voice_client.stop()
            
        except Exception as e:
            logger.error(f"TTS 재생 중 오류: {e}")
            raise
    
    @app_commands.command(
        name="자동참여",
        description="음성 채널 자동 참여 모드를 설정합니다 (관리자 전용)"
    )
    @app_commands.describe(
        활성화="자동 참여 모드 활성화 여부 (ON/OFF)"
    )
    @app_commands.choices(활성화=[
        app_commands.Choice(name="ON", value=1),
        app_commands.Choice(name="OFF", value=0)
    ])
    async def auto_join(
        self,
        interaction: discord.Interaction,
        활성화: app_commands.Choice[int]
    ):
        """
        자동 참여 모드 설정 (관리자 전용)
        
        활성화 시 음성 채널에 사용자가 입장하면 봇이 자동으로 따라 입장합니다.
        """
        # 관리자 권한 확인
        if not await has_admin_permissions(interaction.user):
            embed = discord.Embed(
                title="❌ 권한 없음",
                description="이 명령어는 관리자만 사용할 수 있습니다.",
                color=Config.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 설정 저장
        guild_id = interaction.guild.id
        is_enabled = bool(활성화.value)
        self.auto_join_settings[guild_id] = is_enabled
        
        # 응답 생성
        status = "활성화" if is_enabled else "비활성화"
        emoji = "✅" if is_enabled else "❌"
        
        embed = discord.Embed(
            title=f"{emoji} 자동 참여 설정",
            description=f"자동 참여 모드를 **{status}**할게요!",
            color=Config.COLORS['success'] if is_enabled else Config.COLORS['error']
        )
        embed.add_field(
            name="📌 안내",
            value=f"{'이제 음성 채널에 누군가 입장하면 시리가 자동으로 따라 들어갑니다.' if is_enabled else '이제 음성 채널에 자동으로 참여하지 않습니다.'}",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"길드 {guild_id}의 자동 참여 모드: {status}")
    
    @app_commands.command(
        name="시리야",
        description="시리를 음성 채널로 불러옵니다"
    )
    async def join_voice(self, interaction: discord.Interaction):
        """
        음성 채널에 참여하는 명령어
        
        사용자가 있는 음성 채널에 봇이 입장하고 인사말을 재생합니다.
        """
        # 사용자가 음성 채널에 있는지 확인
        if not interaction.user.voice or not interaction.user.voice.channel:
            embed = discord.Embed(
                title="❌ 음성 채널 없음",
                description="먼저 음성 채널에 입장해주세요!",
                color=Config.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        channel = interaction.user.voice.channel
        
        # 응답 지연 (음성 연결은 시간이 걸릴 수 있음)
        await interaction.response.defer()
        
        try:
            # 이미 음성 채널에 연결되어 있는 경우
            if interaction.guild.voice_client:
                # 같은 채널인 경우
                if interaction.guild.voice_client.channel == channel:
                    embed = discord.Embed(
                        title="ℹ️ 이미 참여 중",
                        description="이미 이 음성 채널에 있어요!",
                        color=Config.COLORS['info']
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                # 다른 채널인 경우 이동
                else:
                    await interaction.guild.voice_client.move_to(channel)
            # 연결되어 있지 않은 경우 새로 연결
            else:
                voice_client = await channel.connect()
                # 연결 직후 약간의 대기 시간
                await asyncio.sleep(0.5)
            
            # 입장 메시지 전송
            embed = discord.Embed(
                title="🎤 시리 참여",
                description="지금 바로 들어갈게요!",
                color=Config.COLORS['success']
            )
            embed.set_footer(text=f"{channel.name} 채널에 참여했습니다")
            await interaction.followup.send(embed=embed)
            
            # TTS 인사말 재생
            try:
                await self.play_tts(interaction.guild.voice_client, "안녕하세요!")
            except Exception as e:
                logger.error(f"TTS 재생 실패: {e}")
            
            logger.info(f"음성 채널 참여: {channel.name} (길드: {interaction.guild.name})")
            
        except discord.ClientException as e:
            logger.error(f"음성 채널 참여 실패 (ClientException): {e}")
            embed = discord.Embed(
                title="❌ 참여 실패",
                description="음성 채널 참여에 실패했습니다. 잠시 후 다시 시도해주세요.",
                color=Config.COLORS['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"음성 채널 참여 중 오류: {e}")
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="음성 채널 참여 중 오류가 발생했습니다.",
                color=Config.COLORS['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(
        name="퇴장해",
        description="시리를 음성 채널에서 내보냅니다"
    )
    async def leave_voice(self, interaction: discord.Interaction):
        """
        음성 채널에서 퇴장하는 명령어
        
        봇이 음성 채널에서 나가기 전 작별 인사를 재생합니다.
        """
        # 봇이 음성 채널에 있는지 확인
        if not interaction.guild.voice_client:
            embed = discord.Embed(
                title="❌ 참여하지 않음",
                description="음성 채널에 참여하고 있지 않습니다!",
                color=Config.COLORS['error']
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # 응답 지연
        await interaction.response.defer()
        
        try:
            # 퇴장 메시지 전송
            channel_name = interaction.guild.voice_client.channel.name
            
            embed = discord.Embed(
                title="👋 시리 퇴장",
                description="좋아요, 이만 물러날게요!",
                color=Config.COLORS['info']
            )
            embed.set_footer(text=f"{channel_name} 채널에서 나갑니다")
            await interaction.followup.send(embed=embed)
            
            # TTS 작별 인사 재생
            try:
                await self.play_tts(interaction.guild.voice_client, "안녕히 계세요!")
                # 작별 인사 후 약간의 대기
            except Exception as e:
                logger.error(f"TTS 재생 실패: {e}")
            
            # 음성 채널 연결 종료
            await interaction.guild.voice_client.disconnect()
            logger.info(f"음성 채널 퇴장: {channel_name} (길드: {interaction.guild.name})")
            
        except Exception as e:
            logger.error(f"음성 채널 퇴장 중 오류: {e}")
            embed = discord.Embed(
                title="❌ 오류 발생",
                description="음성 채널 퇴장 중 오류가 발생했습니다.",
                color=Config.COLORS['error']
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        메시지 이벤트 리스너
        
        음성 채널에 있는 사용자가 메시지를 보내면 TTS로 읽어줍니다.
        """
        # 봇 메시지 무시
        if message.author.bot:
            return
        
        # 길드(서버)가 없는 경우 무시 (DM 등)
        if not message.guild:
            return
        
        # 봇이 음성 채널에 연결되어 있는지 확인
        voice_client = message.guild.voice_client
        if not voice_client or not voice_client.is_connected():
            return
        
        # 메시지 작성자가 음성 채널에 있는지 확인
        if not message.author.voice or not message.author.voice.channel:
            return
        
        # 봇과 같은 음성 채널에 있는지 확인
        if message.author.voice.channel != voice_client.channel:
            return
        
        # 명령어는 읽지 않음
        if message.content.startswith(('/','!','?','.')):
            return
        
        # 메시지가 비어있으면 무시
        if not message.content.strip():
            return
        
        try:
            # 현재 재생 중이면 대기
            while voice_client.is_playing():
                await asyncio.sleep(0.5)
            
            # 메시지 전처리 (이모티콘, 반복 문자 등 처리)
            tts_text = self.process_message_for_tts(message.content)
            
            # 처리 후 빈 메시지면 무시
            if not tts_text.strip():
                return
            
            # 너무 긴 메시지는 잘라서 읽기 (200자 제한)
            if len(tts_text) > 200:
                tts_text = tts_text[:200] + "... 이하 생략"
            
            await self.play_tts(voice_client, tts_text)
            logger.info(f"TTS 메시지 읽음: {message.author.display_name} - {tts_text[:50]}")
            
        except Exception as e:
            logger.error(f"메시지 TTS 재생 중 오류: {e}")
    
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        """
        음성 상태 변경 이벤트 리스너
        
        자동 참여 모드가 활성화되어 있을 때:
        - 사용자가 음성 채널에 입장하면 봇도 자동으로 입장
        - 채널에 아무도 없으면 봇이 자동으로 퇴장
        """
        guild = member.guild
        
        # 봇 자신의 이벤트는 무시
        if member.bot:
            return
        
        # 자동 참여 설정 확인
        auto_join_enabled = self.auto_join_settings.get(guild.id, False)
        
        # 사용자가 음성 채널에 입장한 경우
        if after.channel and not before.channel and auto_join_enabled:
            # 봇이 이미 해당 채널에 있는 경우 무시
            if guild.voice_client and guild.voice_client.channel == after.channel:
                return
            
            try:
                # 봇이 다른 채널에 있으면 이동, 없으면 입장
                if guild.voice_client:
                    await guild.voice_client.move_to(after.channel)
                else:
                    await after.channel.connect()
                    await asyncio.sleep(0.5)
                
                # TTS 인사말 재생
                try:
                    await self.play_tts(
                        guild.voice_client,
                        f"{member.display_name}님, 안녕하세요!"
                    )
                except Exception as e:
                    logger.error(f"자동 참여 TTS 재생 실패: {e}")
                
                logger.info(f"자동 참여: {after.channel.name} (사용자: {member.display_name})")
                
            except Exception as e:
                logger.error(f"자동 참여 중 오류: {e}")
        
        # 채널에 아무도 없으면 봇 퇴장
        if guild.voice_client:
            voice_channel = guild.voice_client.channel
            # 봇을 제외한 멤버 수 확인
            members = [m for m in voice_channel.members if not m.bot]
            if len(members) == 0:
                try:
                    await guild.voice_client.disconnect()
                    logger.info(f"빈 채널에서 자동 퇴장: {voice_channel.name}")
                except Exception as e:
                    logger.error(f"자동 퇴장 중 오류: {e}")
    
    async def cog_unload(self):
        """Cog 언로드 시 정리 작업"""
        logger.info("VoiceCog 언로드 시작 - 음성 채널 정리 중...")
        
        # 모든 음성 연결 정리
        for guild in self.bot.guilds:
            if guild.voice_client:
                try:
                    # 현재 재생 중이면 중지
                    if guild.voice_client.is_playing():
                        guild.voice_client.stop()
                        logger.info(f"{guild.name}: 재생 중인 오디오 중지")
                        await asyncio.sleep(0.2)
                    
                    # 간단한 작별 인사 (언로드 시에는 빠르게)
                    try:
                        tts_text = "다시 올게요"
                        audio_file = await self.generate_tts(tts_text)
                        audio_source = discord.FFmpegPCMAudio(audio_file)
                        
                        done = asyncio.Event()
                        
                        def cleanup_file(error):
                            try:
                                if os.path.exists(audio_file):
                                    os.remove(audio_file)
                            except:
                                pass
                            done.set()
                        
                        guild.voice_client.play(audio_source, after=cleanup_file)
                        
                        # 최대 2초 대기
                        try:
                            await asyncio.wait_for(done.wait(), timeout=2.0)
                        except asyncio.TimeoutError:
                            guild.voice_client.stop()
                            
                    except Exception as e:
                        logger.warning(f"{guild.name}: 작별 인사 실패 - {e}")
                    
                    # 연결 종료
                    await guild.voice_client.disconnect()
                    logger.info(f"Cog 언로드: {guild.name}에서 연결 종료")
                    
                except Exception as e:
                    logger.error(f"{guild.name} 연결 종료 중 오류: {e}")
        
        # 임시 파일 정리
        try:
            cleaned_count = 0
            for file in self.temp_dir.glob("tts_*.mp3"):
                try:
                    file.unlink()
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"파일 삭제 실패 {file}: {e}")
            
            if cleaned_count > 0:
                logger.info(f"임시 TTS 파일 {cleaned_count}개 정리 완료")
        except Exception as e:
            logger.error(f"임시 파일 정리 중 오류: {e}")
        
        logger.info("VoiceCog 언로드 완료")


async def setup(bot):
    """Cog 로드"""
    await bot.add_cog(VoiceCog(bot))
    logger.info("VoiceCog 로드 완료")
