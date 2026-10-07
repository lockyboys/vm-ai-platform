ENV_PATH = BASE_DIR / ".env"

# 환경변수 로드
load_dotenv(dotenv_path=ENV_PATH, override=True)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "bge-m3")

# Tavily 검색 도구 초기화 (키가 있을 경우에만 활성화)
