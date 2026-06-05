"""Payment Engine for TokenPay.

FLX transfers, cross-model settlement, escrow.
"""

from __future__ import annotations

import time
from typing import Optional

from .models import (
    Account, Transaction, TransactionType, TransactionStatus,
    MODEL_REGISTRY,
)
from .wallet import WalletEngine
from .exchange import ExchangeEngine
from .ledger import Ledger


class PaymentEngine:
    """Handles FLX transfers and settlements between accounts."""

    def __init__(self, wallet: WalletEngine, exchange: ExchangeEngine,
                 ledger: Ledger):
        self.wallet = wallet
        self.exchange = exchange
        self.ledger = ledger

    def transfer(self, from_account: Account, to_account: Account,
                 amount_flx: float, memo: str = "") -> Transaction:
        """Transfer FLX from one account to another.

        This is the core payment primitive of TokenPay.
        """
        if amount_flx <= 0:
            raise ValueError("Amount must be positive")

        if from_account.flx_balance.available_flx < amount_flx:
            raise ValueError(
                f"Insufficient FLX. Available: {from_account.flx_balance.available_flx:.4f}, "
                f"Requested: {amount_flx:.4f}"
            )

        # Debit sender
        from_account.flx_balance.total_flx -= amount_flx
        from_account.flx_balance.available_flx = (
            from_account.flx_balance.total_flx - from_account.flx_balance.locked_flx
        )
        from_account.transaction_count += 1

        # Credit receiver
        to_account.flx_balance.total_flx += amount_flx
        to_account.flx_balance.available_flx = (
            to_account.flx_balance.total_flx - to_account.flx_balance.locked_flx
        )
        to_account.transaction_count += 1

        # Record
        tx = Transaction(
            tx_type=TransactionType.TRANSFER,
            from_account=from_account.id,
            to_account=to_account.id,
            amount_flx=amount_flx,
            rate_snapshot=self.exchange.rate,
            status=TransactionStatus.COMPLETED,
            memo=memo,
        )
        self.ledger.record(tx)

        return tx

    def settle_to_tokens(self, account: Account, flx_amount: float,
                         target_model: str) -> dict:
        """Settle FLX into actual API tokens.

        In production: TokenPay uses its own API balance to fulfill.
        The user's FLX is burned and TokenPay's liquidity pool provides tokens.
        """
        if account.flx_balance.available_flx < flx_amount:
            raise ValueError(f"Insufficient FLX: {account.flx_balance.available_flx:.4f}")

        model = MODEL_REGISTRY.get(target_model)
        if not model:
            raise ValueError(f"Unknown model: {target_model}")

        # Calculate token amount
        token_amount = self.exchange.rate.tokens_per_flx(target_model) * flx_amount

        # Apply spread
        spread_flx = flx_amount * self.exchange.spread_pct
        actual_flx = flx_amount - spread_flx
        actual_tokens = self.exchange.rate.tokens_per_flx(target_model) * actual_flx

        # Burn FLX
        account.flx_balance.total_flx -= flx_amount
        account.flx_balance.burned_total += flx_amount
        account.flx_balance.available_flx = (
            account.flx_balance.total_flx - account.flx_balance.locked_flx
        )

        # In production: issue API tokens via our liquidity pool
        # For MVP: return the settlement details

        tx = Transaction(
            tx_type=TransactionType.CONVERT,
            from_account=account.id,
            to_account="liquidity_pool",
            amount_flx=flx_amount,
            rate_snapshot=self.exchange.rate,
            status=TransactionStatus.COMPLETED,
            memo=f"Settle {flx_amount:.4f} FLX → {actual_tokens/1e6:.2f}M {target_model} tokens",
        )
        self.ledger.record(tx)
        account.transaction_count += 1

        return {
            "flx_amount": flx_amount,
            "spread_flx": spread_flx,
            "actual_flx": actual_flx,
            "target_model": target_model,
            "gross_tokens": token_amount,
            "actual_tokens": actual_tokens,
            "usd_value": (actual_tokens / 1_000_000) * model.output_price_per_1m,
            "tx_id": tx.id,
        }

    def escrow_transfer(self, from_account: Account, to_account: Account,
                        amount_flx: float, condition: str = "",
                        timeout_seconds: float = 3600) -> Transaction:
        """Create an escrow — FLX held until condition met.

        For multi-party transactions: "release when work is done."
        """
        if from_account.flx_balance.available_flx < amount_flx:
            raise ValueError("Insufficient FLX")

        # Lock FLX in sender's account
        from_account.flx_balance.locked_flx += amount_flx
        from_account.flx_balance.available_flx = (
            from_account.flx_balance.total_flx - from_account.flx_balance.locked_flx
        )

        tx = Transaction(
            tx_type=TransactionType.LOCK,
            from_account=from_account.id,
            to_account=to_account.id,
            amount_flx=amount_flx,
            rate_snapshot=self.exchange.rate,
            status=TransactionStatus.PENDING,
            memo=f"Escrow: {condition} (timeout: {timeout_seconds}s)",
        )
        self.ledger.record(tx)
        from_account.transaction_count += 1

        return tx

    def release_escrow(self, escrow_tx: Transaction) -> Transaction:
        """Release an escrow — unlock FLX and send to receiver."""
        if escrow_tx.status != TransactionStatus.PENDING:
            raise ValueError("Escrow is not pending")

        from_acct = self.wallet.get_account(escrow_tx.from_account)
        to_acct = self.wallet.get_account(escrow_tx.to_account)

        if not from_acct or not to_acct:
            raise ValueError("Account not found")

        # Unlock
        from_acct.flx_balance.locked_flx -= escrow_tx.amount_flx

        # Transfer
        result_tx = self.transfer(
            from_acct, to_acct, escrow_tx.amount_flx,
            memo=f"Escrow released: {escrow_tx.memo}",
        )

        # Mark escrow as completed
        escrow_tx.status = TransactionStatus.COMPLETED

        return result_tx
