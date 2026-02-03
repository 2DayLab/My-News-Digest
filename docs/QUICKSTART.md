# ⚡ 5분 빠른 시작 가이드

범용 뉴스 자동 요약 시스템을 5분 안에 설정하는 방법입니다.

---

## 📋 체크리스트

- [ ] **1분**: GitHub 레포지토리 생성
- [ ] **3분**: API 키 3개 발급
- [ ] **1분**: GitHub Secrets 등록
- [ ] **완료**: 첫 실행 테스트

---

## 1️⃣ GitHub 레포지토리 생성 (1분)

### 방법 A: Template 사용 (권장)

```
1. 이 레포지토리 페이지에서 "Use this template" 버튼 클릭
2. Repository name 입력 (예: my-news-digest)
3. Public 또는 Private 선택
4. "Create repository" 클릭
```

### 방법 B: Fork

```
1. "Fork" 버튼 클릭
2. 자신의 계정으로 Fork
```

---

## 2️⃣ API 키 발급 (3분)

### A. Gemini API 키 (1분)

**1. 발급 사이트 접속**
```
https://aistudio.google.com/app/apikey
```

**2. API 키 생성**
```
- "Create API Key" 버튼 클릭
- 프로젝트 선택 또는 새로 생성
- 생성된 키 복사
```

**3. 형식 확인**
```
✅ 올바른 형식: AIzaSyA1B2C3D4E5F6G7H8I9J0K...
❌ 잘못된 형식: AIza Sy... (공백 있음)
```

---

### B. 텔레그램 봇 토큰 (1분)

**1. BotFather 시작**
```
1. 텔레그램에서 @BotFather 검색
2. /start 입력
```

**2. 봇 생성**
```
/newbot 입력

Bot name? 
→ My News Bot (원하는 이름)

Bot username?
→ mynews_bot (고유한 이름, 반드시 _bot으로 끝나야 함)
```

**3. 토큰 복사**
```
Done! Your token:
1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ

✅ 이 토큰 전체를 복사하세요!
```

---

### C. Chat ID 확인 (1분)

#### 개인 사용 (개인에게 메시지 받기)

```
1. 텔레그램에서 @userinfobot 검색
2. /start 입력
3. "Id: 123456789" 복사
```

**형식:**
```
✅ 123456789 (양수)
❌ -123456789 (음수는 그룹용)
```

#### 그룹 사용 (그룹에 메시지 받기)

**방법 1: @getmyid_bot 사용**
```
1. 그룹 생성
2. 자신의 봇 추가 (@mynews_bot)
3. @getmyid_bot 추가
4. "This group's ID: -1001234567890" 복사
5. @getmyid_bot 제거 (선택)
```

**방법 2: API 사용**
```
1. 그룹에 봇 추가
2. 그룹에서 아무 메시지 전송
3. 브라우저에서 접속:
   https://api.telegram.org/bot<토큰>/getUpdates
   
4. 결과에서 "chat":{"id":-1001234567890} 찾기
5. -1001234567890 복사
```

**형식:**
```
✅ -1001234567890 (음수)
❌ 1001234567890 (양수는 개인용)
```

**중요: 봇 권한 설정 (그룹 사용 시)**
```
1. 그룹 설정 → 관리자
2. 봇을 관리자로 추가
3. "메시지 전송" 권한 부여
```

---

## 3️⃣ GitHub Secrets 등록 (1분)

### 접근 경로

```
GitHub 레포지토리 → Settings → Secrets and variables → Actions
```

### Secrets 등록 (3개)

**1. GEMINI_API_KEY**
```
1. "New repository secret" 클릭
2. Name: GEMINI_API_KEY
3. Secret: AIzaSy... (발급받은 Gemini API 키)
4. "Add secret" 클릭
```

**2. TELEGRAM_BOT_TOKEN**
```
1. "New repository secret" 클릭
2. Name: TELEGRAM_BOT_TOKEN
3. Secret: 1234567890:ABC... (봇 토큰 전체)
4. "Add secret" 클릭
```

**3. TELEGRAM_CHAT_ID**
```
1. "New repository secret" 클릭
2. Name: TELEGRAM_CHAT_ID
3. Secret: 123456789 (개인) 또는 -1001234567890 (그룹)
   ⚠️ 따옴표 없이 숫자만!
4. "Add secret" 클릭
```

### 등록 확인표

| Name | Value 예시 | 설명 |
|------|----------|------|
| `GEMINI_API_KEY` | `AIzaSyA1B2C...` | Gemini API 키 |
| `TELEGRAM_BOT_TOKEN` | `1234567890:ABC...` | 봇 토큰 전체 |
| `TELEGRAM_CHAT_ID` | `123456789` 또는 `-1001234567890` | 개인(양수) 또는 그룹(음수) |

---

## 4️⃣ RSS 피드 설정 (선택)

기본 설정(BBC, CNN)을 그대로 사용하거나 원하는 뉴스로 변경:

### 파일 수정

```
레포지토리에서 config.yaml 클릭 → 연필 아이콘(Edit) 클릭
```

### 예시: 한국 뉴스로 변경

```yaml
rss_feeds:
  - name: "연합뉴스"
    url: "https://www.yna.co.kr/rss/news.xml"
    enabled: true
    priority: 1
  
  - name: "조선일보"
    url: "https://www.chosun.com/arc/outboundfeeds/rss/"
    enabled: true
    priority: 2
```

### 예시: 기술 뉴스

```yaml
rss_feeds:
  - name: "TechCrunch"
    url: "https://techcrunch.com/feed/"
    enabled: true
    priority: 1
  
  - name: "The Verge"
    url: "https://www.theverge.com/rss/index.xml"
    enabled: true
    priority: 2
```

수정 후 "Commit changes" 클릭

---

## 5️⃣ 첫 실행 테스트 (1분)

### 수동 실행

```
1. Actions 탭 클릭
2. "범용 뉴스 자동 요약" 워크플로우 선택
3. "Run workflow" 드롭다운 클릭
4. "Run workflow" 버튼 클릭
```

### 실행 모니터링

```
1. 새로고침하여 실행 시작 확인
2. 실행 중인 워크플로우 클릭
3. "fetch-and-summarize" 클릭
4. 실시간 로그 확인
```

### 성공 확인

**로그에서 확인:**
```
✅ 환경 변수 검증 완료
✅ 총 N개 기사 수집 완료
✅ Gemini 요약 완료
✅ 전체 메시지 발송 완료 (N개 메시지)
🎉 전체 작업 성공! (소요: XX.X초)
```

**텔레그램에서 확인:**
```
봇으로부터 요약된 뉴스 메시지 수신
```

---

## 🎉 완료!

### 이제 자동으로 실행됩니다!

- ⏰ **매일 오전 8시** (한국 시간) 자동 실행
- 📱 **텔레그램**으로 자동 발송
- ⚙️ **서버 불필요** (GitHub Actions가 자동 실행)

---

## ⚙️ 실행 시간 변경 (선택)

기본값은 매일 오전 8시(KST)입니다. 변경하려면:

```
1. .github/workflows/daily-news.yml 파일 열기
2. schedule 섹션 수정:

schedule:
  - cron: '0 22 * * *'  # 한국 오전 7시
  - cron: '0 23 * * *'  # 한국 오전 8시 (기본값)
  - cron: '0 0 * * *'   # 한국 오전 9시

3. "Commit changes" 클릭
```

**도구:** https://crontab.guru/ (Cron 표현식 생성기)

---

## 🔧 문제 해결

### ❌ 텔레그램으로 메시지가 안 와요!

**확인 사항:**
```
1. 봇과 /start로 대화 시작했나요?
   → 텔레그램에서 @mynews_bot 검색 → /start

2. Chat ID가 맞나요?
   개인: 양수 (123456789)
   그룹: 음수 (-1001234567890)

3. GitHub Secrets가 정확한가요?
   Settings → Secrets → 3개 모두 등록 확인

4. Secret 이름이 정확한가요?
   ✅ GEMINI_API_KEY (대문자)
   ❌ gemini_api_key (소문자)
```

### ❌ "환경 변수 누락" 오류

```
1. GitHub → Settings → Secrets 재확인
2. Secret 이름 대소문자 정확히 확인
3. 값에 공백 없는지 확인
4. Secrets 삭제 후 재등록
```

### ❌ "수집된 기사가 없습니다"

```
1. config.yaml에서 시간 범위 확장:
   hours_threshold: 48  # 24 → 48시간

2. RSS URL이 정확한지 확인:
   브라우저에서 직접 열어보기

3. 주말/공휴일에는 새 기사 없을 수 있음
```

### ❌ Gemini API 오류

```
401 Unauthorized:
→ API 키 재확인
→ https://aistudio.google.com/app/apikey

429 Resource Exhausted:
→ 할당량 초과, 24시간 대기
→ 또는 실행 빈도 줄이기
```

---

## 📚 다음 단계

### 더 배우기

- **[전체 README](../README.md)** - 모든 기능 설명
- **[설정 가이드](CONFIGURATION.md)** - 고급 설정
- **[문제 해결](TROUBLESHOOTING.md)** - 상세 문제 해결

### 커스터마이징

- RSS 피드 추가/변경
- 실행 시간 변경
- 요약 개수 조정
- 언어 변경
- 프롬프트 커스터마이징

---

<p align="center">
  <strong>🎊 설정 완료!</strong><br>
  <strong>매일 아침 자동으로 뉴스를 받아보세요!</strong>
</p>

<p align="center">
  <a href="../README.md">← README로 돌아가기</a>
</p>
