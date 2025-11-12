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
    def get_database_path() -> str:
        return os.getenv("DATABASE_PATH", "./src/data/siri_bot.db")

    @staticmethod
    def get_command_prefix() -> str:
        return os.getenv("COMMAND_PREFIX", "!")

    @staticmethod
    def get_ffmpeg_path() -> str:
        """FFmpeg 실행 파일 경로 (TTS 음성 알림에 사용)"""
        return os.getenv("FFMPEG_PATH", "ffmpeg")

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
        "success": 0x00FF00,  # 초록색
        "error": 0xFF0000,  # 빨간색
        "info": 0x3498DB,  # 파란색
        "warning": 0xFFA500,  # 주황색
        "level_up": 0xFFD700,  # 골드색
    }

    # 레벨별 역할 매핑
    # 레벨 구간: (시작 레벨, 끝 레벨, 역할 ID)
    ROLE_LEVELS = {
        (1, 9): 1392422549174091868,  # 초보자
        (10, 19): 1392431487697293465,  # 입문자
        (20, 29): 1392431532592857182,  # 숙련자
        (30, 39): 1392431564574687323,  # 전문가
        (40, 49): 1392431591304990730,  # 마스터
        (50, 69): 1392431665376264192,  # 그랜드마스터
        (70, 999): 1392431727292448922,  # 레전드 (70레벨 이상)
    }

    # 백업 설정
    BACKUP_ENABLED = True
    BACKUP_RETENTION_DAYS = 30  # 30일간 백업 보관
    BACKUP_HOUR = 3  # 백업 시간 (새벽 3시)

    # 성능 및 안정성 설정
    MAX_LEVEL = 100  # 최대 레벨 제한
    DATABASE_POOL_SIZE = 10  # 향후 확장 시

    # 레이트 리밋 설정 (남용 방지)
    COMMAND_COOLDOWN = 3  # 일반 명령어 쿨다운 (초)
    ATTENDANCE_COOLDOWN = 24 * 60 * 60  # 출석 쿨다운 (24시간)

    # 저장 가능한 XP 한도 (SQLite INTEGER 최대값 보호)
    MAX_XP = 9_000_000_000_000_000_000  # 9e18, signed 64bit 안전 영역

    @classmethod
    def get_role_for_level(cls, level: int) -> int | None:
        """레벨에 맞는 역할 ID 반환"""
        for (min_level, max_level), role_id in cls.ROLE_LEVELS.items():
            if min_level <= level <= max_level:
                return role_id
        return None

    @classmethod
    def calculate_xp_for_level(cls, level: int) -> int:
        """특정 레벨 달성에 필요한 총 XP 계산 (수정됨)"""
        if level <= 1:
            return 0

        if level > cls.MAX_LEVEL:
            level = cls.MAX_LEVEL

        total_xp = 0
        for i in range(1, min(level, cls.MAX_LEVEL)):
            # i 레벨에서 i+1 레벨로 가는데 필요한 XP
            total_xp += int(cls.BASE_XP_REQUIREMENT * (cls.XP_MULTIPLIER ** (i - 1)))
            if total_xp >= cls.MAX_XP:
                return cls.MAX_XP
        return min(total_xp, cls.MAX_XP)

    @classmethod
    def calculate_level_from_xp(cls, xp: int) -> int:
        """XP로부터 레벨 계산 (수정됨)"""
        if xp < 0:
            return 1
        xp = min(xp, cls.MAX_XP)
        if xp >= cls.MAX_XP:
            return cls.MAX_LEVEL

        level = 1
        accumulated_xp = 0

        while level < cls.MAX_LEVEL:
            # 현재 레벨에서 다음 레벨로 가는데 필요한 XP
            xp_needed = min(
                int(cls.BASE_XP_REQUIREMENT * (cls.XP_MULTIPLIER ** (level - 1))),
                cls.MAX_XP,
            )

            if accumulated_xp + xp_needed > xp:
                break

            accumulated_xp += xp_needed
            if accumulated_xp >= cls.MAX_XP:
                return cls.MAX_LEVEL
            level += 1

        return min(level, cls.MAX_LEVEL)

    @classmethod
    def get_level_progress(cls, xp: int) -> tuple[int, int, int]:
        """
        현재 XP를 바탕으로 레벨 진행도 계산 (수정됨)

        Returns:
            tuple: (현재 레벨, 현재 레벨 진행도, 다음 레벨까지 필요 XP)
        """
        current_level = cls.calculate_level_from_xp(xp)
        current_level_total_xp = cls.calculate_xp_for_level(current_level)
        if current_level >= cls.MAX_LEVEL:
            return current_level, 0, 0

        next_level_total_xp = cls.calculate_xp_for_level(current_level + 1)

        current_level_progress = xp - current_level_total_xp
        xp_for_next_level = next_level_total_xp - current_level_total_xp

        return current_level, current_level_progress, xp_for_next_level
