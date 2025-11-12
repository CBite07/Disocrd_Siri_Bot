<p align="center">
  <a href="https://github.com/CBite07/Disocrd_Siri_Bot">
    <img src="./DiscordSiri/assets/Union.svg" width="160" alt="Siri Bot Logo" />
  </a>
</p>

<p align="center">
  <a href="https://discord.gg/G9NAJzpxEM"><img alt="Discord" src="https://img.shields.io/badge/Discord-Join-5865F2?style=for-the-badge&logo=discord&logoColor=white"></a>
  <a href="https://www.youtube.com/@FCPUG"><img alt="YouTube" src="https://img.shields.io/badge/YouTube-FCPUG-FF0000?style=for-the-badge&logo=youtube&logoColor=white"></a>
  <a href="https://github.com/CBite07/Disocrd_Siri_Bot"><img alt="GitHub" src="https://img.shields.io/badge/GitHub-Repo-2b2b2b?style=for-the-badge&logo=github&logoColor=white"></a>
</p>

---

## 1. 개요 및 목표

-   **프로젝트명**: `Siri Bot`
-   **목표**: 디스코드 서버 내 커뮤니티 활성화를 위한 다기능 봇 개발. 출석 체크를 통한 XP 획득, 레벨링, 역할 부여 시스템을 통해 사용자의 지속적인 참여를 유도.
-   **핵심 철학**: "소프트 코딩"을 지향하여, 향후 기능 확장이 용이한 모듈식 구조로 설계. **50년 이상** 운영 가능한 장기 프로젝트를 목표로 함.

---

## 2. 핵심 기능 명세

### 2.1. 출석 체크 및 레벨링 시스템

> **사용자 스토리:**  
> 서버 멤버로서, 채팅창에 `ㅊㅊ`를 입력하여 매일 출석 체크를 하고 싶다. 이를 통해 XP를 얻고 레벨을 올리는 재미를 느끼고 싶다.  
> `/내정보` 명령어로 현재 레벨과 다음 레벨까지의 진행도를 확인하고 싶다.  
> 레벨이 오르면 서버에서 정해진 역할을 자동으로 부여받고 싶다.

#### 출석 체크 시스템

-   **트리거**: 채팅창에 `ㅊㅊ` 메시지 전송
-   **초기화 시간**: **매일 KST(한국 표준시) 오전 7시** 기준으로 출석 체크 초기화
-   **쿨다운**: 1일 1회 (오전 7시 이후 첫 출석부터 다음날 오전 7시까지 재출석 불가)
-   **피드백**:
    -   ✅ **성공**: 출석 완료 시 메시지에 ✅ 이모지 반응
    -   ❌ **실패**: 중복 출석 시 메시지에 ❌ 이모지 반응 및 안내 메시지
-   **보상**: 출석 시 XP 획득

#### XP 및 레벨 시스템

-   **XP 표시**: 총 경험치는 `/내정보` 명령어로 확인 가능
-   **레벨 진행도**: 다음 레벨까지의 진행도를 프로그레스 바(%)로 시각화
-   **난이도 설계**: 레벨업에 필요한 XP가 기하급수적으로 증가하여 장기 프로젝트 지향
-   **XP 공식**: `다음 레벨 필요 XP = 100 * (현재 레벨 ^ 1.5)`
    > _공식은 게임 밸런스에 따라 조정 가능_

#### 역할 자동 부여

-   레벨 달성 시 자동으로 해당 역할 부여 및 이전 레벨 역할 제거
-   **제약사항**: 봇보다 높은 권한을 가진 관리자에게는 역할을 부여할 수 없으며, 이 경우 로그에만 기록

#### 관련 명령어

-   `/내정보` - 현재 레벨, 경험치, 진행도 확인

### 2.2. 리더보드 시스템

> **사용자 스토리:**  
> 서버 멤버로서, 서버 내 다른 유저들의 레벨 순위를 확인하고 싶다.  
> 이를 통해 건전한 경쟁심을 느끼고 더 적극적으로 활동하고 싶다.

#### 기능

-   서버 내 유저들의 레벨 순위를 **상위 10명**까지 표시
-   표시 정보: 순위, 유저 이름(닉네임), 레벨, 총 경험치
-   실시간 순위 반영

#### 관련 명령어

-   `/리더보드` - 서버 레벨 순위 확인

### 2.3. 규칙 관리 시스템

> **사용자 스토리:**  
> 서버 관리자로서, 봇을 사용해 깔끔하게 정리된 형식의 규칙을 특정 채널에 임베드 형태로 게시하고 싶다.

#### 기능

-   **규칙 데이터**: `data/rules.json` 파일에서 규칙 내용을 읽어와 임베드로 표시
-   **메시지 관리**: 기존 봇 메시지를 삭제하고 새로운 규칙 임베드 게시
-   **수정 방법**: JSON 파일을 직접 수정한 후 `/규칙` 명령어를 다시 실행하여 업데이트
-   **권한**: 관리자 전용

#### 규칙 파일 구조 (`data/rules.json`)

```json
{
    "title": "📋 서버 규칙",
    "color": 3447003,
    "rules": [
        "1️⃣ 첫 번째 규칙",
        "2️⃣ 두 번째 규칙",
        "3️⃣ 세 번째 규칙"
    ],
    "footer": "Siri Bot",
    "last_updated": "2025-01-01"
}
```

#### 관련 명령어

-   `/규칙 [채널]` - 지정한 채널(또는 현재 채널)에 규칙 게시

### 2.4. 관리자 기능

> **사용자 스토리:**  
> 서버 관리자로서, 특정 유저의 레벨을 조정하거나 데이터를 초기화하고 싶다.  
> 이벤트 보상 지급이나 문제 발생 시 신속한 대응을 위함.

#### 데이터 관리

-   **레벨 설정**: 특정 유저의 레벨을 직접 설정 (XP도 자동 계산되어 설정됨)
-   **데이터 초기화**: 유저 데이터를 레벨 1, XP 0으로 초기화
-   **안전 장치**: 데이터 초기화 시 확인 버튼을 통한 2단계 검증

#### 봇 관리 (개발자 전용)

-   **명령어 목록**: 등록된 모든 슬래시 명령어 확인
-   **봇 상태**: 핑, 업타임, 메모리 사용량 등 확인
-   **데이터베이스 백업**: 수동 백업 실행

#### 관련 명령어

**관리자 전용:**
-   `/레벨설정 [유저] [레벨]` - 특정 유저의 레벨 설정
-   `/데이터초기화 [유저]` - 특정 유저의 데이터 초기화

**개발자 전용:**
-   `/명령어목록` - 등록된 명령어 목록 확인
-   `/상태` - 봇 상태 및 통계 확인

### 2.5. 음악 재생 시스템 (제거됨)

> **중요**: YouTube의 보안 강화로 인해 음악 재생 기능이 제거되었습니다.
> 음악 재생이 필요한 경우 전용 음악 봇(예: Rythm, Groovy 대체 봇)을 사용하는 것을 권장합니다.

**제거 사유:**
- YouTube의 "Sign in to confirm you're not a bot" 보안 강화
- PO Token, 쿠키, bgutil 등 모든 우회 방법 실패
- 장기 운영에 불안정성 증가

**대안:**
- [Lavalink](https://github.com/lavalink-devs/Lavalink) 기반 음악 봇 사용
- [Music Bot](https://github.com/jagrosh/MusicBot) 등 전용 봇 활용
- Discord 프리미엄의 Go Live 기능 활용

### 2.6. TTS (Text-to-Speech) 기능

> 음성 채널에 봇을 초대하여 인사말을 들을 수 있습니다.

#### 기능

-   GoogleTTS(gTTS) 기반 음성 변환
-   음성 채널 자동 참여 기능 (관리자 설정)
-   사용자 입장 시 자동 인사
-   다국어 지원 (한국어 기본)

#### 시스템 요구사항

-   **필수**: `ffmpeg` (오디오 처리 및 인코딩)
-   **Python 패키지**: `gtts`

#### 설치 방법

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Python 패키지
pip install gtts
```

#### 관련 명령어

-   `/자동참여 [ON/OFF]` - 자동 참여 모드 설정 (관리자 전용)
-   `/시리야` - 봇을 음성 채널에 입장시킴
-   `/퇴장해` - 봇을 음성 채널에서 퇴장시킴


## 3. 기술 설계 및 데이터베이스

-   **라이브러리**: `discord.py`
-   **구조**: `Cogs`를 활용한 모듈식 구조. 각 기능(출석, 리더보드 등)을 별도의 파일로 분리하여 유지보수와 기능 확장 용이성 확보.
-   **데이터베이스**:
    -   **초기**: `SQLite` 사용 권장 (파일 기반으로 초기 개발 및 테스트에 편리).
    -   **장기**: 프로젝트 확장 시 `PostgreSQL` 또는 `MySQL` 같은 전문 데이터베이스로 마이그레이션 고려.
-   **데이터 모델 (테이블 구조 예시)**:
    -   `users` 테이블:
        -   `user_id` (INTEGER, PRIMARY KEY): 유저의 고유 디스코드 ID
        -   `guild_id` (INTEGER): 서버(길드)의 고유 ID
        -   `xp` (INTEGER, DEFAULT 0): 현재 경험치
        -   `level` (INTEGER, DEFAULT 1): 현재 레벨
        -   `last_attendance` (TEXT): 마지막 출석체크 날짜 (YYYY-MM-DD 형식)

---

## 4. 레벨 및 역할 부여 계획

아래 표는 레벨에 따른 역할 부여 계획입니다. (레벨 구간은 논의 후 조정 가능)

| 레벨 구간 | 역할 이름     | 역할 ID             |
| :-------- | :------------ | :------------------ |
| `1 - 9`   | 초보자        | `1392422549174091868` |
| `10 - 19` | 입문자        | `1392431487697293465` |
| `20 - 29` | 숙련자        | `1392431532592857182` |
| `30 - 39` | 전문가        | `1392431564574687323` |
| `40 - 49` | 마스터        | `1392431591304990730` |
| `50 - 69` | 그랜드마스터  | `1392431665376264192` |
| `70+`     | 레전드        | `1392431727292448922` |

---

## 5. 설치 및 실행 방법

### 5.1. 사전 준비

1. **Python 3.10 이상** 설치
2. **Discord Bot 토큰** 발급
   - [Discord Developer Portal](https://discord.com/developers/applications)에서 애플리케이션 생성
   - Bot 메뉴에서 토큰 발급
   - OAuth2 > URL Generator에서 `bot`, `applications.commands` 권한 선택 후 초대 URL 생성

3. **시스템 의존성** (TTS 기능 사용 시)
   ```bash
   # macOS
   brew install ffmpeg
   
   # Ubuntu/Debian
   sudo apt-get install ffmpeg
   ```

### 5.2. 설치

```bash
# 1. 저장소 클론
git clone https://github.com/CBite07/Disocrd_Siri_Bot.git
cd Disocrd_Siri_Bot/DiscordSiri

# 2. 가상환경 생성 및 활성화 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r src/requirements.txt
```

### 5.3. 환경 설정

`.env` 파일 생성:

```env
# Discord Bot 토큰
DISCORD_BOT_TOKEN=your_bot_token_here

# 명령어 접두사 (슬래시 명령어 사용 시 필요 없음)
COMMAND_PREFIX=!

# 데이터베이스 경로 (선택사항, 기본값 사용 가능)
DATABASE_PATH=./siri_bot.db
```

### 5.4. 실행

```bash
cd src
python main.py
```

또는 run.py 사용:

```bash
python run.py
```

### 5.5. 봇 초대

1. Discord Developer Portal에서 생성한 초대 URL 사용
2. 필요한 권한:
   - 메시지 읽기/보내기
   - 임베드 링크
   - 반응 추가
   - 역할 관리
   - 음성 채널 연결 및 말하기 (TTS 기능 사용 시)

---

## 6. 프로젝트 구조

```
DiscordSiri/
├── src/
│   ├── main.py              # 봇 메인 진입점
│   ├── run.py               # 실행 스크립트
│   ├── requirements.txt     # Python 의존성
│   ├── cogs/                # 기능별 모듈
│   │   ├── attendance.py    # 출석 체크 시스템
│   │   ├── leaderboard.py   # 리더보드
│   │   ├── announcement.py  # 규칙 관리
│   │   ├── admin.py         # 관리자 기능
│   │   └── voice.py         # TTS 기능
│   ├── utils/               # 유틸리티
│   │   ├── config.py        # 설정 및 상수
│   │   ├── database.py      # 데이터베이스 관리
│   │   └── helpers.py       # 헬퍼 함수
│   └── data/
│       └── rules.json       # 규칙 데이터
├── assets/                  # 이미지 등 리소스
└── pyproject.toml          # 프로젝트 메타데이터
```

---

## 7. 명령어 목록

### 일반 사용자

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `ㅊㅊ` | 출석 체크 (채팅 메시지) | 채팅창에 `ㅊㅊ` 입력 |
| `/내정보` | 레벨 및 경험치 확인 | `/내정보` |
| `/리더보드` | 서버 순위 확인 | `/리더보드` |

### 관리자 전용

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/규칙 [채널]` | 규칙 게시 | `/규칙 #규칙` |
| `/레벨설정 [유저] [레벨]` | 유저 레벨 설정 | `/레벨설정 @유저 50` |
| `/데이터초기화 [유저]` | 유저 데이터 초기화 | `/데이터초기화 @유저` |

### 음성 기능

| 명령어 | 설명 | 예시 |
|--------|------|------|
| `/자동참여 [ON/OFF]` | 자동 참여 모드 설정 (관리자) | `/자동참여 ON` |
| `/시리야` | 봇을 음성 채널에 입장 | `/시리야` |
| `/퇴장해` | 봇을 음성 채널에서 퇴장 | `/퇴장해` |

### 개발자 전용

| 명령어 | 설명 |
|--------|------|
| `/명령어목록` | 등록된 명령어 확인 |
| `/상태` | 봇 상태 및 통계 |
| `/백업` | 데이터베이스 백업 |

---

## 8. 개발 로드맵

### ✅ 완료된 기능

-   [x] 출석 체크 시스템 (KST 오전 7시 기준)
-   [x] 레벨링 및 XP 시스템
-   [x] 역할 자동 부여
-   [x] 리더보드
-   [x] 규칙 관리 시스템
-   [x] 관리자 데이터 관리 기능
-   [x] TTS 기능
-   [x] 데이터베이스 백업 시스템

### 🚧 개발 예정

-   [ ] 출석 연속 달성 보너스 시스템
-   [ ] 주간/월간 통계
-   [ ] 업적 시스템
-   [ ] 이벤트 시스템
-   [ ] 웹 대시보드

---

## 9. 기여 및 라이선스

### 기여 방법

1. 이 저장소를 Fork합니다
2. 새 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 Push합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

### 문의

-   Discord: [FCPUG 서버](https://discord.gg/G9NAJzpxEM)
-   GitHub Issues: [버그 리포트 및 제안](https://github.com/CBite07/Disocrd_Siri_Bot/issues)
