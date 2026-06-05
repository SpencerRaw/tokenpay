"""Marketplace for TokenPay — Real-world goods & services priced in FLX.

This is where the "pizza moment" happens: the first real transaction
settled in FLX — not cross-model conversion, but actual value exchange.

Flow:
  1. Seller lists item/service with FLX price
  2. Buyer places order → FLX goes to escrow
  3. Seller delivers
  4. Buyer confirms → FLX released from escrow to seller
  5. Both parties rate each other
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ListingCategory(Enum):
    DESIGN = "🎨 Design"
    WRITING = "✍️ Writing"
    CODE = "💻 Code & Dev"
    CONSULTING = "🗣️ Consulting"
    TUTORING = "📚 Tutoring"
    DATA = "📊 Data & Analysis"
    PHYSICAL = "📦 Physical Task"
    OTHER = "🔧 Other"


class ListingStatus(Enum):
    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"


class OrderStatus(Enum):
    PENDING_ESCROW = "pending_escrow"    # FLX locked, waiting for delivery
    DELIVERED = "delivered"               # Seller delivered, waiting for buyer
    COMPLETED = "completed"               # Buyer confirmed, FLX released
    DISPUTED = "disputed"                 # Something went wrong
    CANCELLED = "cancelled"               # Escrow returned to buyer
    REFUNDED = "refunded"


@dataclass
class Listing:
    """An item or service for sale in FLX."""
    id: str = field(default_factory=lambda: f"list_{uuid.uuid4().hex[:8]}")
    seller_id: str = ""
    seller_name: str = ""
    title: str = ""
    description: str = ""
    price_flx: float = 0.0
    category: ListingCategory = ListingCategory.OTHER
    tags: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: ListingStatus = ListingStatus.ACTIVE
    views: int = 0
    order_count: int = 0

    def card(self) -> dict:
        return {
            "id": self.id,
            "seller": self.seller_name,
            "title": self.title,
            "price_flx": self.price_flx,
            "category": self.category.value,
            "tags": self.tags,
        }


@dataclass
class Order:
    """A marketplace order with escrow."""
    id: str = field(default_factory=lambda: f"ord_{uuid.uuid4().hex[:8]}")
    listing_id: str = ""
    listing_title: str = ""
    buyer_id: str = ""
    buyer_name: str = ""
    seller_id: str = ""
    seller_name: str = ""
    amount_flx: float = 0.0
    escrow_tx_id: str = ""          # The escrow transaction in the ledger
    release_tx_id: str = ""          # The release transaction
    status: OrderStatus = OrderStatus.PENDING_ESCROW
    created_at: float = field(default_factory=time.time)
    delivered_at: Optional[float] = None
    completed_at: Optional[float] = None
    buyer_note: str = ""             # Buyer's message to seller
    delivery_note: str = ""          # Seller's delivery message
    buyer_rating: int = 0            # 1-5 stars
    seller_rating: int = 0


@dataclass
class SellerProfile:
    """Reputation profile for a seller."""
    account_id: str
    name: str
    total_sales: int = 0
    total_earned_flx: float = 0.0
    avg_rating: float = 0.0
    completed_orders: int = 0
    disputed_orders: int = 0
    member_since: float = field(default_factory=time.time)


class Marketplace:
    """TokenPay marketplace for real-world FLX transactions."""

    def __init__(self):
        self.listings: dict[str, Listing] = {}
        self.orders: dict[str, Order] = {}
        self.sellers: dict[str, SellerProfile] = {}

    # --- Listings ---

    def create_listing(self, seller_id: str, seller_name: str,
                       title: str, description: str, price_flx: float,
                       category: ListingCategory = ListingCategory.OTHER,
                       tags: list[str] = None) -> Listing:
        """Create a new listing priced in FLX.

        This is the core action: someone says "I'll do X for Y FLX."
        """
        if price_flx <= 0:
            raise ValueError("Price must be positive")

        listing = Listing(
            seller_id=seller_id,
            seller_name=seller_name,
            title=title,
            description=description,
            price_flx=price_flx,
            category=category,
            tags=tags or [],
        )
        self.listings[listing.id] = listing

        # Ensure seller profile exists
        if seller_id not in self.sellers:
            self.sellers[seller_id] = SellerProfile(
                account_id=seller_id, name=seller_name
            )

        return listing

    def get_listing(self, listing_id: str) -> Optional[Listing]:
        return self.listings.get(listing_id)

    def get_active_listings(self, category: Optional[ListingCategory] = None,
                            sort_by: str = "newest") -> list[Listing]:
        """Get all active listings, optionally filtered."""
        listings = [l for l in self.listings.values() if l.status == ListingStatus.ACTIVE]

        if category:
            listings = [l for l in listings if l.category == category]

        if sort_by == "cheapest":
            listings.sort(key=lambda l: l.price_flx)
        elif sort_by == "popular":
            listings.sort(key=lambda l: l.order_count, reverse=True)
        else:  # newest
            listings.sort(key=lambda l: l.created_at, reverse=True)

        return listings

    # --- Orders ---

    def place_order(self, listing_id: str, buyer_id: str, buyer_name: str,
                    payment_engine, note: str = "") -> dict:
        """Place an order for a listing.

        1. Validates listing is active
        2. Creates escrow (FLX locked)
        3. Returns order details

        The actual FLX escrow is handled by payment_engine.escrow_transfer().
        """
        listing = self.listings.get(listing_id)
        if not listing:
            raise ValueError("Listing not found")
        if listing.status != ListingStatus.ACTIVE:
            raise ValueError("Listing is no longer active")
        if buyer_id == listing.seller_id:
            raise ValueError("Cannot buy your own listing")

        # Mark listing as sold (one listing = one buyer for simplicity)
        listing.status = ListingStatus.SOLD
        listing.order_count += 1

        # Create order
        order = Order(
            listing_id=listing.id,
            listing_title=listing.title,
            buyer_id=buyer_id,
            buyer_name=buyer_name,
            seller_id=listing.seller_id,
            seller_name=listing.seller_name,
            amount_flx=listing.price_flx,
            buyer_note=note,
        )
        self.orders[order.id] = order

        return {
            "order": order,
            "listing": listing,
            "action": "escrow_required",
            "amount_flx": listing.price_flx,
            "seller": listing.seller_name,
            "title": listing.title,
        }

    def mark_delivered(self, order_id: str, delivery_note: str = "") -> Order:
        """Seller marks the order as delivered."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.PENDING_ESCROW:
            raise ValueError(f"Order is in {order.status.value} state")

        order.status = OrderStatus.DELIVERED
        order.delivered_at = time.time()
        order.delivery_note = delivery_note
        return order

    def confirm_receipt(self, order_id: str, payment_engine,
                        buyer_rating: int = 5) -> dict:
        """Buyer confirms receipt — releases escrow to seller.

        This is the moment FLX changes hands for real value.
        """
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")
        if order.status != OrderStatus.DELIVERED:
            raise ValueError(f"Order must be delivered first (current: {order.status.value})")

        # Release escrow via payment engine
        # The escrow transaction was created when the order was placed
        from .payment import PaymentEngine

        order.status = OrderStatus.COMPLETED
        order.completed_at = time.time()
        order.buyer_rating = buyer_rating

        # Update seller profile
        seller = self.sellers.get(order.seller_id)
        if seller:
            seller.total_sales += 1
            seller.total_earned_flx += order.amount_flx
            seller.completed_orders += 1
            # Update average rating
            if seller.completed_orders > 0:
                seller.avg_rating = (
                    (seller.avg_rating * (seller.completed_orders - 1) + buyer_rating)
                    / seller.completed_orders
                )

        return {
            "order": order,
            "released_flx": order.amount_flx,
            "seller": order.seller_name,
            "rating_given": buyer_rating,
        }

    def dispute_order(self, order_id: str, reason: str = "") -> Order:
        """Open a dispute on an order."""
        order = self.orders.get(order_id)
        if not order:
            raise ValueError("Order not found")

        order.status = OrderStatus.DISPUTED

        seller = self.sellers.get(order.seller_id)
        if seller:
            seller.disputed_orders += 1

        return order

    def get_orders_for_user(self, account_id: str) -> list[Order]:
        """Get all orders where user is buyer or seller."""
        return [
            o for o in self.orders.values()
            if o.buyer_id == account_id or o.seller_id == account_id
        ]

    # --- Stats ---

    def get_stats(self) -> dict:
        """Marketplace statistics."""
        active = len(self.get_active_listings())
        completed = sum(1 for o in self.orders.values()
                       if o.status == OrderStatus.COMPLETED)
        volume = sum(o.amount_flx for o in self.orders.values()
                    if o.status == OrderStatus.COMPLETED)

        return {
            "active_listings": active,
            "total_orders": len(self.orders),
            "completed_orders": completed,
            "total_volume_flx": volume,
            "total_sellers": len(self.sellers),
        }

    def get_seller_profile(self, account_id: str) -> Optional[SellerProfile]:
        return self.sellers.get(account_id)


# --- Sample listings for demo ---

SAMPLE_LISTINGS = [
    {
        "title": "Design a logo for your AI startup",
        "description": "Custom logo design. 3 concepts, 2 revisions. Vector + PNG. 48h turnaround.",
        "price_flx": 5.0,
        "category": ListingCategory.DESIGN,
        "tags": ["logo", "branding", "startup"],
    },
    {
        "title": "Code review: Python ML pipeline",
        "description": "I'll review your ML training pipeline code. Performance, bugs, architecture feedback.",
        "price_flx": 3.0,
        "category": ListingCategory.CODE,
        "tags": ["python", "ml", "code-review"],
    },
    {
        "title": "Write a LinkedIn post about your product",
        "description": "Engaging LinkedIn post with hook, story, and CTA. Your product, my words.",
        "price_flx": 1.5,
        "category": ListingCategory.WRITING,
        "tags": ["social-media", "linkedin", "copywriting"],
    },
    {
        "title": "1-hour AI strategy consultation",
        "description": "Video call. We'll map your AI use cases, pick tools, and plan your first 90 days.",
        "price_flx": 8.0,
        "category": ListingCategory.CONSULTING,
        "tags": ["strategy", "consulting", "ai"],
    },
    {
        "title": "Clean & label your dataset (up to 1000 rows)",
        "description": "Data cleaning, deduplication, labeling. Ready for training.",
        "price_flx": 4.0,
        "category": ListingCategory.DATA,
        "tags": ["data", "cleaning", "labeling"],
    },
    {
        "title": "Pick up my dry cleaning (Causeway Bay)",
        "description": "Need someone near Causeway Bay to pick up and drop off. ~30min task.",
        "price_flx": 2.0,
        "category": ListingCategory.PHYSICAL,
        "tags": ["physical", "hong-kong", "errand"],
    },
    {
        "title": "Tutor me on Transformers architecture (1hr)",
        "description": "Explain attention mechanisms, positional encoding, and the full architecture. Beginner-friendly.",
        "price_flx": 6.0,
        "category": ListingCategory.TUTORING,
        "tags": ["tutoring", "transformers", "nlp"],
    },
    {
        "title": "Make me a matcha latte",
        "description": "I'm in Sheung Wan. Bring me a hot matcha latte. Will tip for speed.",
        "price_flx": 0.8,
        "category": ListingCategory.PHYSICAL,
        "tags": ["coffee", "physical", "hong-kong"],
    },
]
