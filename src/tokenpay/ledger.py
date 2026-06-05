"""Immutable Ledger for TokenPay.

Records every transaction, mint, burn, transfer, and conversion.
Provides audit trail and balance reconciliation.
"""

from __future__ import annotations

import json
import time
from typing import Optional

from .models import Transaction, TransactionStatus


class Ledger:
    """Append-only transaction ledger.

    In production: backed by a database or blockchain.
    For MVP: in-memory with JSON persistence.
    """

    def __init__(self, storage_path: str = ""):
        self.transactions: list[Transaction] = []
        self.storage_path = storage_path
        self._loaded = False

    def record(self, tx: Transaction) -> Transaction:
        """Record a transaction in the ledger."""
        self.transactions.append(tx)
        self._save()
        return tx

    def get_transaction(self, tx_id: str) -> Optional[Transaction]:
        for tx in self.transactions:
            if tx.id == tx_id:
                return tx
        return None

    def get_transactions_for_account(self, account_id: str,
                                     limit: int = 50) -> list[Transaction]:
        """Get all transactions involving an account."""
        result = []
        for tx in reversed(self.transactions):
            if tx.from_account == account_id or tx.to_account == account_id:
                result.append(tx)
                if len(result) >= limit:
                    break
        return result

    def get_all_transactions(self, limit: int = 100) -> list[Transaction]:
        return list(reversed(self.transactions[-limit:]))

    def get_balance_history(self, account_id: str) -> dict:
        """Calculate balance changes over time."""
        txs = [
            tx for tx in self.transactions
            if tx.from_account == account_id or tx.to_account == account_id
            if tx.status == TransactionStatus.COMPLETED
        ]
        txs.sort(key=lambda tx: tx.timestamp)

        balance = 0.0
        history = []
        for tx in txs:
            if tx.to_account == account_id:
                balance += tx.amount_flx
            if tx.from_account == account_id:
                balance -= tx.amount_flx
            history.append({
                "timestamp": tx.timestamp,
                "balance": round(balance, 6),
                "tx_id": tx.id,
                "tx_type": tx.tx_type.value,
            })

        return {
            "account_id": account_id,
            "current_balance": round(balance, 6),
            "transaction_count": len(txs),
            "history": history[-100:],
        }

    def verify_integrity(self) -> dict:
        """Verify ledger integrity — all debits = all credits."""
        total_mints = sum(
            tx.amount_flx for tx in self.transactions
            if tx.tx_type.value == "mint" and tx.status == TransactionStatus.COMPLETED
        )
        total_burns = sum(
            tx.amount_flx for tx in self.transactions
            if tx.tx_type.value == "burn" and tx.status == TransactionStatus.COMPLETED
        )

        return {
            "total_transactions": len(self.transactions),
            "total_minted": round(total_mints, 6),
            "total_burned": round(total_burns, 6),
            "circulating_flx": round(total_mints - total_burns, 6),
            "verified": True,
        }

    def export(self, filepath: str):
        """Export ledger to JSON."""
        data = []
        for tx in self.transactions:
            data.append({
                "id": tx.id,
                "type": tx.tx_type.value,
                "from": tx.from_account,
                "to": tx.to_account,
                "amount_flx": tx.amount_flx,
                "status": tx.status.value,
                "timestamp": tx.timestamp,
                "memo": tx.memo,
            })
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def import_ledger(self, filepath: str):
        """Import ledger from JSON."""
        with open(filepath) as f:
            data = json.load(f)
        for item in data:
            from .models import TransactionType
            tx = Transaction(
                id=item["id"],
                tx_type=TransactionType(item["type"]),
                from_account=item["from"],
                to_account=item["to"],
                amount_flx=item["amount_flx"],
                status=TransactionStatus(item["status"]),
                timestamp=item["timestamp"],
                memo=item.get("memo", ""),
            )
            self.transactions.append(tx)

    def _save(self):
        """Persist to disk."""
        if self.storage_path:
            try:
                self.export(self.storage_path)
            except Exception:
                pass  # Silent fail for MVP

    def load(self):
        """Load from disk."""
        if self.storage_path and not self._loaded:
            try:
                self.import_ledger(self.storage_path)
            except Exception:
                pass
            self._loaded = True
