"""
설정 관리 모듈
환경 변수 및 봇 설정을 중앙 집중식으로 관리
"""

import os

class Config:
    """봇 설정 클래스"""
    
    # 환경 변수에서 설정 로드 (메서드로 동적 접근)
    @staticmethod
    def get_bot_token() -> str:
        """Siri 봇 토큰 (하위 호환성)"""
        return os.getenv("SIRI_BOT_TOKEN", os.getenv("DISCORD_BOT_TOKEN", ""))
    
    @staticmethod
    def get_siri_bot_token() -> str:
        """Siri 봇 토큰"""
        return os.getenv("SIRI_BOT_TOKEN", "")
    
    @staticmethod
    def get_gpt_bot_token() -> str:
        """GPT 봇 토큰"""
        return os.getenv("GPT_BOT_TOKEN", "")
    
    @staticmethod
    def get_gpt_api_host() -> str:
        """GPT 봇 API 호스트"""
        return os.getenv("GPT_BOT_API_HOST", "localhost")
    
    @staticmethod
    def get_gpt_api_port() -> int:
        """GPT 봇 API 포트"""
        return int(os.getenv("GPT_BOT_API_PORT", "5000"))
    
    @staticmethod
    def get_database_path() -> str:
        return os.getenv("DATABASE_PATH", "./src/data/siri_bot.db")
    
    @staticmethod
    def get_command_prefix() -> str:
        return os.getenv("COMMAND_PREFIX", "!")
    
    @staticmethod
    def get_https_enabled() -> bool:
        return os.getenv("HTTPS_ENABLED", "False").lower() == "true"
    
    @staticmethod
    def get_ssl_cert_path() -> str:
        return os.getenv("SSL_CERT_PATH", "")
    
    @staticmethod
    def get_ssl_key_path() -> str:
        return os.getenv("SSL_KEY_PATH", "")
    
    @staticmethod
    def get_music_proxy_url() -> str:
        return os.getenv("MUSIC_PROXY_URL", "")
    
    @staticmethod
    def get_youtube_cookies_path() -> str:
        """YouTube 쿠키 파일 경로"""
        return os.getenv("YOUTUBE_COOKIES_PATH", "")
    
    @staticmethod
    def get_music_use_https() -> bool:
        return os.getenv("MUSIC_USE_HTTPS", "True").lower() == "true"
    
    @staticmethod
    def get_music_geo_bypass() -> bool:
        return os.getenv("MUSIC_GEO_BYPASS", "True").lower() == "true"
    
    # 호환성을 위한 프로퍼티
    BOT_TOKEN = property(lambda self: Config.get_bot_token())
    DATABASE_PATH = property(lambda self: Config.get_database_path()) 
    COMMAND_PREFIX = property(lambda self: Config.get_command_prefix())
    
    # XP 및 레벨 설정
    XP_PER_ATTENDANCE = 50  # 출석 시 획득 XP
    BASE_XP_REQUIREMENT = 100  # 레벨 1->2 기본 XP
    XP_MULTIPLIER = 1.5  # XP 증가 배율 (기하급수적 증가)
    
    # 쿨다운 설정 (초 단위)
    ATTENDANCE_COOLDOWN = 24 * 60 * 60  # 24시간
    
    # 디스코드 색상 코드
    COLORS = {
        'success': 0x00ff00,    # 초록색
        'error': 0xff0000,      # 빨간색 
        'info': 0x3498db,       # 파란색
        'warning': 0xffa500,    # 주황색
        'level_up': 0xffd700    # 골드색
    }
    
    # 레벨별 역할 매핑
    # 레벨 구간: (시작 레벨, 끝 레벨, 역할 ID)
    ROLE_LEVELS = {
        (1, 9): 1392422549174091868,      # 초보자
        (10, 19): 1392431487697293465,    # 입문자  
        (20, 29): 1392431532592857182,    # 숙련자
        (30, 39): 1392431564574687323,    # 전문가
        (40, 49): 1392431591304990730,    # 마스터
        (50, 69): 1392431665376264192,    # 그랜드마스터
        (70, 999): 1392431727292448922,   # 레전드 (70레벨 이상)
    }
    
    @classmethod
    def get_role_for_level(cls, level: int) -> int | None:
        """레벨에 맞는 역할 ID 반환"""
        for (min_level, max_level), role_id in cls.ROLE_LEVELS.items():
            if min_level <= level <= max_level:
                return role_id
        return None
    
    @classmethod
    def calculate_xp_for_level(cls, level: int) -> int:
        """특정 레벨 달성에 필요한 총 XP 계산"""
        total_xp = 0
        for i in range(1, level):
            total_xp += int(cls.BASE_XP_REQUIREMENT * (i ** cls.XP_MULTIPLIER))
        return total_xp
    
    @classmethod
    def calculate_level_from_xp(cls, xp: int) -> int:
        """XP로부터 레벨 계산"""
        level = 1
        total_xp = 0
        
        while True:
            next_level_xp = int(cls.BASE_XP_REQUIREMENT * (level ** cls.XP_MULTIPLIER))
            if total_xp + next_level_xp > xp:
                break
            total_xp += next_level_xp
            level += 1
            
        return level
    
    @classmethod
    def get_level_progress(cls, xp: int) -> tuple[int, int, int]:
        """
        현재 XP를 바탕으로 레벨 진행도 계산
        
        Returns:
            tuple: (현재 레벨, 현재 레벨 진행도, 다음 레벨까지 필요 XP)
        """
        current_level = cls.calculate_level_from_xp(xp)
        current_level_total_xp = cls.calculate_xp_for_level(current_level)
        next_level_total_xp = cls.calculate_xp_for_level(current_level + 1)
        
        current_level_progress = xp - current_level_total_xp
        xp_for_next_level = next_level_total_xp - current_level_total_xp
        
        return current_level, current_level_progress, xp_for_next_level
