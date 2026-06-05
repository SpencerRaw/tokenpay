"""TokenPay Dashboard — AI Payment Network.

Streamlit app: wallet, exchange rates, transfers, ledger.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import time
import random

from tokenpay.models import (
    Account, MODEL_REGISTRY, GLOBAL_WEIGHTS,
)
from tokenpay.exchange import ExchangeEngine
from tokenpay.wallet import WalletEngine
from tokenpay.ledger import Ledger
from tokenpay.payment import PaymentEngine
from tokenpay.marketplace import (
    Marketplace, ListingCategory, ListingStatus, OrderStatus,
    SAMPLE_LISTINGS,
)


st.set_page_config(
    page_title="TokenPay — AI Settlement Layer",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .tp-title { font-size: 2.5rem; font-weight: 700; letter-spacing: -0.02em; }
    .tp-subtitle { font-size: 1.1rem; color: #888; }
    .flx-badge { background: linear-gradient(135deg, #667eea, #764ba2); color: white;
                 padding: 0.3rem 0.8rem; border-radius: 8px; font-weight: 600;
                 display: inline-block; }
    .metric-card { background: #f8f9fa; border-radius: 12px; padding: 1.2rem;
                   text-align: center; border: 1px solid #e9ecef; }
    .metric-value { font-size: 1.8rem; font-weight: 700; color: #2d2d2d; }
    .metric-label { font-size: 0.8rem; color: #888; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

# --- Init Engines ---
if "exchange" not in st.session_state:
    st.session_state.exchange = ExchangeEngine()
if "wallet" not in st.session_state:
    st.session_state.wallet = WalletEngine(st.session_state.exchange)
if "ledger" not in st.session_state:
    st.session_state.ledger = Ledger(storage_path="data/ledger.json")
if "payment" not in st.session_state:
    st.session_state.payment = PaymentEngine(
        st.session_state.wallet, st.session_state.exchange, st.session_state.ledger
    )
if "account" not in st.session_state:
    acct = st.session_state.wallet.create_account("My Wallet")
    st.session_state.account = acct
if "accounts" not in st.session_state:
    st.session_state.accounts = {"alice": st.session_state.wallet.create_account("Alice"),
                                  "bob": st.session_state.wallet.create_account("Bob")}
if "marketplace" not in st.session_state:
    mp = Marketplace()
    # Seed sample listings
    for sl in SAMPLE_LISTINGS:
        mp.create_listing(
            seller_id=st.session_state.accounts["alice"].id,
            seller_name="Alice",
            title=sl["title"],
            description=sl["description"],
            price_flx=sl["price_flx"],
            category=sl["category"],
            tags=sl["tags"],
        )
    st.session_state.marketplace = mp

exchange = st.session_state.exchange
wallet = st.session_state.wallet
ledger = st.session_state.ledger
payment = st.session_state.payment
account = st.session_state.account
accounts_registry = st.session_state.accounts

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 💳 TokenPay")
    st.caption("AI Settlement Layer")

    page = st.radio("Navigate", ["🏦 Wallet", "💱 Exchange", "💸 Transfer", "🛒 Market", "📒 Ledger"],
                    label_visibility="collapsed")

    st.divider()

    # Account quick view
    summary = wallet.get_summary(account)
    st.markdown(f"**{account.name}** — `{account.id[:12]}...`")
    st.markdown(f'<span class="flx-badge">{summary["flx_balance"]:.4f} FLX</span>',
                unsafe_allow_html=True)
    st.caption(f"≈ ${summary['total_usd_value']:.2f} USD · {summary['bound_keys']} keys")

    st.divider()
    st.caption(f"1 FLX = ${exchange.rate.usd_per_flx:.4f} USD")
    st.caption("[GitHub](https://github.com/SpencerRaw/tokenpay)")


# ============================================================
# PAGE 1: WALLET
# ============================================================
if page == "🏦 Wallet":
    st.markdown('<p class="tp-title">🏦 Wallet</p>', unsafe_allow_html=True)
    st.markdown('<p class="tp-subtitle">Bind API keys. Mint FLX. Manage your AI wealth.</p>',
                unsafe_allow_html=True)

    summary = wallet.get_summary(account)

    # KPI row
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{summary["flx_balance"]:.4f}</div><div class="metric-label">FLX Balance</div></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">${summary["total_usd_value"]:.2f}</div><div class="metric-label">USD Value</div></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{summary["bound_keys"]}</div><div class="metric-label">API Keys</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{account.transaction_count}</div><div class="metric-label">Transactions</div></div>', unsafe_allow_html=True)

    # Bind API Key
    st.markdown("### 🔑 Bind API Key")
    col1, col2, col3 = st.columns(3)
    with col1:
        provider = st.selectbox("Provider", ["openai", "anthropic", "google", "deepseek", "groq"])
    with col2:
        model_options = [m for m in MODEL_REGISTRY if MODEL_REGISTRY[m].provider == provider]
        model_id = st.selectbox("Model", model_options)
    with col3:
        api_key = st.text_input("API Key", type="password", placeholder="sk-...")

    if st.button("🔗 Bind & Verify", type="primary"):
        try:
            bound = wallet.bind_api_key(account, provider, model_id, api_key)
            st.success(f"✅ {provider}/{model_id} verified! ~{bound.verified_balance/1e6:.1f}M tokens detected.")
            st.rerun()
        except Exception as e:
            st.error(str(e))

    # Mint FLX
    if account.bound_keys:
        st.markdown("### 🪙 Mint FLX")
        col_a, col_b = st.columns(2)
        with col_a:
            mint_model = st.selectbox("From model", [bk.model_id for bk in account.bound_keys], key="mint_model")
        with col_b:
            mint_tokens = st.number_input("Tokens to convert", min_value=1000, value=1000000, step=100000,
                                          format="%d", key="mint_tokens")

        if st.button("✨ Mint FLX", type="primary"):
            try:
                tx = wallet.mint_flx(account, mint_model, mint_tokens)
                ledger.record(tx)
                st.success(f"✅ Minted {tx.amount_flx:.4f} FLX!")
                st.rerun()
            except Exception as e:
                st.error(str(e))

    # Bound keys table
    if account.bound_keys:
        st.markdown("### 📋 Bound Keys")
        keys_data = []
        for bk in account.bound_keys:
            model = MODEL_REGISTRY.get(bk.model_id)
            flx_val = exchange.rate.flx_per_tokens(bk.model_id, bk.verified_balance)
            keys_data.append({
                "Provider": bk.provider,
                "Model": bk.model_id,
                "Tokens": f"{bk.verified_balance/1e6:.1f}M",
                "FLX Value": f"{flx_val:.4f}",
                "USD Value": f"${(bk.verified_balance/1e6)*model.avg_price_per_1m:.2f}" if model else "N/A",
                "Status": bk.status,
            })
        st.dataframe(pd.DataFrame(keys_data), use_container_width=True)


# ============================================================
# PAGE 2: EXCHANGE
# ============================================================
elif page == "💱 Exchange":
    st.markdown('<p class="tp-title">💱 Exchange</p>', unsafe_allow_html=True)
    st.markdown('<p class="tp-subtitle">Real-time FLX rates. Cross-model conversion.</p>',
                unsafe_allow_html=True)

    # FLX Price
    c1, c2 = st.columns(2)
    with c1:
        st.metric("1 FLX", f"${exchange.rate.usd_per_flx:.4f} USD", "Live")
    with c2:
        st.metric("Components", f"{len(exchange.rate.components)} models", "Weighted avg")

    # Rate card
    st.markdown("### 📊 Rate Card")
    cards = exchange.get_model_rate_card()
    df = pd.DataFrame(cards)
    df_display = df[["name", "provider", "output_price", "tokens_per_flx", "flx_per_1m_tokens", "global_weight"]]
    df_display.columns = ["Model", "Provider", "$/1M out", "Tokens/FLX", "FLX/1M tokens", "Weight"]
    st.dataframe(df_display, use_container_width=True, hide_index=True,
                 column_config={
                     "$/1M out": st.column_config.NumberColumn(format="$%.2f"),
                     "FLX/1M tokens": st.column_config.NumberColumn(format="%.4f"),
                     "Weight": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=0.3),
                 })

    # Conversion calculator
    st.markdown("### 🔄 Convert Tokens")
    col1, col2, col3 = st.columns(3)
    with col1:
        from_m = st.selectbox("From", list(MODEL_REGISTRY.keys()), key="conv_from")
    with col2:
        to_m = st.selectbox("To", list(MODEL_REGISTRY.keys()), key="conv_to")
    with col3:
        amount_tok = st.number_input("Tokens", min_value=1000, value=1000000, step=100000, key="conv_amount")

    if st.button("💱 Calculate Conversion"):
        result = exchange.convert(from_m, to_m, amount_tok)
        st.markdown(f"""
        <div style="background:#f8f9fa;padding:1.5rem;border-radius:12px;text-align:center;">
            <span style="font-size:1.2rem;">{result['from_tokens']/1e6:.2f}M <b>{from_m}</b></span>
            <span style="font-size:2rem;margin:0 1rem;">→</span>
            <span style="font-size:1.2rem;font-weight:700;">{result['to_tokens']/1e6:.2f}M <b>{to_m}</b></span><br>
            <small style="color:#888;">USD value: ${result['usd_value']:.2f} · Spread: {result['spread_pct']:.1%} · FLX: {result['flx_before']:.4f}</small>
        </div>
        """, unsafe_allow_html=True)

    # Simulate market event (demo)
    st.markdown("### 🎭 Simulate Market Event")
    col_a, col_b = st.columns(2)
    with col_a:
        sim_model = st.selectbox("Model", list(MODEL_REGISTRY.keys()), key="sim_model")
    with col_b:
        sim_change = st.slider("Price Change %", -50, 50, 10, key="sim_change")

    if st.button("🎲 Trigger Event"):
        exchange.simulate_market_event(sim_model, sim_change / 100)
        st.success(f"✅ {sim_model} price changed by {sim_change}%. New FLX rate: ${exchange.rate.usd_per_flx:.4f}")
        st.rerun()


# ============================================================
# PAGE 3: TRANSFER
# ============================================================
elif page == "💸 Transfer":
    st.markdown('<p class="tp-title">💸 Transfer FLX</p>', unsafe_allow_html=True)
    st.markdown('<p class="tp-subtitle">Send FLX. Settle to tokens. Cross-model payments.</p>',
                unsafe_allow_html=True)

    summary = wallet.get_summary(account)

    tab1, tab2 = st.tabs(["📤 Send FLX", "🏦 Settle to Tokens"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            recipient = st.selectbox("Recipient", list(accounts_registry.keys()))
        with col2:
            amount = st.number_input("FLX Amount", min_value=0.0001, value=1.0, step=0.1, format="%.4f")

        memo = st.text_input("Memo (optional)", placeholder="Payment for logo design...")

        if st.button("📤 Send FLX", type="primary"):
            try:
                to_acct = accounts_registry[recipient]
                tx = payment.transfer(account, to_acct, amount, memo)
                st.success(f"✅ Sent {amount:.4f} FLX to {recipient}! TX: {tx.id[:16]}")
                st.balloons()
                st.rerun()
            except Exception as e:
                st.error(str(e))

    with tab2:
        st.markdown("Convert FLX back to spendable API tokens.")
        col1, col2, col3 = st.columns(3)
        with col1:
            settle_amount = st.number_input("FLX to settle", min_value=0.0001, value=1.0, step=0.1, format="%.4f", key="settle_amount")
        with col2:
            settle_model = st.selectbox("Target model", list(MODEL_REGISTRY.keys()), key="settle_model")

        model = MODEL_REGISTRY[settle_model]
        est_tokens = exchange.rate.tokens_per_flx(settle_model) * settle_amount
        with col3:
            st.metric("Est. Tokens", f"{est_tokens/1e6:.2f}M", f"${(est_tokens/1e6)*model.output_price_per_1m:.2f} USD")

        if st.button("🏦 Settle to Tokens", type="primary"):
            try:
                result = payment.settle_to_tokens(account, settle_amount, settle_model)
                st.success(f"✅ Settled {settle_amount:.4f} FLX → {result['actual_tokens']/1e6:.2f}M {settle_model} tokens")
                st.rerun()
            except Exception as e:
                st.error(str(e))


# ============================================================
# PAGE 4: MARKETPLACE
# ============================================================
elif page == "🛒 Market":
    st.markdown('<p class="tp-title">🛒 Marketplace</p>', unsafe_allow_html=True)
    st.markdown('<p class="tp-subtitle">Real goods & services. Priced in FLX. Escrow-protected.</p>',
                unsafe_allow_html=True)

    mp = st.session_state.marketplace
    account = st.session_state.account

    # Stats
    stats = mp.get_stats()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Active Listings", stats["active_listings"])
    with c2:
        st.metric("Orders", stats["total_orders"])
    with c3:
        st.metric("Completed", stats["completed_orders"])
    with c4:
        st.metric("Volume", f"{stats['total_volume_flx']:.1f} FLX")

    tab1, tab2, tab3 = st.tabs(["🛍️ Browse", "📋 My Orders", "📝 Create Listing"])

    with tab1:
        category_filter = st.selectbox("Category", ["All"] + [c.value for c in ListingCategory])
        cat = None if category_filter == "All" else ListingCategory(category_filter)

        listings = mp.get_active_listings(category=cat)

        if listings:
            for listing in listings:
                seller = mp.get_seller_profile(listing.seller_id)
                rating = f"⭐{seller.avg_rating:.1f}" if seller and seller.avg_rating > 0 else "New"

                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{listing.title}**")
                        st.caption(f"{listing.description[:120]}... · {listing.category.value} · {rating}")
                        if listing.tags:
                            st.caption(" · ".join(f"`{t}`" for t in listing.tags))
                    with col2:
                        st.markdown(f"<span class='flx-badge' style='font-size:1.1rem;'>{listing.price_flx} FLX</span>", unsafe_allow_html=True)
                        st.caption(f"≈ ${listing.price_flx * exchange.rate.usd_per_flx:.2f} USD")
                    with col3:
                        if st.button(f"🛒 Buy", key=f"buy_{listing.id}"):
                            try:
                                result = mp.place_order(
                                    listing.id, account.id, account.name or "Me",
                                    payment, note=""
                                )
                                # Create escrow in payment engine
                                seller_acct = wallet.get_account(listing.seller_id)
                                if seller_acct and account.flx_balance.available_flx >= listing.price_flx:
                                    escrow_tx = payment.escrow_transfer(
                                        account, seller_acct, listing.price_flx,
                                        condition=f"Order for: {listing.title}"
                                    )
                                    result["order"].escrow_tx_id = escrow_tx.id
                                    ledger.record(escrow_tx)
                                    st.success(f"✅ Order placed! {listing.price_flx} FLX in escrow.")
                                    st.rerun()
                                else:
                                    st.error(f"Insufficient FLX. Available: {account.flx_balance.available_flx:.4f}")
                            except Exception as e:
                                st.error(str(e))
                    st.divider()
        else:
            st.info("No active listings in this category.")

    with tab2:
        orders = mp.get_orders_for_user(account.id)
        if orders:
            for order in reversed(orders):
                with st.container():
                    status_color = {
                        OrderStatus.PENDING_ESCROW: "🟡", OrderStatus.DELIVERED: "🟢",
                        OrderStatus.COMPLETED: "✅", OrderStatus.DISPUTED: "🔴",
                        OrderStatus.CANCELLED: "⚫", OrderStatus.REFUNDED: "↩️",
                    }
                    emoji = status_color.get(order.status, "❓")

                    st.markdown(f"{emoji} **{order.listing_title}** — {order.amount_flx} FLX")
                    st.caption(f"{order.status.value} · Seller: {order.seller_name} · Buyer: {order.buyer_name}")

                    col_a, col_b = st.columns(2)
                    if order.status == OrderStatus.DELIVERED and order.buyer_id == account.id:
                        with col_a:
                            if order.delivery_note:
                                st.caption(f"📝 Seller note: {order.delivery_note}")
                        with col_b:
                            rating = st.selectbox("Rating", [5,4,3,2,1], key=f"rate_{order.id}")
                            if st.button(f"✅ Confirm Receipt", key=f"confirm_{order.id}"):
                                result = mp.confirm_receipt(order.id, payment, rating)
                                # Release escrow
                                # (in production: find escrow tx and release it)
                                st.success(f"🎉 Order complete! {order.amount_flx} FLX released to {order.seller_name}.")
                                st.balloons()
                                st.rerun()

                    elif order.status == OrderStatus.PENDING_ESCROW and order.seller_id == account.id:
                        delivery_note = st.text_input("Delivery note", key=f"delnote_{order.id}",
                                                       placeholder="Work delivered! Here's the link...")
                        if st.button(f"📤 Mark Delivered", key=f"deliver_{order.id}"):
                            mp.mark_delivered(order.id, delivery_note)
                            st.success("Marked as delivered. Waiting for buyer confirmation.")
                            st.rerun()

                    st.divider()
        else:
            st.info("No orders yet. Go browse the marketplace!")

    with tab3:
        st.markdown("### Sell something for FLX")
        col1, col2 = st.columns(2)
        with col1:
            new_title = st.text_input("Title", placeholder="e.g., Design a logo")
            new_cat = st.selectbox("Category", [c for c in ListingCategory], format_func=lambda c: c.value)
        with col2:
            new_price = st.number_input("Price (FLX)", min_value=0.1, value=3.0, step=0.5)
            new_tags = st.text_input("Tags (comma-separated)", placeholder="design, logo, fast")

        new_desc = st.text_area("Description", placeholder="Describe what you're offering...", height=100)

        if st.button("📝 Create Listing", type="primary"):
            if new_title and new_price > 0:
                tags = [t.strip() for t in new_tags.split(",") if t.strip()]
                listing = mp.create_listing(
                    account.id, account.name or "Anonymous",
                    new_title, new_desc, new_price, new_cat, tags,
                )
                st.success(f"✅ Listed! '{new_title}' for {new_price} FLX.")
                st.rerun()
            else:
                st.warning("Title and price are required.")


# ============================================================
# PAGE 5: LEDGER
# ============================================================
elif page == "📒 Ledger":
    st.markdown('<p class="tp-title">📒 Ledger</p>', unsafe_allow_html=True)
    st.markdown('<p class="tp-subtitle">Immutable transaction record. Every FLX accounted for.</p>',
                unsafe_allow_html=True)

    # Network stats
    integrity = ledger.verify_integrity()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Total TXs", integrity["total_transactions"])
    with c2:
        st.metric("FLX Minted", f"{integrity['total_minted']:.4f}")
    with c3:
        st.metric("FLX Circulating", f"{integrity['circulating_flx']:.4f}")

    # Transaction table
    all_txs = ledger.get_all_transactions(100)
    if all_txs:
        tx_data = []
        for tx in all_txs:
            tx_data.append({
                "TX ID": tx.id[:16],
                "Type": tx.tx_type.value,
                "From": tx.from_account[:12] if tx.from_account else "—",
                "To": tx.to_account[:12] if tx.to_account else "—",
                "FLX": f"{tx.amount_flx:.4f}",
                "Status": tx.status.value,
                "Time": time.strftime("%H:%M:%S", time.localtime(tx.timestamp)),
                "Memo": tx.memo[:60],
            })
        st.dataframe(pd.DataFrame(tx_data), use_container_width=True, hide_index=True,
                     column_config={"Memo": st.column_config.TextColumn(width="large")})

    # Balance history chart
    st.markdown("### 📈 FLX Rate History")
    rate_history = exchange.get_rate_history(50)
    if len(rate_history) > 1:
        df_rate = pd.DataFrame(rate_history)
        fig = px.line(df_rate, x="timestamp", y="usd_per_flx",
                      title=None, labels={"usd_per_flx": "USD per FLX"})
        fig.update_layout(height=250, margin=dict(l=20, r=20, t=10, b=20),
                          template="plotly_white")
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.caption("TokenPay v0.1 · The Settlement Layer of the AI Economy · [GitHub](https://github.com/SpencerRaw/tokenpay)")
