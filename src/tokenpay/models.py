"""Data models for TokenPay."""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# --- FLX: The AI Reserve Currency ---

@dataclass
class ModelProvider:
    """A supported AI model provider."""
    id: str                     # "openai", "anthropic", "google", "deepseek"
    name: str                   # "OpenAI", "Anthropic"
    models: list[ModelInfo] = field(default_factory=list)


@dataclass
class ModelInfo:
    """A specific model with pricing."""
    id: str                     # "gpt-4o", "claude-sonnet-4-20250514"
    provider: str               # "openai"
    name: str                   # "GPT-4o"
    input_price_per_1m: float   # USD per 1M input tokens
    output_price_per_1m: float  # USD per 1M output tokens
    avg_price_per_1m: float = 0.0

    def __post_init__(self):
        if self.avg_price_per_1m == 0.0:
            # Weighted: 70% input, 30% output (typical usage ratio)
            self.avg_price_per_1m = (
                self.input_price_per_1m * 0.7 + self.output_price_per_1m * 0.3
            )


# Real pricing data (June 2026)
MODEL_REGISTRY = {
    "gpt-4o": ModelInfo("gpt-4o", "openai", "GPT-4o", 2.50, 10.00),
    "gpt-4.1": ModelInfo("gpt-4.1", "openai", "GPT-4.1", 2.00, 8.00),
    "gpt-4.1-mini": ModelInfo("gpt-4.1-mini", "openai", "GPT-4.1 Mini", 0.40, 1.60),
    "claude-opus-4": ModelInfo("claude-opus-4", "anthropic", "Claude Opus 4", 15.00, 75.00),
    "claude-sonnet-4": ModelInfo("claude-sonnet-4", "anthropic", "Claude Sonnet 4", 3.00, 15.00),
    "claude-haiku-4": ModelInfo("claude-haiku-4", "anthropic", "Claude Haiku 4", 0.80, 4.00),
    "gemini-2.5-pro": ModelInfo("gemini-2.5-pro", "google", "Gemini 2.5 Pro", 1.25, 10.00),
    "gemini-2.5-flash": ModelInfo("gemini-2.5-flash", "google", "Gemini 2.5 Flash", 0.15, 0.60),
    "deepseek-v3": ModelInfo("deepseek-v3", "deepseek", "DeepSeek V3", 0.27, 1.10),
    "deepseek-r1": ModelInfo("deepseek-r1", "deepseek", "DeepSeek R1", 0.55, 2.19),
    "llama-4-groq": ModelInfo("llama-4-groq", "groq", "Llama 4 (Groq)", 0.30, 0.90),
}

# Global daily consumption weights (estimated, June 2026)
GLOBAL_WEIGHTS = {
    "gpt-4o": 0.28,
    "gpt-4.1": 0.12,
    "claude-sonnet-4": 0.18,
    "claude-opus-4": 0.05,
    "gemini-2.5-pro": 0.12,
    "deepseek-v3": 0.18,
    "deepseek-r1": 0.03,
    "llama-4-groq": 0.04,
}


# --- Account & Wallet ---

@dataclass
class BoundAPIKey:
    """An API key bound to a TokenPay account."""
    provider: str              # "openai", "anthropic", etc.
    model_id: str              # "gpt-4o", etc.
    key_hash: str              # SHA256 of API key (never store raw key)
    verified_at: float         # When last verified
    verified_balance: float    # Verified token count
    spending_limit_monthly: float = 0.0  # Max tokens/month from API
    status: str = "active"     # active, expired, revoked


@dataclass
class FLXBalance:
    """A user's FLX balance."""
    total_flx: float = 0.0
    locked_flx: float = 0.0         # Reserved as backing for converted tokens
    available_flx: float = 0.0
    minted_total: float = 0.0       # Lifetime FLX minted
    burned_total: float = 0.0       # Lifetime FLX burned (converted back)

    def __post_init__(self):
        self.available_flx = self.total_flx - self.locked_flx


@dataclass
class Account:
    """A TokenPay user account."""
    id: str = field(default_factory=lambda: f"tp_{uuid.uuid4().hex[:12]}")
    name: str = ""
    created_at: float = field(default_factory=time.time)
    bound_keys: list[BoundAPIKey] = field(default_factory=list)
    flx_balance: FLXBalance = field(default_factory=FLXBalance)
    transaction_count: int = 0

    def total_usd_value(self, exchange_rate: FLXRate) -> float:
        return self.flx_balance.total_flx * exchange_rate.usd_per_flx


# --- Exchange Rates ---

@dataclass
class FLXRate:
    """Current FLX exchange rate."""
    usd_per_flx: float          # USD value of 1 FLX
    timestamp: float = field(default_factory=time.time)
    components: dict[str, float] = field(default_factory=dict)  # model_id → contribution

    def tokens_per_flx(self, model_id: str) -> float:
        """How many tokens of a model 1 FLX can buy."""
        model = MODEL_REGISTRY.get(model_id)
        if not model:
            return 0.0
        return (self.usd_per_flx / model.output_price_per_1m) * 1_000_000

    def flx_per_tokens(self, model_id: str, token_count: float) -> float:
        """How much FLX a given token balance is worth."""
        model = MODEL_REGISTRY.get(model_id)
        if not model:
            return 0.0
        usd_value = (token_count / 1_000_000) * model.avg_price_per_1m
        return usd_value / self.usd_per_flx


# --- Transactions ---

class TransactionType(Enum):
    MINT = "mint"              # Balance → FLX
    BURN = "burn"              # FLX → Balance
    TRANSFER = "transfer"       # FLX between accounts
    CONVERT = "convert"        # Cross-model exchange
    LOCK = "lock"              # Lock FLX as backing
    UNLOCK = "unlock"          # Release backing

class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


@dataclass
class Transaction:
    """A single transaction on the TokenPay network."""
    id: str = field(default_factory=lambda: f"tx_{uuid.uuid4().hex[:16]}")
    tx_type: TransactionType = TransactionType.TRANSFER
    from_account: str = ""
    to_account: str = ""
    amount_flx: float = 0.0
    rate_snapshot: Optional[FLXRate] = None
    status: TransactionStatus = TransactionStatus.PENDING
    timestamp: float = field(default_factory=time.time)
    memo: str = ""
    settlement_hash: str = ""


@dataclass
class LiquidityPool:
    """TokenPay's internal liquidity pool for cross-model settlement."""
    id: str = "liquidity_pool"
    balances: dict[str, float] = field(default_factory=dict)  # model_id → FLX
    total_liquidity_flx: float = 0.0
    providers: list[str] = field(default_factory=list)  # account IDs providing liquidity
    yield_rate: float = 0.03  # 3% APY for providers
