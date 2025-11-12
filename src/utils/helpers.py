"""
유틸리티 함수 모듈
공통으로 사용되는 헬퍼 함수들
"""

import asyncio
import logging
import random
import time

import discord
from typing import Optional
from utils.config import Config
from collections import defaultdict
from datetime import datetime, timedelta

def create_embed(title: str, description: str = "", color: int = Config.COLORS['info']) -> discord.Embed:
    """공통 임베드 생성 함수"""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color
    )
    embed.set_footer(text="Siri Bot")
    return embed

def create_success_embed(title: str, description: str = "") -> discord.Embed:
    """성공 메시지용 임베드"""
    return create_embed(title, description, Config.COLORS['success'])

def create_error_embed(title: str, description: str = "") -> discord.Embed:
    """오류 메시지용 임베드"""
    return create_embed(title, description, Config.COLORS['error'])

def create_level_up_embed(user: discord.Member, old_level: int, new_level: int) -> discord.Embed:
    """레벨업 메시지용 임베드"""
    embed = discord.Embed(
        title="🎉 레벨업!",
        description=f"{user.mention}님이 레벨 {old_level} → {new_level}로 올랐습니다!",
        color=Config.COLORS['level_up']
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    return embed

def format_progress_bar(current: int, total: int, length: int = 10) -> str:
    """진행도 바 생성 (디스코드 이모지 사용, 10개 고정)"""
    if total == 0:
        percentage = 0
    else:
        percentage = min(current / total, 1.0)
    
    filled = int(length * percentage)
    
    # 디스코드 이모지를 사용한 프로그레스 바 (10개)
    filled_squares = "🟦" * filled
    empty_squares = "⬜" * (length - filled)
    
    percent = int(percentage * 100)
    
    return f"{filled_squares}{empty_squares} {percent}%"

def format_number(number: int) -> str:
    """숫자를 천 단위로 구분하여 포맷"""
    return f"{number:,}"

async def has_admin_permissions(member: discord.Member) -> bool:
    """관리자 권한 확인"""
    return member.guild_permissions.administrator

def get_role_by_id(guild: discord.Guild, role_id: int) -> Optional[discord.Role]:
    """역할 ID로 역할 객체 조회"""
    return guild.get_role(role_id)

def calculate_percentage(current: int, total: int) -> int:
    """퍼센트 계산"""
    if total == 0:
        return 0
    return min(int((current / total) * 100), 100)

class RateLimiter:
    """간단한 레이트 리미터"""
    
    def __init__(self, max_calls: int, period: int):
        self.max_calls = max_calls
        self.period = period  # 초 단위
        self.calls = defaultdict(list)
    
    def is_allowed(self, user_id: int) -> bool:
        """사용자가 명령을 실행할 수 있는지 확인"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.period)
        
        # 오래된 기록 제거
        self.calls[user_id] = [
            call_time for call_time in self.calls[user_id]
            if call_time > cutoff
        ]
        
        # 제한 확인
        if len(self.calls[user_id]) >= self.max_calls:
            return False
        
        # 기록 추가
        self.calls[user_id].append(now)
        return True


class MessageCleanupManager:
    """봇이 보낸 메시지를 일정 시간 후 일괄 삭제"""

    def __init__(
        self,
        delay_seconds: float = 30.0,
        jitter_seconds: float = 3.0,
        min_interval: float = 0.4,
    ):
        self.delay_seconds = delay_seconds
        self.jitter_seconds = max(0.0, jitter_seconds)
        self.min_interval = max(0.0, min_interval)
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._worker: asyncio.Task | None = None
        self._stopped = False
        self._logger = logging.getLogger("Siri.MessageCleanup")
        self._persistent_ids: set[int] = {1372750739478282341}
        self._skip_ids: set[int] = set(self._persistent_ids)

    def start(self) -> None:
        if self._worker and not self._worker.done():
            return
        self._stopped = False
        self._worker = asyncio.create_task(self._worker_loop(), name="siri-message-cleanup")

    def schedule(self, message: discord.Message, delay: float | None = None) -> None:
        if self._stopped:
            return

        if self.should_skip(message):
            return

        delay_value = self.delay_seconds if delay is None else max(0.0, delay)
        run_at = time.monotonic() + delay_value
        if self.jitter_seconds > 0.0:
            run_at += random.uniform(0, self.jitter_seconds)

        try:
            self._queue.put_nowait((run_at, message))
        except asyncio.QueueFull:
            self._logger.warning("메시지 삭제 큐가 가득 찼습니다 - 메시지를 건너뜁니다")
            return

        if self._worker is None or self._worker.done():
            self.start()

    async def shutdown(self) -> None:
        self._stopped = True
        if self._worker:
            self._worker.cancel()
            try:
                await self._worker
            except asyncio.CancelledError:
                pass
            self._worker = None

        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break

        self._skip_ids = set(self._persistent_ids)

    def mark_persistent(self, message: discord.Message) -> None:
        setattr(message, "_siri_skip_cleanup", True)
        self._persistent_ids.add(message.id)
        self._skip_ids.add(message.id)

    def should_skip(self, message: discord.Message) -> bool:
        return bool(
            getattr(message, "_siri_skip_cleanup", False)
            or message.id in self._skip_ids
            or message.id in self._persistent_ids
        )

    async def _worker_loop(self) -> None:
        try:
            while not self._stopped:
                run_at, message = await self._queue.get()
                wait_for = run_at - time.monotonic()
                if wait_for > 0:
                    try:
                        await asyncio.sleep(wait_for)
                    except asyncio.CancelledError:
                        self._queue.task_done()
                        raise

                if self._stopped:
                    self._queue.task_done()
                    break

                try:
                    if self.should_skip(message):
                        continue

                    await message.delete()
                except (discord.NotFound, discord.Forbidden):
                    pass
                except discord.HTTPException as exc:
                    if exc.status == 429:
                        # 재시도 스케줄링 (속도 제한)
                        self.schedule(message, delay=5.0)
                    else:
                        self._logger.warning("메시지 삭제 실패 (%s): %s", message.id, exc)
                finally:
                    if message.id not in self._persistent_ids:
                        self._skip_ids.discard(message.id)
                    self._queue.task_done()

                if self.min_interval > 0:
                    await asyncio.sleep(self.min_interval)
        except asyncio.CancelledError:
            raise
