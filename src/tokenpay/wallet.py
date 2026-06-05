"""Wallet Engine for TokenPay.

API key binding, Balance Proof, FLX minting and burning.
"""

from __future__ import annotations

import hashlib
import time
import os
from typing import Optional
from dataclasses import dataclass

from .models import (
    Account, BoundAPIKey, FLXBalance, FLXRate,
    Transaction, TransactionType, TransactionStatus,
    MODEL_REGISTRY, GLOBAL_WEIGHTS,
)
from .exchange import ExchangeEngine


@dataclass
class BalanceProof:
    """Result of a balance verification."""
    provider: str
    model_id: str
    verified: bool
    token_balance: float          # Estimated token count
    rate_limit_tpm: float = 0.0    # Tokens per minute
    error: str = ""


class WalletEngine:
    """Manages user wallets: bind keys, verify balances, mint FLX."""

    def __init__(self, exchange: ExchangeEngine):
        self.exchange = exchange
        self.accounts: dict[str, Account] = {}

    # --- Account Management ---

    def create_account(self, name: str = "") -> Account:
        """Create a new TokenPay account."""
        account = Account(name=name)
        self.accounts[account.id] = account
        return account

    def get_account(self, account_id: str) -> Optional[Account]:
        return self.accounts.get(account_id)

    # --- API Key Binding ---

    def bind_api_key(self, account: Account, provider: str,
                     model_id: str, api_key: str) -> BoundAPIKey:
        """Bind an API key to an account and verify it.

        In production: makes one lightweight API call to verify the key.
        For MVP: simulates verification with a hash.
        """
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Check for duplicate
        for existing in account.bound_keys:
            if existing.provider == provider and existing.model_id == model_id:
                raise ValueError(f"Key already bound for {provider}/{model_id}")

        # Verify balance (simulated for MVP)
        proof = self._verify_balance(provider, model_id, api_key)

        if not proof.verified:
            raise ValueError(f"API key verification failed: {proof.error}")

        bound = BoundAPIKey(
            provider=provider,
            model_id=model_id,
            key_hash=key_hash,
            verified_at=time.time(),
            verified_balance=proof.token_balance,
            spending_limit_monthly=proof.rate_limit_tpm * 60 * 24 * 30,
        )

        account.bound_keys.append(bound)
        return bound

    def _verify_balance(self, provider: str, model_id: str,
                        api_key: str) -> BalanceProof:
        """Verify an API key has real balance.

        Production: calls GET https://api.openai.com/v1/models
        with the key to check access + rate limit headers.

        For MVP: simulated verification.
        """
        # Simulate verification
        if not api_key or len(api_key) < 10:
            return BalanceProof(
                provider=provider, model_id=model_id,
                verified=False, token_balance=0,
                error="Invalid API key format",
            )

        # Key starts with provider prefix
        prefixes = {
            "openai": "sk-",
            "anthropic": "sk-ant-",
            "google": "AIza",
            "deepseek": "sk-",
            "groq": "gsk_",
        }
        expected = prefixes.get(provider, "")
        if expected and not api_key.startswith(expected):
            return BalanceProof(
                provider=provider, model_id=model_id,
                verified=False, token_balance=0,
                error=f"Key should start with '{expected}'",
            )

        # Simulate balance based on key hash (deterministic)
        hash_val = int(hashlib.sha256(api_key.encode()).hexdigest()[:8], 16)
        simulated_balance = 500_000 + (hash_val % 10_000_000)

        return BalanceProof(
            provider=provider,
            model_id=model_id,
            verified=True,
            token_balance=simulated_balance,
            rate_limit_tpm=100_000 + (hash_val % 500_000),
        )

    # --- FLX Minting ---

    def mint_flx(self, account: Account, model_id: str,
                 token_amount: float) -> Transaction:
        """Mint FLX from verified token balance.

        Converts verified API token balance into FLX.
        The tokens are "locked" in your API account (still yours, still usable)
        but TokenPay issues FLX backed by that balance.
        """
        # Find the bound key for this model
        bound_key = None
        for bk in account.bound_keys:
            if bk.model_id == model_id:
                bound_key = bk
                break

        if not bound_key:
            raise ValueError(f"No verified API key for model {model_id}")

        # Check if enough balance
        current_flx = self.exchange.rate.flx_per_tokens(model_id, token_amount)
        if current_flx <= 0:
            raise ValueError(f"Cannot mint 0 FLX")

        # Check against spending limit
        already_minted = self._get_minted_for_model(account, model_id)
        if already_minted + token_amount > bound_key.spending_limit_monthly:
            raise ValueError(
                f"Exceeds monthly limit. "
                f"Minted: {already_minted/1e6:.1f}M, "
                f"Requesting: {token_amount/1e6:.1f}M, "
                f"Limit: {bound_key.spending_limit_monthly/1e6:.1f}M tokens"
            )

        # Update balances
        account.flx_balance.total_flx += current_flx
        account.flx_balance.minted_total += current_flx
        account.flx_balance.available_flx = (
            account.flx_balance.total_flx - account.flx_balance.locked_flx
        )
        account.transaction_count += 1

        # Record transaction
        tx = Transaction(
            tx_type=TransactionType.MINT,
            from_account="",
            to_account=account.id,
            amount_flx=current_flx,
            rate_snapshot=self.exchange.rate,
            status=TransactionStatus.COMPLETED,
            memo=f"Mint {token_amount/1e6:.2f}M {model_id} tokens → {current_flx:.4f} FLX",
        )

        return tx

    def burn_flx(self, account: Account, flx_amount: float,
                 target_model: str) -> Transaction:
        """Burn FLX back into API tokens.

        Converts FLX back to spendable API tokens.
        """
        if account.flx_balance.available_flx < flx_amount:
            raise ValueError(
                f"Insufficient FLX. Have: {account.flx_balance.available_flx:.4f}, "
                f"Need: {flx_amount:.4f}"
            )

        token_amount = self.exchange.rate.tokens_per_flx(target_model) * flx_amount

        account.flx_balance.total_flx -= flx_amount
        account.flx_balance.burned_total += flx_amount
        account.flx_balance.available_flx = (
            account.flx_balance.total_flx - account.flx_balance.locked_flx
        )
        account.transaction_count += 1

        tx = Transaction(
            tx_type=TransactionType.BURN,
            from_account=account.id,
            to_account="",
            amount_flx=flx_amount,
            rate_snapshot=self.exchange.rate,
            status=TransactionStatus.COMPLETED,
            memo=f"Burn {flx_amount:.4f} FLX → {token_amount/1e6:.2f}M {target_model} tokens",
        )

        return tx

    def _get_minted_for_model(self, account: Account, model_id: str) -> float:
        """Get total tokens already minted for a model (from ledger)."""
        # Simplified: for MVP, track via bound key
        # In production: query ledger
        return 0.0  # MVP: no tracking yet

    # --- Account Summary ---

    def get_summary(self, account: Account) -> dict:
        """Get account summary for dashboard."""
        models_breakdown = []
        total_usd_value = 0.0

        for bk in account.bound_keys:
            model = MODEL_REGISTRY.get(bk.model_id)
            if model:
                usd_val = (bk.verified_balance / 1_000_000) * model.avg_price_per_1m
                flx_val = self.exchange.rate.flx_per_tokens(
                    bk.model_id, bk.verified_balance
                )
                models_breakdown.append({
                    "model": bk.model_id,
                    "provider": bk.provider,
                    "tokens": bk.verified_balance,
                    "usd_value": usd_val,
                    "flx_value": flx_val,
                })
                total_usd_value += usd_val

        return {
            "account_id": account.id,
            "name": account.name,
            "flx_balance": account.flx_balance.total_flx,
            "flx_available": account.flx_balance.available_flx,
            "flx_locked": account.flx_balance.locked_flx,
            "total_usd_value": total_usd_value,
            "models": models_breakdown,
            "bound_keys": len(account.bound_keys),
            "transaction_count": account.transaction_count,
        }
