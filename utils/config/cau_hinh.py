"""
cau_hinh.py — Read and Validate All KAIROS Configuration

Priority order (highest to lowest):
    1. System environment variables (os.environ)
    2. .env file at project root (searched upward automatically)
    3. Hardcoded defaults below

No other file needs to call load_dotenv().
This module handles it once at import time.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import logging


# ─── Locate and load .env (once) ─────────────────────────────────────────────
def _find_dotenv() -> Optional[Path]:
    """Walk parent directories to find .env file."""
    current = Path(__file__).resolve()
    for parent in [current, *current.parents]:
        candidate = parent / ".env"
        if candidate.exists():
            return candidate
    return None


def _parse_dotenv_manual(path: Path) -> None:
    """Fallback: parse .env manually when python-dotenv is not installed."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            
            # CHỈ cắt comment nếu dấu '#' đứng sau một khoảng trắng (inline comment chuẩn)
            if " #" in v:
                v = v.split(" #")[0]
                
            v = v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


_dotenv_path = _find_dotenv()
try:
    from dotenv import load_dotenv as _load_dotenv
    if _dotenv_path:
        _load_dotenv(dotenv_path=_dotenv_path, override=False)
        logging.info(f"a08: loaded configuration from {_dotenv_path}")
    else:
        _load_dotenv(override=False)
except ImportError:
    # python-dotenv not installed — parse .env manually
    if _dotenv_path:
        _parse_dotenv_manual(_dotenv_path)


def _env(key: str, default: str = "") -> str:
    """Get environment variable, return default if absent."""
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(_env(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(_env(key, str(default)))
    except ValueError:
        return default


# ─── Configuration dataclasses ───────────────────────────────────────────────

@dataclass
class LLMConfig:
    """Large Language Model provider configuration."""
    provider: str      = field(default_factory=lambda: _env("LANGCHAIN_PROVIDER", "groq"))
    model_name: str    = field(default_factory=lambda: _env("LANGCHAIN_MODEL_NAME", "llama-3.3-70b-versatile"))
    temperature: float = field(default_factory=lambda: _env_float("LANGCHAIN_TEMPERATURE", 0.0))

    # API Keys by provider
    groq_api_key: str      = field(default_factory=lambda: _env("GROQ_API_KEY"))
    openrouter_api_key: str= field(default_factory=lambda: _env("OPENROUTER_API_KEY"))
    deepseek_api_key: str  = field(default_factory=lambda: _env("DEEPSEEK_API_KEY"))
    openai_api_key: str    = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    gemini_api_key: str    = field(default_factory=lambda: _env("GEMINI_API_KEY"))
    custom_api_key: str    = field(default_factory=lambda: _env("CUSTOM_API_KEY", "no-key"))

    # Base URLs by provider
    groq_base_url: str       = field(default_factory=lambda: _env("GROQ_BASE_URL", "https://api.groq.com/openai/v1"))
    openrouter_base_url: str = field(default_factory=lambda: _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    deepseek_base_url: str   = field(default_factory=lambda: _env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"))
    openai_base_url: str     = field(default_factory=lambda: _env("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    gemini_base_url: str     = field(default_factory=lambda: _env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"))
    ollama_base_url: str     = field(default_factory=lambda: _env("OLLAMA_BASE_URL", "http://localhost:11434/v1"))
    custom_base_url: str     = field(default_factory=lambda: _env("CUSTOM_BASE_URL", "http://localhost:8000/v1"))

    def get_api_key_for(self, provider: str) -> str:
        """Return API key for the given provider."""
        mapping = {
            "groq":       self.groq_api_key,
            "openrouter": self.openrouter_api_key,
            "deepseek":   self.deepseek_api_key,
            "openai":     self.openai_api_key,
            "gemini":     self.gemini_api_key,
            "ollama":     "ollama",
            "custom":     self.custom_api_key,
        }
        return mapping.get(provider, self.groq_api_key)

    @property
    def api_key(self) -> str:
        """Return API key for the currently active provider."""
        return self.get_api_key_for(self.provider)

    def get_base_url_for(self, provider: str) -> str:
        """Return base URL for the given provider."""
        mapping = {
            "groq":       self.groq_base_url,
            "openrouter": self.openrouter_base_url,
            "deepseek":   self.deepseek_base_url,
            "openai":     self.openai_base_url,
            "gemini":     self.gemini_base_url,
            "ollama":     self.ollama_base_url,
            "custom":     self.custom_base_url,
        }
        return mapping.get(provider, self.groq_base_url)

    @property
    def base_url(self) -> str:
        """Return base URL for the currently active provider."""
        return self.get_base_url_for(self.provider)

    def to_openai_kwargs(self) -> dict:
        """Return kwargs dict for OpenAI client."""
        return {"api_key": self.api_key, "base_url": self.base_url}


@dataclass
class DataConfig:
    """Market data source configuration."""
    # OKX (Crypto)
    okx_api_key: str    = field(default_factory=lambda: _env("OKX_API_KEY"))
    okx_secret: str     = field(default_factory=lambda: _env("OKX_SECRET"))
    okx_passphrase: str = field(default_factory=lambda: _env("OKX_PASSPHRASE"))
    okx_flag: str       = field(default_factory=lambda: _env("OKX_FLAG", "1"))  # 0=live, 1=demo

    # Binance (Crypto)
    binance_api_key: str = field(default_factory=lambda: _env("BINANCE_API_KEY"))
    binance_secret: str  = field(default_factory=lambda: _env("BINANCE_SECRET"))

    # Bybit (Crypto)
    bybit_api_key: str   = field(default_factory=lambda: _env("BYBIT_API_KEY"))
    bybit_secret: str    = field(default_factory=lambda: _env("BYBIT_SECRET"))

    # vnstock (no key needed by default)
    vnstock_source: str = field(default_factory=lambda: _env("VNSTOCK_SOURCE", "VCI"))

    # CCXT source (default: binance)
    ccxt_exchange: str  = field(default_factory=lambda: _env("CCXT_EXCHANGE", "binance"))

    # Default data source
    default_source: str = field(default_factory=lambda: _env("DEFAULT_DATA_SOURCE", "auto"))


@dataclass
class SystemConfig:
    """System operational parameters."""
    # Timeout & retry
    timeout_seconds: int = field(default_factory=lambda: _env_int("TIMEOUT_SECONDS", 120))
    max_retries: int     = field(default_factory=lambda: _env_int("MAX_RETRIES", 2))

    # Swarm / Multi-agent
    swarm_worker_timeout: int  = field(default_factory=lambda: _env_int("SWARM_WORKER_TIMEOUT", 300))
    swarm_worker_max_iter: int = field(default_factory=lambda: _env_int("SWARM_WORKER_MAX_ITER", 50))
    swarm_max_workers: int     = field(default_factory=lambda: _env_int("SWARM_MAX_WORKERS", 4))
    token_threshold: int       = field(default_factory=lambda: _env_int("TOKEN_THRESHOLD", 40000))

    # Server ports
    backend_port: int  = field(default_factory=lambda: _env_int("BACKEND_PORT", 8900))
    frontend_port: int = field(default_factory=lambda: _env_int("FRONTEND_PORT", 5900))

    # PubSub / Redis
    pubsub_backend: str = field(default_factory=lambda: _env("PUBSUB_BACKEND", "in_process"))
    redis_host: str     = field(default_factory=lambda: _env("REDIS_HOST", "localhost"))
    redis_port: int     = field(default_factory=lambda: _env_int("REDIS_PORT", 6379))

    # Environment
    debug: bool = field(default_factory=lambda: _env("DEBUG", "false").lower() in ("true", "1", "yes", "t"))
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))


@dataclass
class KairosConfig:
    """
    Single unified configuration object for KAIROS.

    Usage:
        from utils.config import cfg
        cfg.llm.api_key          # active provider API key
        cfg.llm.base_url         # active provider base URL
        cfg.data.okx_api_key
        cfg.system.timeout_seconds
    """
    llm: LLMConfig     = field(default_factory=LLMConfig)
    data: DataConfig   = field(default_factory=DataConfig)
    system: SystemConfig = field(default_factory=SystemConfig)

    def __post_init__(self):
        self._validate()

    def _validate(self) -> None:
        """Basic configuration check at startup."""
        if not self.llm.api_key:
            import warnings
            warnings.warn(
                f"⚠️  a08: No API key found for provider '{self.llm.provider}'. "
                f"Check .env file or environment variables.",
                UserWarning,
                stacklevel=3,
            )

    def summary(self) -> str:
        """Print summary of current configuration (API keys masked)."""
        lines = [
            "═══ KAIROS CONFIG SUMMARY ═══",
            f"LLM Provider : {self.llm.provider}",
            f"LLM Model    : {self.llm.model_name}",
            f"LLM Temp     : {self.llm.temperature}",
            f"LLM Base URL : {self.llm.base_url}",
            f"LLM API Key  : {'*' * 8 + self.llm.api_key[-4:] if len(self.llm.api_key) > 4 else '(not set)'}",
            "─────────────────────────────",
            f"OKX API      : {'✅ Set' if self.data.okx_api_key else '❌ Not set'}",
            f"Data Source  : {self.data.default_source}",
            "─────────────────────────────",
            f"Backend Port : {self.system.backend_port}",
            f"Frontend Port: {self.system.frontend_port}",
            f"Timeout      : {self.system.timeout_seconds}s",
            f"Max Workers  : {self.system.swarm_max_workers}",
            f"Debug        : {self.system.debug}",
            "═════════════════════════════",
        ]
        return "\n".join(lines)


# ─── Singleton instance ───────────────────────────────────────────────────────
# Created once at import — shared across all modules
cfg = KairosConfig()

if __name__ == "__main__":
    print(cfg.summary())
