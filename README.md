# 📰 범용 뉴스 자동 요약 시스템

> **모든 RSS 피드를 지원하는 완전 자동화 뉴스 요약 시스템**  
> AI 기반 · 텔레그램 발송 · GitHub Actions 자동 실행

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4)](https://ai.google.dev/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4)](https://core.telegram.org/bots)

---

## ✨ 특징

- 🌍 **범용 지원**: 국가, 언어, 주제 제한 없이 모든 RSS 피드 사용 가능
- 🤖 **AI 자동 요약**: Google Gemini가 핵심 뉴스만 선별 및 요약
- 📱 **텔레그램 발송**: 매일 자동으로 요약된 뉴스를 텔레그램으로 수신
- ⚙️ **완전 자동화**: GitHub Actions로 서버 없이 자동 실행
- 💰 **완전 무료**: Gemini API + GitHub Actions + 텔레그램 (월 $0)
- 🎨 **쉬운 커스터마이징**: `config.yaml` 파일만 수정하면 모든 설정 변경

---

## 📋 목차

- [시작하기](#시작하기)
- [사용 예시](#사용-예시)
- [상세 설명](#상세-설명)
- [커스터마이징](#커스터마이징)
- [문제 해결](#문제-해결)
- [FAQ](#faq)
- [라이선스](#라이선스)

---

## 🚀 시작하기

### 1단계: 레포지토리 생성

**방법 A: 템플릿 사용 (권장)**
```
1. 이 레포지토리에서 "Use this template" 클릭
2. 레포지토리 이름 입력
3. Public 또는 Private 선택
4. "Create repository" 클릭
```

**방법 B: Fork**
```
1. "Fork" 버튼 클릭
2. 자신의 계정으로 Fork
```

### 2단계: API 키 발급 (3분)

#### Gemini API 키
```
1. https://aistudio.google.com/app/apikey 접속
2. "Create API Key" 클릭
3. 생성된 키 복사 (AIzaSy...)
```

#### 텔레그램 봇 생성
```
1. 텔레그램에서 @BotFather 검색
2. /newbot 입력
3. 봇 이름 입력 (예: My News Bot)
4. 봇 사용자명 입력 (예: mynews_bot)
5. 토큰 복사 (1234567890:ABC...)
```

#### Chat ID 확인
```
개인 사용:
1. @userinfobot 검색
2. /start 입력
3. "Id: 123456789" 복사

그룹 사용:
1. 그룹에 봇 추가
2. @getmyid_bot 추가
3. Group ID 복사 (음수)
```

### 3단계: GitHub Secrets 등록

```
1. 레포지토리 → Settings
2. Secrets and variables → Actions
3. "New repository secret" 클릭
4. 다음 3개 등록:
```

| Name | Value | 설명 |
|------|-------|------|
| `GEMINI_API_KEY` | `AIzaSy...` | Gemini API 키 |
| `TELEGRAM_BOT_TOKEN` | `1234567890:ABC...` | 텔레그램 봇 토큰 |
| `TELEGRAM_CHAT_ID` | `123456789` | Chat ID (개인: 양수, 그룹: 음수) |

### 4단계: RSS 피드 설정

`config.yaml` 파일을 열어 원하는 뉴스 소스 설정:

```yaml
rss_feeds:
  # 원하는 RSS 피드로 변경
  - name: "BBC News"
    url: "http://feeds.bbci.co.uk/news/rss.xml"
    enabled: true
  
  - name: "연합뉴스"
    url: "https://www.yna.co.kr/rss/news.xml"
    enabled: true
```

### 5단계: 테스트 실행

```
1. Actions 탭 클릭
2. "범용 뉴스 자동 요약" 워크플로우 선택
3. "Run workflow" → "Run workflow" 클릭
4. 실행 완료 후 텔레그램 확인
```

**🎉 완료! 이제 매일 오전 8시에 자동으로 뉴스가 전송됩니다.**

---

## 🌟 사용 예시

### 예시 1: 국제 뉴스 (영어)

```yaml
rss_feeds:
  - name: "BBC News"
    url: "http://feeds.bbci.co.uk/news/rss.xml"
    enabled: true
  
  - name: "CNN"
    url: "http://rss.cnn.com/rss/cnn_topstories.rss"
    enabled: true

ai:
  language: "en"  # 영어 요약
```

### 예시 2: 한국 뉴스 (한국어)

```yaml
rss_feeds:
  - name: "연합뉴스"
    url: "https://www.yna.co.kr/rss/news.xml"
    enabled: true
  
  - name: "조선일보"
    url: "https://www.chosun.com/arc/outboundfeeds/rss/"
    enabled: true

ai:
  language: "ko"  # 한국어 요약
```

### 예시 3: 기술 뉴스 (영어)

```yaml
rss_feeds:
  - name: "TechCrunch"
    url: "https://techcrunch.com/feed/"
    enabled: true
  
  - name: "The Verge"
    url: "https://www.theverge.com/rss/index.xml"
    enabled: true

ai:
  language: "en"
  summary_count: 15  # 더 많은 기사
```

### 예시 4: 다국어 혼합

```yaml
rss_feeds:
  - name: "BBC (영어)"
    url: "http://feeds.bbci.co.uk/news/rss.xml"
    enabled: true
  
  - name: "Le Monde (프랑스어)"
    url: "https://www.lemonde.fr/rss/une.xml"
    enabled: true
  
  - name: "日本経済新聞 (일본어)"
    url: "https://www.nikkei.com/rss/"
    enabled: true

ai:
  language: "ko"  # 한국어로 요약
```

---

## 📚 상세 설명

### 시스템 구조

```
┌─────────────────┐
│  GitHub Actions │ ← 매일 오전 8시 자동 실행
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RSS 수집       │ ← 여러 뉴스 소스에서 기사 수집
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Gemini AI      │ ← 핵심 뉴스 선별 및 요약
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  텔레그램 발송   │ ← 요약된 뉴스 자동 전송
└─────────────────┘
```

### 주요 기능

#### 1. RSS 수집
- 설정한 모든 RSS 피드에서 최신 기사 수집
- 중복 제거 및 시간 필터링
- 네트워크 오류 자동 재시도

#### 2. AI 요약
- Google Gemini API로 자동 분석
- 가장 중요한 N개 뉴스만 선별
- 설정한 언어로 요약 생성

#### 3. 텔레그램 발송
- Markdown 형식으로 보기 좋게 전송
- 긴 메시지 자동 분할
- 발송 실패 시 자동 재시도

#### 4. 자동 실행
- GitHub Actions로 서버 없이 실행
- 원하는 시간에 자동 실행
- 실행 로그 자동 저장

---

## 🎨 커스터마이징

### RSS 피드 추가

RSS 피드 URL을 찾는 방법:

1. **뉴스 사이트에서 RSS 아이콘 찾기**
2. **Google 검색**: "사이트명 RSS feed"
3. **개발자 도구**: 페이지 소스에서 `<link type="application/rss+xml"` 검색

```yaml
rss_feeds:
  - name: "뉴스 소스 이름"
    url: "RSS 피드 URL"
    enabled: true
    priority: 1
```

### 실행 시간 변경

`.github/workflows/daily-news.yml` 파일 수정:

```yaml
schedule:
  # UTC 기준 (한국시간 -9시간)
  - cron: '0 23 * * *'  # 한국 오전 8시
  
  # 하루 2회 실행
  - cron: '0 23 * * *'  # 한국 오전 8시
  - cron: '0 9 * * *'   # 한국 오후 6시
  
  # 평일만 실행
  - cron: '0 23 * * 1-5'  # 월~금
```

Cron 표현식 생성: https://crontab.guru/

### 요약 개수 변경

```yaml
ai:
  summary_count: 15  # 10 → 15개로 변경
```

### 언어 변경

```yaml
ai:
  language: "en"  # 영어
  language: "ko"  # 한국어
  language: "ja"  # 일본어
  language: "zh"  # 중국어
  language: "id"  # 인도네시아어
```

### 프롬프트 커스터마이징

`config.yaml`의 `prompts` 섹션 수정:

```yaml
prompts:
  summary: |
    당신은 전문 뉴스 에디터입니다.
    
    다음 기사들 중 가장 중요한 {summary_count}개를 선별하고,
    각 기사를 {language} 언어로 간결하게 요약해주세요.
    
    [기사 목록]
    {articles_text}
    
    [출력 형식]
    1. 제목 - 요약
    2. 제목 - 요약
    ...
```

---

## 🔧 문제 해결

### 텔레그램으로 메시지가 안 와요!

**체크리스트:**
```
□ 봇과 /start로 대화 시작했나요?
□ Chat ID가 정확한가요? (개인: 양수, 그룹: 음수)
□ GitHub Secrets에 3개 모두 등록했나요?
□ Secret 이름이 정확한가요? (대소문자 구분)
```

**확인 방법:**
```
1. GitHub → Actions 탭
2. 최근 실행 클릭
3. 로그에서 "✅ 전체 메시지 발송 완료" 확인
```

### "수집된 기사가 없습니다" 오류

**해결 방법:**

```yaml
# config.yaml
collection:
  hours_threshold: 48  # 24 → 48시간으로 확장
```

또는

```yaml
rss_feeds:
  - name: "문제되는 소스"
    enabled: false  # 일시 비활성화
```

### Gemini API 오류

**401 Unauthorized:**
```
→ API 키가 잘못됨
→ https://aistudio.google.com/app/apikey 에서 재확인
→ GitHub Secrets 재등록
```

**429 Resource Exhausted:**
```
→ API 할당량 초과
→ 24시간 대기 또는 실행 빈도 줄이기
```

### GitHub Actions가 실행 안 돼요!

**확인 사항:**
```
1. 파일 위치: .github/workflows/daily-news.yml (정확히)
2. Settings → Actions → "Allow all actions" 확인
3. 첫 실행은 수동으로 "Run workflow" 클릭
4. 스케줄은 다음 예정 시간부터 자동 실행
```

---

## ❓ FAQ

### Q1. 정말 무료인가요?

**A.** 네, 100% 무료입니다!

- Gemini API: 일 1,500회 무료 (이 시스템은 일 1회만 사용)
- GitHub Actions: Public 레포지토리는 무제한, Private도 월 2,000분 제공
- 텔레그램: 영구 무료

### Q2. Private 레포지토리에서도 무료인가요?

**A.** 네! Private 레포지토리는 월 2,000분 제공됩니다.
- 하루 1회 실행 (1분) = 월 30분
- 충분히 무료 범위 내

### Q3. 프로그래밍 지식이 없어도 되나요?

**A.** 네, 기본 사용은 설정 파일(`config.yaml`)만 수정하면 됩니다.

### Q4. 다른 언어로 요약 가능한가요?

**A.** 네, `config.yaml`에서 `language` 설정만 변경하면 됩니다.

```yaml
ai:
  language: "en"  # 영어, 한국어, 일본어 등
```

### Q5. 한국 뉴스로 변경할 수 있나요?

**A.** 물론입니다!

```yaml
rss_feeds:
  - name: "연합뉴스"
    url: "https://www.yna.co.kr/rss/news.xml"
    enabled: true
```

### Q6. 실행 시간을 변경할 수 있나요?

**A.** 네, `.github/workflows/daily-news.yml` 파일에서 변경 가능합니다.

### Q7. 로컬에서도 실행 가능한가요?

**A.** 네!

```bash
# 설치
pip install -r requirements.txt

# 환경 변수 설정
export GEMINI_API_KEY="..."
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHAT_ID="..."

# 실행
python news_digest.py
```

### Q8. 상업적으로 사용 가능한가요?

**A.** 네, MIT 라이선스로 상업적 사용 가능합니다.

---

## 📖 추가 문서

- **[빠른 시작 가이드](docs/QUICKSTART.md)** - 5분 만에 시작하기
- **[설정 가이드](docs/CONFIGURATION.md)** - 모든 설정 옵션 설명
- **[문제 해결 가이드](docs/TROUBLESHOOTING.md)** - 문제 발생 시 참고
- **[FAQ](docs/FAQ.md)** - 자주 묻는 질문

---

## 🤝 기여

기여는 언제나 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📜 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

---

## 🙏 감사의 말

- [Google Gemini](https://ai.google.dev/) - AI 요약 엔진
- [Telegram](https://telegram.org/) - 메시징 플랫폼
- [GitHub Actions](https://github.com/features/actions) - 자동화 플랫폼
- [feedparser](https://github.com/kurtmckee/feedparser) - RSS 파싱 라이브러리

---

## 📞 지원

문제가 발생하거나 질문이 있으시면:

- [Issues](https://github.com/yourusername/news-digest/issues) - 버그 리포트 및 기능 요청
- [Discussions](https://github.com/yourusername/news-digest/discussions) - 일반 질문 및 토론

---

<p align="center">
  <strong>🎉 완벽한 뉴스 자동화 시스템을 경험하세요!</strong>
</p>

<p align="center">
  <sub>Made with ❤️ by the community</sub>
</p>
