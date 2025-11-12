"""
데이터베이스 관리 모듈
SQLite를 사용한 사용자 데이터 관리
확장 가능한 구조로 설계
"""

import asyncio
import sqlite3
import aiosqlite
import logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseManager:
    """데이터베이스 관리 클래스"""

    def __init__(self, db_path: str):
        self.db_path = db_path

    async def init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # users 테이블 생성
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id INTEGER NOT NULL,
                        guild_id INTEGER NOT NULL,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 1,
                        last_attendance TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, guild_id)
                    )
                """
                )

                # 인덱스 생성 (성능 최적화)
                await db.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_users_guild_level 
                    ON users(guild_id, level DESC)
                """
                )

                await db.commit()
                logger.info("데이터베이스 초기화 완료")

        except Exception as e:
            logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    async def get_user_data(
        self, user_id: int, guild_id: int
    ) -> Optional[Dict[str, Any]]:
        """사용자 데이터 조회"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                cursor = await db.execute(
                    """
                    SELECT * FROM users 
                    WHERE user_id = ? AND guild_id = ?
                """,
                    (user_id, guild_id),
                )

                row = await cursor.fetchone()
                return dict(row) if row else None

        except Exception as e:
            logger.error(f"사용자 데이터 조회 실패: {e}")
            return None

    async def create_user(self, user_id: int, guild_id: int) -> bool:
        """새 사용자 생성"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT OR IGNORE INTO users (user_id, guild_id, xp, level)
                    VALUES (?, ?, 0, 1)
                """,
                    (user_id, guild_id),
                )

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"사용자 생성 실패: {e}")
            return False

    async def update_user_xp(self, user_id: int, guild_id: int, xp_change: int) -> bool:
        """사용자 XP 업데이트"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 현재 XP 조회
                cursor = await db.execute(
                    """
                    SELECT xp FROM users 
                    WHERE user_id = ? AND guild_id = ?
                """,
                    (user_id, guild_id),
                )

                row = await cursor.fetchone()
                if not row:
                    return False

                from utils.config import Config

                new_xp = max(0, row[0] + xp_change)  # XP는 0 이하로 떨어지지 않음
                new_xp = min(new_xp, Config.MAX_XP)

                await db.execute(
                    """
                    UPDATE users 
                    SET xp = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ?
                """,
                    (new_xp, user_id, guild_id),
                )

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"XP 업데이트 실패: {e}")
            return False

    async def update_attendance(
        self, user_id: int, guild_id: int, xp_gain: int
    ) -> tuple[bool, int, int]:
        """
        출석 체크 처리
        KST(한국 표준시) 오전 7시를 기준으로 날짜 계산

        Returns:
            tuple: (성공 여부, 이전 레벨, 새 레벨)
        """
        try:
            # KST는 UTC+9이므로, UTC에서 9시간을 더한 후 다시 7시간을 빼서 계산
            # 즉, KST 오전 7시 = UTC+2시간 기준으로 날짜 전환
            # 예: UTC 2025-01-01 22:00 (KST 2025-01-02 07:00) -> 게임 날짜 2025-01-02
            #     UTC 2025-01-01 21:59 (KST 2025-01-02 06:59) -> 게임 날짜 2025-01-01
            utc_now = datetime.now(timezone.utc)
            kst_time = utc_now + timedelta(hours=9)  # KST = UTC+9
            # KST 오전 7시 기준으로 날짜 전환을 위해 7시간을 빼고 날짜만 추출
            game_reference_time = kst_time - timedelta(hours=7)
            today = game_reference_time.date().isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                # 사용자 데이터 조회
                cursor = await db.execute(
                    """
                    SELECT xp, level, last_attendance FROM users 
                    WHERE user_id = ? AND guild_id = ?
                """,
                    (user_id, guild_id),
                )

                row = await cursor.fetchone()
                if not row:
                    return False, 0, 0

                current_xp, old_level, last_attendance = row

                # 이미 오늘 출석했는지 확인
                if last_attendance == today:
                    return False, old_level, old_level

                # XP 업데이트 및 출석일 기록
                from utils.config import Config

                new_xp = min(current_xp + xp_gain, Config.MAX_XP)

                await db.execute(
                    """
                    UPDATE users 
                    SET xp = ?, last_attendance = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ?
                """,
                    (new_xp, today, user_id, guild_id),
                )

                # 새 레벨 계산
                from utils.config import Config

                new_level = Config.calculate_level_from_xp(new_xp)

                # 레벨 업데이트 (필요한 경우)
                if new_level != old_level:
                    await db.execute(
                        """
                        UPDATE users 
                        SET level = ?
                        WHERE user_id = ? AND guild_id = ?
                    """,
                        (new_level, user_id, guild_id),
                    )

                await db.commit()
                return True, old_level, new_level

        except Exception as e:
            logger.error(f"출석 체크 실패: {e}")
            return False, 0, 0

    async def get_leaderboard(
        self, guild_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """리더보드 데이터 조회"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row

                cursor = await db.execute(
                    """
                    SELECT user_id, level, xp 
                    FROM users 
                    WHERE guild_id = ?
                    ORDER BY level DESC, xp DESC
                    LIMIT ?
                """,
                    (guild_id, limit),
                )

                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"리더보드 조회 실패: {e}")
            return []

    async def reset_user_data(self, user_id: int, guild_id: int) -> bool:
        """사용자 데이터 초기화"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    UPDATE users 
                    SET xp = 0, level = 1, last_attendance = NULL, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ?
                """,
                    (user_id, guild_id),
                )

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"사용자 데이터 초기화 실패: {e}")
            return False

    async def set_user_xp(self, user_id: int, guild_id: int, new_xp: int) -> bool:
        """사용자 XP 직접 설정 (관리자용)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                from utils.config import Config

                new_level = Config.calculate_level_from_xp(new_xp)

                safe_xp = min(max(new_xp, 0), Config.MAX_XP)

                await db.execute(
                    """
                    UPDATE users 
                    SET xp = ?, level = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ?
                """,
                    (safe_xp, new_level, user_id, guild_id),
                )

                await db.commit()
                return True

        except Exception as e:
            logger.error(f"XP 설정 실패: {e}")
            return False

    async def close(self):
        """데이터베이스 연결 정리"""
        # SQLite는 연결을 매번 열고 닫기 때문에 특별한 정리가 필요없음
        logger.info("데이터베이스 연결 정리 완료")

    async def get_schema_version(self) -> int:
        """현재 데이터베이스 스키마 버전 확인"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                await conn.commit()
                cursor = await conn.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except:
            return 0

    async def migrate_schema(self):
        """스키마 마이그레이션 실행"""
        current_version = await self.get_schema_version()

        # 버전 1: schema_version 테이블 생성
        if current_version < 1:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """
                )
                await conn.execute("INSERT INTO schema_version (version) VALUES (1)")
                await conn.commit()
                logger.info("스키마 버전 1 적용 완료")

    async def backup_database(self) -> str:
        """
        데이터베이스 백업 생성

        Returns:
            백업 파일 경로
        """
        try:
            source_path = Path(self.db_path).resolve()

            if not source_path.exists():
                raise FileNotFoundError(
                    f"데이터베이스 파일을 찾을 수 없습니다: {source_path}"
                )

            backup_dir = source_path.parent / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"siri_bot_backup_{timestamp}.db"

            def _backup_sqlite() -> None:
                with sqlite3.connect(source_path, timeout=30) as source_conn:
                    source_conn.execute("PRAGMA busy_timeout = 30000")
                    source_conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                    with sqlite3.connect(backup_path) as dest_conn:
                        source_conn.backup(dest_conn, pages=100, progress=None)

            await asyncio.to_thread(_backup_sqlite)

            logger.info(f"데이터베이스 백업 완료: {backup_path}")
            return str(backup_path)

        except Exception as e:
            logger.error(f"데이터베이스 백업 실패: {e}")
            raise

    async def cleanup_old_backups(self, keep_days: int = 30):
        """오래된 백업 파일 정리"""
        try:
            backup_dir = Path(self.db_path).parent / "backups"
            if not backup_dir.exists():
                return

            cutoff_time = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            deleted_count = 0

            for backup_file in backup_dir.glob("siri_bot_backup_*.db"):
                if backup_file.stat().st_mtime < cutoff_time:
                    backup_file.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"{deleted_count}개의 오래된 백업 파일 삭제")

        except Exception as e:
            logger.error(f"백업 정리 중 오류: {e}")
