#!/usr/bin/env python3
"""
범용 뉴스 자동 요약 시스템 (개선 버전)
2026년 2월 최적화: 실용적 개선만 적용
"""

import os
import sys
import logging
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import feedparser
import requests
import google.generativeai as genai
import telegram
from config_loader import load_config, validate_config

# ═══════════════════════════════════════════════════════════════
# 로깅 설정
# ═══════════════════════════════════════════════════════════════

def setup_logging(config: Dict) -> None:
    """로깅 설정"""
    log_config = config.get('logging', {})
    
    logging.basicConfig(
        level=getattr(logging, log_config.get('level', 'INFO')),
        format=log_config.get('format', '%(asctime)s [%(levelname)s] %(message)s'),
        datefmt=log_config.get('date_format', '%Y-%m-%d %H:%M:%S')
    )

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# User-Agent 로테이션 (403 차단 방지)
# ═══════════════════════════════════════════════════════════════

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15'
]

def get_random_user_agent() -> str:
    """랜덤 User-Agent 반환"""
    return random.choice(USER_AGENTS)

# ═══════════════════════════════════════════════════════════════
# 환경 변수 검증
# ═══════════════════════════════════════════════════════════════

def validate_environment() -> Dict[str, str]:
    """환경 변수 검증 및 반환"""
    logger.info("🔍 환경 변수 검증 중...")
    
    required_vars = {
        'GEMINI_API_KEY': 'Gemini API 키',
        'TELEGRAM_BOT_TOKEN': '텔레그램 봇 토큰',
        'TELEGRAM_CHAT_ID': 'Chat ID'
    }
    
    missing = []
    env_vars = {}
    
    for key, name in required_vars.items():
        value = os.getenv(key)
        if not value:
            missing.append(f"  ❌ {key}: {name}")
        else:
            env_vars[key] = value
            
            # API 키 형식 검증
            if key == 'GEMINI_API_KEY' and not value.startswith('AIza'):
                logger.warning(f"⚠️ {key} 형식이 올바르지 않을 수 있습니다")
    
    if missing:
        logger.error("❌ 누락된 환경 변수:")
        for msg in missing:
            logger.error(msg)
        logger.error("\n💡 설정 방법:")
        logger.error("  - Gemini API: https://aistudio.google.com/app/apikey")
        logger.error("  - 텔레그램 봇: @BotFather")
        logger.error("  - Chat ID: @userinfobot")
        sys.exit(1)
    
    logger.info("✅ 환경 변수 검증 완료")
    return env_vars

# ═══════════════════════════════════════════════════════════════
# 텔레그램 연결 검증
# ═══════════════════════════════════════════════════════════════

def validate_telegram(token: str, chat_id: str) -> telegram.Bot:
    """텔레그램 설정 검증"""
    logger.info("🔍 텔레그램 연결 검증 중...")
    
    try:
        bot = telegram.Bot(token=token)
        
        # 봇 정보 확인
        bot_info = bot.get_me()
        logger.info(f"✅ 봇 연결: @{bot_info.username}")
        
        # Chat 존재 확인
        try:
            chat = bot.get_chat(chat_id)
            logger.info(f"✅ Chat 확인: {chat.type}")
        except telegram.error.BadRequest:
            logger.error("❌ Chat ID가 잘못되었습니다")
            logger.error("💡 확인 방법:")
            logger.error("  - 개인: @userinfobot → /start")
            logger.error("  - 그룹: @getmyid_bot 사용")
            sys.exit(1)
        
        logger.info("✅ 텔레그램 검증 완료")
        return bot
        
    except telegram.error.Unauthorized:
        logger.error("❌ 봇 토큰이 잘못되었습니다")
        logger.error("💡 @BotFather에서 토큰 재확인")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 텔레그램 검증 실패: {e}")
        sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# RSS 수집 (재시도 로직 + User-Agent 로테이션)
# ═══════════════════════════════════════════════════════════════

def fetch_rss_with_retry(url: str, config: Dict) -> Optional[str]:
    """재시도 로직이 있는 RSS 수집"""
    collection_config = config.get('collection', {})
    timeout = collection_config.get('request_timeout', 10)
    max_retries = collection_config.get('max_retries', 3)
    rotate_ua = collection_config.get('rotate_user_agent', True)
    
    for attempt in range(max_retries):
        try:
            # User-Agent 로테이션
            headers = {}
            if rotate_ua:
                headers['User-Agent'] = get_random_user_agent()
            
            logger.debug(f"RSS 수집 시도 {attempt+1}/{max_retries}: {url}")
            
            response = requests.get(
                url,
                timeout=timeout,
                headers=headers
            )
            
            # 상태 코드별 처리
            if response.status_code == 403:
                logger.warning(f"🚫 차단됨 (403): {url}")
                return None  # 즉시 포기
            elif response.status_code == 429:
                logger.warning(f"⏱️ Rate Limit (429): {url}")
                if attempt < max_retries - 1:
                    time.sleep(60)  # 1분 대기
                    continue
            
            response.raise_for_status()
            logger.debug(f"✅ RSS 수집 성공: {url}")
            return response.text
            
        except requests.Timeout:
            logger.warning(f"⏱️ 타임아웃 ({attempt+1}/{max_retries}): {url}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 지수 백오프
                
        except requests.RequestException as e:
            logger.error(f"❌ RSS 수집 실패: {url} - {e}")
            if attempt == max_retries - 1:
                return None
    
    return None

def fetch_all_rss(config: Dict) -> List[Dict]:
    """모든 RSS 피드 수집"""
    logger.info("📰 RSS 피드 수집 시작...")
    
    feeds = config.get('rss_feeds', [])
    enabled_feeds = [f for f in feeds if f.get('enabled', False)]
    
    if not enabled_feeds:
        logger.warning("⚠️ 활성화된 RSS 피드가 없습니다")
        return []
    
    logger.info(f"📡 {len(enabled_feeds)}개 소스에서 수집 중...")
    
    all_articles = []
    collection_config = config.get('collection', {})
    max_per_source = collection_config.get('max_articles_per_source', 20)
    max_total = collection_config.get('max_total_articles', 60)
    hours_threshold = collection_config.get('hours_threshold', 24)
    
    cutoff_time = datetime.now() - timedelta(hours=hours_threshold)
    
    for feed in enabled_feeds:
        name = feed.get('name')
        url = feed.get('url')
        
        logger.info(f"  📡 {name} 수집 중...")
        
        # RSS 수집
        content = fetch_rss_with_retry(url, config)
        if not content:
            logger.warning(f"  ⚠️ {name}: 수집 실패")
            continue
        
        # 파싱
        try:
            parsed = feedparser.parse(content)
            entries = parsed.entries[:max_per_source]
            
            # 시간 필터링
            recent_articles = []
            for entry in entries:
                pub_date = entry.get('published_parsed')
                if pub_date:
                    pub_datetime = datetime(*pub_date[:6])
                    if pub_datetime >= cutoff_time:
                        recent_articles.append({
                            'source': name,
                            'title': entry.get('title', '제목 없음'),
                            'link': entry.get('link', ''),
                            'published': pub_datetime
                        })
            
            all_articles.extend(recent_articles)
            logger.info(f"  ✅ {name}: {len(recent_articles)}개 수집")
            
        except Exception as e:
            logger.error(f"  ❌ {name}: 파싱 실패 - {e}")
    
    # 전체 개수 제한
    if len(all_articles) > max_total:
        all_articles = sorted(all_articles, key=lambda x: x['published'], reverse=True)
        all_articles = all_articles[:max_total]
    
    logger.info(f"✅ 총 {len(all_articles)}개 기사 수집 완료")
    return all_articles

# ═══════════════════════════════════════════════════════════════
# Gemini AI 요약 (토큰 카운팅 + 스마트 자르기)
# ═══════════════════════════════════════════════════════════════

def count_tokens(model, text: str) -> int:
    """토큰 수 계산"""
    try:
        result = model.count_tokens(text)
        return result.total_tokens
    except:
        # 대략적 계산 (영어: 4자/토큰, 한국어: 2자/토큰)
        return len(text) // 3

def smart_truncate_articles(model, articles: List[Dict], config: Dict, max_tokens: int = 30000) -> List[Dict]:
    """토큰 제한 내로 기사 수 조정"""
    ai_config = config.get('ai', {})
    prompts = config.get('prompts', {})
    
    # 프롬프트 준비
    prompt_template = prompts.get('summary', '')
    summary_count = ai_config.get('summary_count', 10)
    hours_threshold = config.get('collection', {}).get('hours_threshold', 24)
    language = ai_config.get('language', 'ko')
    
    # 기사 텍스트 포맷팅
    def format_articles(arts):
        articles_text = "\n\n".join([
            f"[{a['source']}] {a['title']}\n링크: {a['link']}"
            for a in arts
        ])
        return prompt_template.format(
            summary_count=summary_count,
            hours_threshold=hours_threshold,
            language=language,
            articles_text=articles_text
        )
    
    # 초기 토큰 계산
    full_prompt = format_articles(articles)
    current_tokens = count_tokens(model, full_prompt)
    
    logger.info(f"📊 초기 토큰 수: {current_tokens:,}")
    
    # 토큰 초과 시 기사 축소
    if current_tokens > max_tokens:
        logger.warning(f"⚠️ 토큰 수 많음 ({current_tokens:,}), 기사 축소 중...")
        
        while current_tokens > max_tokens and len(articles) > 10:
            articles = articles[:-5]  # 마지막 5개 제거
            full_prompt = format_articles(articles)
            current_tokens = count_tokens(model, full_prompt)
        
        logger.info(f"✅ 축소 완료: {len(articles)}개 기사, {current_tokens:,} 토큰")
    
    return articles

def summarize_with_gemini(articles: List[Dict], config: Dict, api_key: str) -> str:
    """Gemini AI로 뉴스 요약"""
    if not articles:
        logger.warning("⚠️ 요약할 기사가 없습니다")
        return None
    
    logger.info("🤖 Gemini AI 요약 생성 중...")
    
    ai_config = config.get('ai', {})
    prompts = config.get('prompts', {})
    
    # Gemini 설정
    genai.configure(api_key=api_key)
    
    model_name = ai_config.get('model', 'gemini-2.5-flash')
    model = genai.GenerativeModel(model_name)
    
    logger.info(f"  🤖 모델: {model_name}")
    
    # 토큰 제한 확인 및 축소
    articles = smart_truncate_articles(model, articles, config)
    
    # 프롬프트 생성
    prompt_template = prompts.get('summary', '')
    summary_count = ai_config.get('summary_count', 10)
    hours_threshold = config.get('collection', {}).get('hours_threshold', 24)
    language = ai_config.get('language', 'ko')
    
    articles_text = "\n\n".join([
        f"[{a['source']}] {a['title']}\n링크: {a['link']}"
        for a in articles
    ])
    
    prompt = prompt_template.format(
        summary_count=summary_count,
        hours_threshold=hours_threshold,
        language=language,
        articles_text=articles_text
    )
    
    # AI 요약 생성
    max_retries = 3
    for attempt in range(max_retries):
        try:
            logger.debug(f"  요약 생성 시도 {attempt+1}/{max_retries}")
            
            generation_config = {
                'temperature': ai_config.get('temperature', 0.3),
                'top_p': ai_config.get('top_p', 0.9),
                'top_k': ai_config.get('top_k', 40),
                'max_output_tokens': ai_config.get('max_output_tokens', 2048),
            }
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            summary = response.text.strip()
            
            # 🔥 핵심 수정: 응답 검증 강화!
            MIN_EXPECTED_LENGTH = 800  # 10개 뉴스 최소 길이
            
            if not summary or len(summary) < MIN_EXPECTED_LENGTH:
                logger.warning(f"  ⚠️ 응답 부족: {len(summary)}자 (최소 {MIN_EXPECTED_LENGTH}자 필요)")
                if attempt < max_retries - 1:
                    logger.info(f"  🔄 재시도 {attempt+1}/{max_retries}")
                    time.sleep(2 ** attempt)  # 지수 백오프
                    continue  # 재시도!
                else:
                    # 최종 시도도 실패
                    raise ValueError(f"응답 길이 부족: {len(summary)}자")
            
            logger.info(f"✅ 요약 생성 완료 ({len(summary)}자)")
            return summary
            
        except Exception as e:
            logger.error(f"  ❌ 시도 {attempt+1}/{max_retries}: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
    
    logger.error("❌ Gemini API 최종 실패")
    return None

# ═══════════════════════════════════════════════════════════════
# 텔레그램 발송 (Markdown Escape + 에러 처리)
# ═══════════════════════════════════════════════════════════════

def escape_markdown(text: str) -> str:
    """Markdown v2 특수문자 이스케이프"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def send_to_telegram(bot: telegram.Bot, chat_id: str, message: str, config: Dict) -> bool:
    """텔레그램으로 메시지 발송"""
    logger.info("📱 텔레그램 발송 중...")
    
    telegram_config = config.get('telegram', {})
    max_length = telegram_config.get('max_message_length', 4000)
    parse_mode = telegram_config.get('parse_mode', 'Markdown')
    disable_preview = telegram_config.get('disable_preview', True)
    should_escape = telegram_config.get('escape_markdown', True)
    
    # 메시지 분할
    if len(message) > max_length:
        logger.warning(f"⚠️ 메시지 길이 초과 ({len(message)}자), 분할 발송")
        messages = [message[i:i+max_length] for i in range(0, len(message), max_length)]
    else:
        messages = [message]
    
    # 발송
    for i, msg in enumerate(messages):
        try:
            # Markdown escape
            if should_escape and parse_mode == 'Markdown':
                msg_escaped = escape_markdown(msg)
            else:
                msg_escaped = msg
            
            bot.send_message(
                chat_id=chat_id,
                text=msg_escaped,
                parse_mode=parse_mode,
                disable_web_page_preview=disable_preview
            )
            
            logger.info(f"  ✅ 메시지 {i+1}/{len(messages)} 발송 완료")
            
            if i < len(messages) - 1:
                time.sleep(telegram_config.get('send_interval', 0.5))
            
        except telegram.error.BadRequest as e:
            # Markdown 파싱 실패 시 plain text로 재시도
            if "can't parse" in str(e).lower():
                logger.warning(f"  ⚠️ Markdown 파싱 실패, plain text로 재시도")
                try:
                    bot.send_message(
                        chat_id=chat_id,
                        text=msg,  # 원본 그대로
                        disable_web_page_preview=disable_preview
                    )
                    logger.info(f"  ✅ Plain text 발송 성공")
                except Exception as e2:
                    logger.error(f"  ❌ 재시도 실패: {e2}")
                    return False
            else:
                logger.error(f"  ❌ 발송 실패: {e}")
                return False
        except Exception as e:
            logger.error(f"  ❌ 발송 실패: {e}")
            return False
    
    logger.info(f"✅ 전체 메시지 발송 완료 ({len(messages)}개)")
    return True

# ═══════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════

def main():
    """메인 실행 함수"""
    start_time = time.time()
    
    try:
        print("="*60)
        print("🚀 범용 뉴스 자동 요약 시스템 (개선 버전)")
        print("="*60)
        
        # 1. 설정 로드
        logger.info("📋 설정 파일 로드 중...")
        config = load_config()
        validate_config(config)
        setup_logging(config)
        logger.info("✅ 설정 로드 완료")
        
        # 2. 환경 변수 검증
        env_vars = validate_environment()
        
        # 3. 텔레그램 검증
        bot = validate_telegram(
            env_vars['TELEGRAM_BOT_TOKEN'],
            env_vars['TELEGRAM_CHAT_ID']
        )
        
        # 4. RSS 수집
        articles = fetch_all_rss(config)
        
        if not articles:
            logger.warning("⚠️ 수집된 기사가 없습니다")
            logger.warning("💡 가능한 원인:")
            logger.warning("  - RSS 피드 일시 오류")
            logger.warning("  - 24시간 내 새 기사 없음")
            logger.warning("  - 네트워크 문제")
            sys.exit(0)
        
        # 5. AI 요약
        summary = summarize_with_gemini(
            articles,
            config,
            env_vars['GEMINI_API_KEY']
        )
        
        if not summary:
            logger.error("❌ 요약 생성 실패")
            sys.exit(1)
        
        # 6. 텔레그램 발송
        success = send_to_telegram(
            bot,
            env_vars['TELEGRAM_CHAT_ID'],
            summary,
            config
        )
        
        if not success:
            logger.error("❌ 텔레그램 발송 실패")
            sys.exit(1)
        
        # 완료
        elapsed = time.time() - start_time
        logger.info(f"🎉 전체 작업 성공! (소요: {elapsed:.1f}초)")
        print("="*60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 사용자가 중단했습니다")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ 치명적 오류: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
