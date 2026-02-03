#!/usr/bin/env python3
"""
인도네시아 뉴스 자동 요약 스크립트 (개선 버전 v2.0)
- Phase 1 개선사항 적용: 로깅, 세션 관리, 재귀 제한
- Phase 2 개선사항 적용: AppConfig 클래스, 예외 처리 개선
"""

import os
import sys
import time
import logging
import hashlib
import asyncio
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

import feedparser
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from telegram import Bot
from telegram.error import TelegramError
from dateutil import parser as date_parser

# ========================================
# 1. 로깅 초기화 (config 로드 전)
# ========================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ========================================
# 2. 설정 로드
# ========================================

from config_loader import load_config, ConfigLoader

try:
    CONFIG = load_config('config.yaml')
except Exception as e:
    logger.error(f"❌ 설정 로드 실패: {e}")
    sys.exit(1)

# 설정 기반 로깅 재설정
log_level = getattr(logging, CONFIG['logging']['level'])
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=log_level,
    format=CONFIG['logging']['format'],
    datefmt=CONFIG['logging']['date_format'],
    force=True
)
logger = logging.getLogger(__name__)

# ========================================
# 3. 설정 통합 클래스
# ========================================

@dataclass
class AppConfig:
    """애플리케이션 설정 통합 클래스"""
    # Secrets
    gemini_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    
    # RSS
    rss_feeds: Dict[str, str]
    
    # Collection
    max_articles_per_source: int
    max_total_articles: int
    hours_threshold: int
    request_timeout: int
    max_retries: int
    user_agent: str
    
    # AI
    model_name: str
    temperature: float
    max_output_tokens: int
    top_p: float
    top_k: int
    summary_count: int
    language: str
    
    # Telegram
    max_message_length: int
    parse_mode: str
    disable_preview: bool
    send_interval: float
    
    @classmethod
    def from_config_and_env(cls, config: Dict) -> 'AppConfig':
        """설정 파일 + 환경 변수로부터 생성"""
        return cls(
            # Secrets
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.environ.get("TELEGRAM_CHAT_ID", ""),
            
            # RSS
            rss_feeds=ConfigLoader.get_rss_feeds(config),
            
            # Collection
            max_articles_per_source=config['collection']['max_articles_per_source'],
            max_total_articles=config['collection']['max_total_articles'],
            hours_threshold=config['collection']['hours_threshold'],
            request_timeout=config['collection']['request_timeout'],
            max_retries=config['collection']['max_retries'],
            user_agent=config['collection']['user_agent'],
            
            # AI
            model_name=config['ai']['model'],
            temperature=config['ai']['temperature'],
            max_output_tokens=config['ai']['max_output_tokens'],
            top_p=config['ai'].get('top_p', 0.9),
            top_k=config['ai'].get('top_k', 40),
            summary_count=config['ai']['summary_count'],
            language=config['ai']['language'],
            
            # Telegram
            max_message_length=config['telegram']['max_message_length'],
            parse_mode=config['telegram'].get('parse_mode', 'Markdown'),
            disable_preview=config['telegram'].get('disable_preview', True),
            send_interval=config['telegram'].get('send_interval', 0.5)
        )
    
    def validate_secrets(self) -> List[str]:
        """누락된 secrets 검증"""
        missing = []
        if not self.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        return missing
    
    def log_summary(self):
        """설정 요약 로그"""
        logger.info("📋 설정 요약:")
        logger.info(f"  • RSS 피드: {len(self.rss_feeds)}개")
        logger.info(f"  • 최대 수집: {self.max_total_articles}개")
        logger.info(f"  • 시간 범위: {self.hours_threshold}시간")
        logger.info(f"  • AI 모델: {self.model_name}")
        logger.info(f"  • 요약 개수: {self.summary_count}개")

# 설정 인스턴스 생성
app_config = AppConfig.from_config_and_env(CONFIG)

# ========================================
# 4. HTTP 세션 관리 (개선)
# ========================================

@contextmanager
def get_http_session(config: AppConfig):
    """HTTP 세션 컨텍스트 매니저"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=config.max_retries,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,  # 커넥션 풀 크기
        pool_maxsize=10
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({'User-Agent': config.user_agent})
    
    try:
        yield session
    finally:
        session.close()

# ========================================
# 5. RSS 수집 함수 (개선)
# ========================================

def fetch_rss_articles(config: AppConfig) -> List[Dict]:
    """RSS 피드에서 최근 기사 수집"""
    all_articles = []
    seen_hashes = set()
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=config.hours_threshold)
    
    logger.info(f"📡 RSS 수집 시작 (기준: {cutoff_time.strftime('%Y-%m-%d %H:%M UTC')})")
    
    with get_http_session(config) as session:
        for source, feed_url in config.rss_feeds.items():
            try:
                logger.info(f"🔍 {source} 수집 중...")
                
                response = session.get(feed_url, timeout=config.request_timeout)
                response.raise_for_status()
                feed = feedparser.parse(response.content)
                
                if not feed.entries:
                    logger.warning(f"⚠️  {source}: 기사 없음")
                    continue
                
                article_count = 0
                for entry in feed.entries[:config.max_articles_per_source]:
                    published_date = parse_article_date(entry)
                    
                    if published_date and published_date < cutoff_time:
                        continue
                    
                    article_hash = hashlib.md5(
                        (entry.title + entry.link).encode('utf-8')
                    ).hexdigest()
                    
                    if article_hash in seen_hashes:
                        continue
                    seen_hashes.add(article_hash)
                    
                    article = {
                        "source": source,
                        "title": clean_text(entry.title),
                        "link": entry.link,
                        "summary": clean_text(getattr(entry, 'summary', ''))[:800],
                        "published": published_date.strftime('%Y-%m-%d %H:%M UTC') if published_date else "N/A"
                    }
                    
                    all_articles.append(article)
                    article_count += 1
                    
                    if len(all_articles) >= config.max_total_articles:
                        break
                
                logger.info(f"✅ {source}: {article_count}개 수집")
                
            except requests.exceptions.Timeout:
                logger.error(f"⏱️  {source}: 타임아웃 ({config.request_timeout}초)")
            except requests.exceptions.RequestException as e:
                logger.error(f"🌐 {source}: 네트워크 오류 - {str(e)}")
            except Exception as e:
                logger.error(f"❌ {source}: 예상치 못한 오류 - {str(e)}")
            
            if len(all_articles) >= config.max_total_articles:
                logger.info(f"⚠️  최대 수집 개수 도달 ({config.max_total_articles})")
                break
    
    logger.info(f"✅ 총 {len(all_articles)}개 기사 수집 완료")
    return all_articles

def parse_article_date(entry) -> Optional[datetime]:
    """기사 날짜 파싱 (개선)"""
    for field in ['published', 'updated', 'pubDate', 'created']:
        try:
            date_str = entry.__dict__.get(field)
            if date_str:
                dt = date_parser.parse(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
        except (ValueError, TypeError, AttributeError, KeyError):
            continue
    return None

def clean_text(text: str) -> str:
    """텍스트 정리"""
    return ' '.join(text.replace('\n', ' ').replace('\t', ' ').split())

# ========================================
# 6. Gemini 요약 함수 (개선)
# ========================================

# 재시도 가능/불가능 예외 정의
RETRYABLE_EXCEPTIONS = (
    google_exceptions.DeadlineExceeded,
    google_exceptions.ServiceUnavailable,
    google_exceptions.ResourceExhausted,
    ConnectionError,
    TimeoutError,
)

NON_RETRYABLE_EXCEPTIONS = (
    google_exceptions.InvalidArgument,
    google_exceptions.Unauthenticated,
    google_exceptions.PermissionDenied,
)

def build_articles_text(articles: List[Dict]) -> str:
    """기사 목록을 텍스트로 변환"""
    text = ""
    for i, article in enumerate(articles, 1):
        text += f"{i}. [{article['source']}] {article['title']}\n"
        if article['summary']:
            text += f"   개요: {article['summary'][:200]}\n"
        text += f"   링크: {article['link']}\n"
        text += f"   발행: {article['published']}\n\n"
    return text

def adjust_articles_for_token_limit(articles: List[Dict], max_attempts: int = 3) -> List[Dict]:
    """토큰 제한에 맞게 기사 수 조정"""
    for attempt in range(1, max_attempts + 1):
        articles_text = build_articles_text(articles)
        estimated_tokens = len(articles_text) // 3
        
        if estimated_tokens <= 28000:
            return articles
        
        if attempt == max_attempts:
            logger.error(f"❌ 토큰 수 초과 ({estimated_tokens}), 강제 축소")
            return articles[:20]
        
        # 30% 축소
        new_count = int(len(articles) * 0.7)
        logger.warning(f"⚠️  시도 {attempt}: 토큰 {estimated_tokens}, 기사 {len(articles)} → {new_count}")
        articles = articles[:new_count]
    
    return articles

def summarize_with_gemini(articles: List[Dict], config: AppConfig) -> str:
    """Gemini로 뉴스 요약 (개선)"""
    
    if not articles:
        logger.error("❌ 요약할 기사가 없습니다")
        return "⚠️ 수집된 기사가 없어 요약을 생성할 수 없습니다."
    
    logger.info(f"🤖 Gemini 요약 시작 ({len(articles)}개 기사 → {config.summary_count}개 선별)")
    
    # 토큰 제한 확인 및 조정
    articles = adjust_articles_for_token_limit(articles)
    articles_text = build_articles_text(articles)
    
    # 프롬프트 생성
    current_time = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
    
    if 'prompts' in CONFIG and 'summary' in CONFIG['prompts']:
        prompt = CONFIG['prompts']['summary'].format(
            hours_threshold=config.hours_threshold,
            article_count=len(articles),
            summary_count=config.summary_count,
            language=config.language,
            articles_text=articles_text,
            current_time=current_time
        )
    else:
        prompt = f"""당신은 인도네시아 전문 뉴스 편집자입니다.
다음은 최근 {config.hours_threshold}시간 내 인도네시아 관련 뉴스 {len(articles)}개입니다.

[핵심 요구사항]
1. 정치, 경제, 사회, 국제관계 등에서 가장 중요한 뉴스 정확히 {config.summary_count}개만 선별
2. 동일 사건은 하나로 통합
3. 각 뉴스를 {config.language} 언어로 간결하게 요약

[뉴스 목록]
{articles_text}

[출력 형식]
🌅 **인도네시아 오늘의 핵심 뉴스**
━━━━━━━━━━━━━━━━━━

1. **[매체] 제목**
   → 요약 내용

... (총 {config.summary_count}개)

━━━━━━━━━━━━━━━━━━
🤖 *Gemini AI 자동 요약* | {current_time}
"""
    
    try:
        genai.configure(api_key=config.gemini_api_key)
        model = genai.GenerativeModel(config.model_name)
        
        safety_settings = [
            {"category": cat, "threshold": "BLOCK_NONE"}
            for cat in [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT"
            ]
        ]
        
        generation_config = {
            "temperature": config.temperature,
            "max_output_tokens": config.max_output_tokens,
            "top_p": config.top_p,
            "top_k": config.top_k
        }
        
        # 재시도 로직 (개선)
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = model.generate_content(
                    prompt,
                    safety_settings=safety_settings,
                    generation_config=generation_config
                )
                
                if not response.text or len(response.text) < 200:
                    raise ValueError(f"응답 너무 짧음: {len(response.text)} chars")
                
                summary = response.text.strip()
                logger.info(f"✅ Gemini 요약 완료 ({len(summary)} chars)")
                return summary
                
            except NON_RETRYABLE_EXCEPTIONS as e:
                logger.error(f"❌ 재시도 불가능한 오류: {type(e).__name__}")
                raise
                
            except RETRYABLE_EXCEPTIONS as e:
                logger.warning(f"⚠️  시도 {attempt}/{max_attempts}: {type(e).__name__}")
                if attempt < max_attempts:
                    wait_time = min(2 ** attempt, 60)
                    logger.info(f"⏳ {wait_time}초 대기 후 재시도...")
                    time.sleep(wait_time)
                else:
                    raise
            
            except Exception as e:
                logger.warning(f"⚠️  알 수 없는 오류: {type(e).__name__} - {str(e)}")
                if attempt < max_attempts:
                    time.sleep(2 ** attempt)
                else:
                    raise
        
    except Exception as e:
        logger.error(f"❌ Gemini API 최종 실패: {str(e)}")
        backup = "⚠️ **AI 요약 실패** - 원문 기사 목록:\n\n"
        for i, article in enumerate(articles[:10], 1):
            backup += f"{i}. **[{article['source']}]** {article['title']}\n"
            backup += f"   🔗 {article['link']}\n\n"
        backup += f"\n━━━━━━━━━━━━━━━━━━\n⚠️ *수동 확인 필요* | {current_time}"
        return backup

# ========================================
# 7. 텔레그램 발송 함수
# ========================================

async def send_to_telegram(message: str, config: AppConfig) -> bool:
    """텔레그램으로 메시지 발송"""
    
    try:
        bot = Bot(token=config.telegram_bot_token)
        messages = split_message(message, config.max_message_length)
        logger.info(f"📤 텔레그램 발송 시작 ({len(messages)}개 메시지)")
        
        for i, msg in enumerate(messages, 1):
            try:
                await bot.send_message(
                    chat_id=config.telegram_chat_id,
                    text=msg,
                    parse_mode=config.parse_mode,
                    disable_web_page_preview=config.disable_preview
                )
                logger.info(f"✅ 메시지 {i}/{len(messages)} 발송 완료")
                
                if i < len(messages):
                    await asyncio.sleep(config.send_interval)
                    
            except TelegramError as e:
                logger.error(f"❌ 메시지 {i} 발송 실패: {str(e)}")
                if "parse" in str(e).lower():
                    logger.info("🔄 plain text로 재시도")
                    await bot.send_message(
                        chat_id=config.telegram_chat_id,
                        text=msg,
                        disable_web_page_preview=True
                    )
                else:
                    raise
        
        logger.info("✅ 전체 메시지 발송 완료")
        return True
        
    except Exception as e:
        logger.error(f"❌ 텔레그램 발송 실패: {str(e)}")
        return False

def split_message(message: str, max_length: int) -> List[str]:
    """메시지 분할"""
    if len(message) <= max_length:
        return [message]
    
    messages = []
    parts = message.split('\n\n')
    current = ""
    
    for part in parts:
        if len(part) > max_length:
            if current:
                messages.append(current.strip())
                current = ""
            lines = part.split('\n')
            for line in lines:
                if len(current) + len(line) + 1 > max_length:
                    messages.append(current.strip())
                    current = line + "\n"
                else:
                    current += line + "\n"
        elif len(current) + len(part) + 2 > max_length:
            messages.append(current.strip())
            current = part + "\n\n"
        else:
            current += part + "\n\n"
    
    if current.strip():
        messages.append(current.strip())
    
    return messages

# ========================================
# 8. 메인 실행 함수
# ========================================

def main():
    """메인 실행 로직"""
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("🚀 인도네시아 뉴스 자동 요약 v2.0 (개선 버전)")
    logger.info(f"⏰ 실행 시간: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    logger.info("=" * 60)
    
    # 1. 환경 변수 검증
    missing = app_config.validate_secrets()
    if missing:
        logger.error(f"❌ 누락된 환경 변수: {', '.join(missing)}")
        logger.error("GitHub Secrets에 다음 값을 설정해주세요:")
        for var in missing:
            logger.error(f"  - {var}")
        sys.exit(1)
    
    logger.info("✅ 환경 변수 검증 완료")
    app_config.log_summary()
    
    # 2. RSS 수집
    logger.info("\n[단계 1/3] RSS 수집")
    articles = fetch_rss_articles(app_config)
    
    if not articles:
        logger.warning("⚠️  수집된 기사가 없습니다")
        sys.exit(0)
    
    # 3. Gemini 요약
    logger.info("\n[단계 2/3] Gemini AI 요약")
    summary = summarize_with_gemini(articles, app_config)
    
    # 4. 텔레그램 발송
    logger.info("\n[단계 3/3] 텔레그램 발송")
    success = send_to_telegram(summary, app_config)
    
    # 5. 결과
    elapsed_time = time.time() - start_time
    logger.info("\n" + "=" * 60)
    if success:
        logger.info(f"🎉 전체 작업 성공! (소요: {elapsed_time:.1f}초)")
    else:
        logger.error(f"❌ 텔레그램 발송 실패 (소요: {elapsed_time:.1f}초)")
        sys.exit(1)
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n⚠️  사용자 중단")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n💥 치명적 오류: {str(e)}", exc_info=True)
        sys.exit(1)
