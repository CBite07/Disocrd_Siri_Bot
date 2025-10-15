"""
GPT 봇 API 클라이언트
Siri 봇에서 GPT 봇의 API를 호출하기 위한 모듈
"""

import logging
import aiohttp
from typing import Optional, Dict, Any

from utils.config import Config

logger = logging.getLogger(__name__)


class GPTBotClient:
    """GPT 봇 API 클라이언트"""
    
    def __init__(self):
        self.host = Config.get_gpt_api_host()
        self.port = Config.get_gpt_api_port()
        self.base_url = f"http://{self.host}:{self.port}"
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def health_check(self) -> bool:
        """GPT 봇 서버 상태 확인"""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/health") as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("bot_ready", False)
                    return False
        except Exception as e:
            logger.warning(f"GPT 봇 헬스 체크 실패: {e}")
            return False
    
    async def play_music(
        self,
        query: str,
        guild_id: int,
        channel_id: int,
        user: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        GPT 봇에게 음악 재생 요청
        
        Args:
            query: 검색어 또는 URL
            guild_id: 디스코드 서버 ID
            channel_id: 음성 채널 ID
            user: 요청한 사용자 이름
            
        Returns:
            응답 딕셔너리 {"status": "playing/error", ...}
        """
        try:
            payload = {
                "query": query,
                "guild_id": guild_id,
                "channel_id": channel_id,
                "user": user
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/play",
                    json=payload
                ) as response:
                    data = await response.json()
                    
                    if response.status != 200:
                        logger.error(f"GPT 봇 재생 요청 실패: {data}")
                    
                    return data
                    
        except aiohttp.ClientError as e:
            logger.error(f"GPT 봇 통신 오류: {e}")
            return {
                "status": "error",
                "message": f"GPT 봇과 통신할 수 없습니다. 봇이 실행 중인지 확인하세요."
            }
        except Exception as e:
            logger.error(f"예상치 못한 오류: {e}")
            return {
                "status": "error",
                "message": f"오류가 발생했습니다: {str(e)}"
            }
    
    async def stop_music(self, guild_id: int) -> Dict[str, Any]:
        """
        GPT 봇에게 음악 정지 요청
        
        Args:
            guild_id: 디스코드 서버 ID
            
        Returns:
            응답 딕셔너리
        """
        try:
            payload = {"guild_id": guild_id}
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/stop",
                    json=payload
                ) as response:
                    return await response.json()
                    
        except Exception as e:
            logger.error(f"GPT 봇 정지 요청 오류: {e}")
            return {
                "status": "error",
                "message": f"정지 요청 실패: {str(e)}"
            }


# 전역 클라이언트 인스턴스
gpt_client = GPTBotClient()
