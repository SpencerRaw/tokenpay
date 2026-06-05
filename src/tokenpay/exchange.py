"""Exchange Engine for TokenPay.

Real-time pricing oracle, FLX rate calculation, cross-model conversion.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from .models import (
    FLXRate, MODEL_REGISTRY, GLOBAL_WEIGHTS, ModelInfo,
)


@dataclass
class PriceTick:
    """A single price observation."""
    model_id: str
    input_price: float
    output_price: float
    timestamp: float = field(default_factory=time.time)
    source: str = "api"  # "api", "manual", "derived"


class PricingOracle:
    """Fetches and maintains real-time pricing data.

    In production: scrapes official pricing pages or API endpoints.
    For MVP: uses hardcoded MODEL_REGISTRY with simulated price fluctuations.
    """

    def __init__(self):
        self._prices: dict[str, PriceTick] = {}
        self._last_update = 0.0
        self.refresh()

    def refresh(self):
        """Refresh all prices from sources."""
        for model_id, model in MODEL_REGISTRY.items():
            self._prices[model_id] = PriceTick(
                model_id=model_id,
                input_price=model.input_price_per_1m,
                output_price=model.output_price_per_1m,
            )
        self._last_update = time.time()

    def get_price(self, model_id: str) -> Optional[PriceTick]:
        return self._prices.get(model_id)

    def get_all_prices(self) -> dict[str, PriceTick]:
        return dict(self._prices)

    def simulate_fluctuation(self, model_id: str, change_pct: float):
        """Simulate a price change (for demo purposes)."""
        tick = self._prices.get(model_id)
        if tick:
            tick.input_price *= (1 + change_pct)
            tick.output_price *= (1 + change_pct)
            tick.timestamp = time.time()
            tick.source = "simulated"


class ExchangeEngine:
    """Core exchange: FLX rate calculation + conversion."""

    def __init__(self):
        self.oracle = PricingOracle()
        self.rate = self._calculate_rate()
        self._rate_history: list[FLXRate] = [self.rate]
        self.spread_pct = 0.01  # 1% exchange spread
        self.mint_fee_pct = 0.005  # 0.5% minting fee

    def _calculate_rate(self) -> FLXRate:
        """Calculate current FLX rate based on global weighted average.

        FLX = Σ(weight_i × avg_price_i) for all models i

        This anchors FLX to the real-world cost of compute.
        """
        components = {}
        weighted_sum = 0.0
        total_weight = 0.0

        for model_id, weight in GLOBAL_WEIGHTS.items():
            model = MODEL_REGISTRY.get(model_id)
            if not model:
                continue
            contribution = weight * model.avg_price_per_1m
            components[model_id] = contribution
            weighted_sum += contribution
            total_weight += weight

        # Normalize
        usd_per_flx = weighted_sum / total_weight if total_weight > 0 else 10.0

        return FLXRate(
            usd_per_flx=round(usd_per_flx, 4),
            components=components,
        )

    def update_rate(self) -> FLXRate:
        """Refresh prices and recalculate FLX rate."""
        self.oracle.refresh()
        self.rate = self._calculate_rate()
        self._rate_history.append(self.rate)
        if len(self._rate_history) > 1000:
            self._rate_history = self._rate_history[-1000:]
        return self.rate

    def convert(self, from_model: str, to_model: str,
                token_amount: float) -> dict:
        """Convert tokens between models at current rates.

        Args:
            from_model: Source model ID
            to_model: Target model ID
            token_amount: Number of source tokens to convert

        Returns:
            Dict with conversion details
        """
        from_model_info = MODEL_REGISTRY.get(from_model)
        to_model_info = MODEL_REGISTRY.get(to_model)

        if not from_model_info or not to_model_info:
            raise ValueError(f"Unknown model: {from_model or to_model}")

        # Step 1: Source tokens → USD value
        usd_value = (token_amount / 1_000_000) * from_model_info.output_price_per_1m

        # Step 2: Apply spread
        usd_after_spread = usd_value * (1 - self.spread_pct)

        # Step 3: USD → target tokens
        target_tokens = (usd_after_spread / to_model_info.output_price_per_1m) * 1_000_000

        # Step 4: Calculate FLX equivalents
        flx_value = self.rate.flx_per_tokens(from_model, token_amount)
        flx_after = self.rate.flx_per_tokens(to_model, target_tokens)

        return {
            "from_model": from_model,
            "to_model": to_model,
            "from_tokens": token_amount,
            "to_tokens": target_tokens,
            "usd_value": usd_value,
            "spread_pct": self.spread_pct,
            "spread_flx": flx_value * self.spread_pct,
            "flx_before": flx_value,
            "flx_after": flx_after,
            "rate": self.rate,
            "effective_rate": target_tokens / token_amount if token_amount > 0 else 0,
        }

    def get_model_rate_card(self) -> list[dict]:
        """Get current FLX exchange rates for all models."""
        cards = []
        for model_id, model in MODEL_REGISTRY.items():
            tokens_per_flx = self.rate.tokens_per_flx(model_id)
            flx_per_1m = self.rate.flx_per_tokens(model_id, 1_000_000)
            cards.append({
                "model_id": model_id,
                "name": model.name,
                "provider": model.provider,
                "input_price": model.input_price_per_1m,
                "output_price": model.output_price_per_1m,
                "tokens_per_flx": round(tokens_per_flx),
                "flx_per_1m_tokens": round(flx_per_1m, 6),
                "global_weight": GLOBAL_WEIGHTS.get(model_id, 0),
            })
        return sorted(cards, key=lambda c: c["tokens_per_flx"], reverse=True)

    def get_rate_history(self, limit: int = 50) -> list[dict]:
        """Get recent FLX rate history."""
        return [
            {"timestamp": r.timestamp, "usd_per_flx": r.usd_per_flx}
            for r in self._rate_history[-limit:]
        ]

    def simulate_market_event(self, model_id: str, change_pct: float):
        """Simulate a market event for demo."""
        self.oracle.simulate_fluctuation(model_id, change_pct)
        self.update_rate()
