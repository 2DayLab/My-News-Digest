"""
설정 파일 로더 및 검증기
config.yaml을 로드하고 검증합니다.
"""

import os
import sys
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

try:
    import yaml
except ImportError:
    print("❌ PyYAML이 설치되지 않았습니다.")
    print("   pip install pyyaml")
    sys.exit(1)

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """설정 관련 오류"""
    pass


class ConfigValidator:
    """설정 검증기"""
    
    @staticmethod
    def validate_rss_feeds(feeds: List[Dict[str, Any]]) -> bool:
        """RSS 피드 검증"""
        if not feeds:
            raise ConfigError("RSS 피드가 비어있습니다")
        
        enabled_count = 0
        for i, feed in enumerate(feeds):
            # 필수 필드 확인
            if 'name' not in feed:
                raise ConfigError(f"피드 #{i+1}: 'name' 필드 누락")
            if 'url' not in feed:
                raise ConfigError(f"피드 '{feed['name']}': 'url' 필드 누락")
            
            # URL 검증
            url = feed['url']
            if not isinstance(url, str) or not url.startswith(('http://', 'https://')):
                raise ConfigError(f"피드 '{feed['name']}': 잘못된 URL - {url}")
            
            # enabled 확인
            if feed.get('enabled', True):
                enabled_count += 1
        
        if enabled_count == 0:
            raise ConfigError("활성화된 RSS 피드가 없습니다 (enabled=true 필요)")
        
        logger.info(f"✅ RSS 피드 검증 완료: {enabled_count}/{len(feeds)}개 활성화")
        return True
    
    @staticmethod
    def validate_collection(config: Dict[str, Any]) -> bool:
        """수집 설정 검증"""
        max_per_source = config.get('max_articles_per_source', 20)
        max_total = config.get('max_total_articles', 60)
        hours = config.get('hours_threshold', 24)
        timeout = config.get('request_timeout', 10)
        retries = config.get('max_retries', 3)
        
        # 범위 검증
        if not (1 <= max_per_source <= 100):
            raise ConfigError(f"max_articles_per_source는 1~100 사이여야 함: {max_per_source}")
        
        if not (1 <= max_total <= 200):
            raise ConfigError(f"max_total_articles는 1~200 사이여야 함: {max_total}")
        
        if not (1 <= hours <= 168):
            raise ConfigError(f"hours_threshold는 1~168 사이여야 함: {hours}")
        
        if not (1 <= timeout <= 60):
            raise ConfigError(f"request_timeout은 1~60 사이여야 함: {timeout}")
        
        if not (1 <= retries <= 10):
            raise ConfigError(f"max_retries는 1~10 사이여야 함: {retries}")
        
        logger.info("✅ 수집 설정 검증 완료")
        return True
    
    @staticmethod
    def validate_ai(config: Dict[str, Any]) -> bool:
        """AI 설정 검증"""
        model = config.get('model', '')
        temperature = config.get('temperature', 0.3)
        max_tokens = config.get('max_output_tokens', 2048)
        summary_count = config.get('summary_count', 10)
        
        # 모델명 검증
        valid_models = [
            'gemini-1.5-flash-8b',
            'gemini-1.5-flash',
            'gemini-1.5-pro',
            'gemini-pro'
        ]
        if model not in valid_models:
            logger.warning(f"⚠️  알 수 없는 모델: {model} (계속 진행)")
        
        # 파라미터 범위 검증
        if not (0.0 <= temperature <= 2.0):
            raise ConfigError(f"temperature는 0.0~2.0 사이여야 함: {temperature}")
        
        if not (100 <= max_tokens <= 8192):
            raise ConfigError(f"max_output_tokens는 100~8192 사이여야 함: {max_tokens}")
        
        if not (1 <= summary_count <= 50):
            raise ConfigError(f"summary_count는 1~50 사이여야 함: {summary_count}")
        
        logger.info("✅ AI 설정 검증 완료")
        return True
    
    @classmethod
    def validate(cls, config: Dict[str, Any]) -> bool:
        """전체 설정 검증"""
        # 필수 섹션 확인
        required_sections = ['rss_feeds', 'collection', 'ai']
        for section in required_sections:
            if section not in config:
                raise ConfigError(f"필수 섹션 누락: {section}")
        
        # 각 섹션 검증
        cls.validate_rss_feeds(config['rss_feeds'])
        cls.validate_collection(config['collection'])
        cls.validate_ai(config['ai'])
        
        return True


class ConfigLoader:
    """설정 파일 로더"""
    
    DEFAULT_CONFIG = {
        'rss_feeds': [
            {
                'name': 'The Jakarta Post',
                'url': 'https://www.thejakartapost.com/rss',
                'enabled': True,
                'priority': 1
            },
            {
                'name': 'CNBC Indonesia',
                'url': 'https://www.cnbcindonesia.com/rss',
                'enabled': True,
                'priority': 2
            },
            {
                'name': 'Tempo.co',
                'url': 'https://www.tempo.co/rss',
                'enabled': True,
                'priority': 3
            },
            {
                'name': 'Antara News',
                'url': 'https://www.antaranews.com/rss/terkini',
                'enabled': True,
                'priority': 4
            }
        ],
        'collection': {
            'max_articles_per_source': 20,
            'max_total_articles': 60,
            'hours_threshold': 24,
            'request_timeout': 10,
            'max_retries': 3,
            'user_agent': 'Mozilla/5.0 (compatible; NewsBot/1.0)'
        },
        'ai': {
            'model': 'gemini-1.5-flash-8b',
            'temperature': 0.3,
            'max_output_tokens': 2048,
            'top_p': 0.9,
            'top_k': 40,
            'summary_count': 10,
            'language': 'ko',
            'safety_settings': {
                'harassment': 'BLOCK_NONE',
                'hate_speech': 'BLOCK_NONE',
                'sexually_explicit': 'BLOCK_NONE',
                'dangerous_content': 'BLOCK_NONE'
            }
        },
        'telegram': {
            'max_message_length': 4000,
            'disable_preview': True,
            'parse_mode': 'Markdown',
            'retry_on_error': True,
            'send_interval': 0.5
        },
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s [%(levelname)s] %(message)s',
            'date_format': '%Y-%m-%d %H:%M:%S'
        }
    }
    
    @classmethod
    def load(cls, config_path: str = 'config.yaml', 
             use_default_on_error: bool = True) -> Dict[str, Any]:
        """
        설정 파일 로드
        
        Args:
            config_path: 설정 파일 경로
            use_default_on_error: 오류 시 기본값 사용 여부
            
        Returns:
            설정 딕셔너리
            
        Raises:
            ConfigError: 설정 검증 실패 시
        """
        # 파일 존재 확인
        config_file = Path(config_path)
        
        if not config_file.exists():
            logger.warning(f"⚠️  설정 파일 없음: {config_path}")
            if use_default_on_error:
                logger.info("📄 기본 설정 사용")
                return cls.DEFAULT_CONFIG.copy()
            else:
                raise ConfigError(f"설정 파일을 찾을 수 없습니다: {config_path}")
        
        # YAML 파싱
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ConfigError("설정 파일이 비어있습니다")
            
            logger.info(f"📄 설정 파일 로드: {config_path}")
            
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML 파싱 오류: {e}")
            if use_default_on_error:
                logger.info("📄 기본 설정 사용")
                return cls.DEFAULT_CONFIG.copy()
            else:
                raise ConfigError(f"YAML 파싱 실패: {e}")
        
        # 기본값 병합 (누락된 설정 보완)
        config = cls._merge_with_defaults(config, cls.DEFAULT_CONFIG)
        
        # 검증
        try:
            ConfigValidator.validate(config)
        except ConfigError as e:
            logger.error(f"❌ 설정 검증 실패: {e}")
            if use_default_on_error:
                logger.info("📄 기본 설정 사용")
                return cls.DEFAULT_CONFIG.copy()
            else:
                raise
        
        logger.info("✅ 설정 로드 및 검증 완료")
        return config
    
    @classmethod
    def _merge_with_defaults(cls, config: Dict[str, Any], 
                            defaults: Dict[str, Any]) -> Dict[str, Any]:
        """
        사용자 설정과 기본값 병합
        (누락된 필드를 기본값으로 채움)
        """
        result = defaults.copy()
        
        for key, value in config.items():
            if isinstance(value, dict) and key in result and isinstance(result[key], dict):
                # 중첩된 딕셔너리는 재귀적으로 병합
                result[key] = cls._merge_with_defaults(value, result[key])
            else:
                # 일반 값은 덮어쓰기
                result[key] = value
        
        return result
    
    @classmethod
    def get_rss_feeds(cls, config: Dict[str, Any]) -> Dict[str, str]:
        """
        활성화된 RSS 피드만 추출 (우선순위 순)
        
        Returns:
            {매체명: URL} 딕셔너리
        """
        feeds = config['rss_feeds']
        
        # 활성화되고 우선순위 순으로 정렬
        enabled_feeds = [
            f for f in feeds 
            if f.get('enabled', True)
        ]
        enabled_feeds.sort(key=lambda x: x.get('priority', 999))
        
        return {feed['name']: feed['url'] for feed in enabled_feeds}


def load_config(config_path: str = 'config.yaml') -> Dict[str, Any]:
    """
    설정 로드 (단축 함수)
    
    Usage:
        config = load_config()
        RSS_FEEDS = ConfigLoader.get_rss_feeds(config)
        MAX_ARTICLES = config['collection']['max_articles_per_source']
    """
    return ConfigLoader.load(config_path)


if __name__ == '__main__':
    # 테스트 코드
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("설정 로더 테스트")
    print("=" * 60)
    
    # 설정 로드
    config = load_config('config.yaml')
    
    # RSS 피드 출력
    print("\n📡 활성화된 RSS 피드:")
    feeds = ConfigLoader.get_rss_feeds(config)
    for i, (name, url) in enumerate(feeds.items(), 1):
        print(f"  {i}. {name}")
        print(f"     → {url}")
    
    # 주요 설정 출력
    print("\n⚙️  주요 설정:")
    print(f"  • 매체당 최대 기사: {config['collection']['max_articles_per_source']}개")
    print(f"  • 전체 최대 기사: {config['collection']['max_total_articles']}개")
    print(f"  • 시간 범위: {config['collection']['hours_threshold']}시간")
    print(f"  • AI 모델: {config['ai']['model']}")
    print(f"  • 요약 개수: {config['ai']['summary_count']}개")
    
    print("\n✅ 모든 테스트 통과")
