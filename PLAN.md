# TokenPay — Product Plan

> **Tagline**: The settlement layer of the AI economy.
> **Status**: Concept / MVP (pre-seed)
> **Last updated**: 2026-06-05

---

## 1. Thesis

The AI industry has a currency problem: every model provider issues their own tokens, siloed in separate accounts. GPT-4 tokens cannot buy Claude inference. Claude tokens cannot pay a designer. A designer's invoice cannot be settled in compute.

This is exactly the problem banking solved in the 15th century — when every city-state minted its own coins and merchants couldn't trade across borders without money changers taking 20% cuts.

**TokenPay is the SWIFT of the AI economy.** It introduces FLX — a universal settlement unit backed by real compute — and a payment network that connects every AI wallet into a single addressable system.

---

## 2. What TokenPay Does

### Layer 1: Unified Wallet
```
Bind your API keys (OpenAI, Anthropic, Google, DeepSeek, ...)
        ↓
TokenPay verifies your real token balances
        ↓
One dashboard: total value in FLX, per-model breakdown
```

### Layer 2: FLX — The AI Reserve Currency
```
FLX is backed by real compute. Not by faith. Not by a government.

1 FLX = weighted average of 1 million output tokens across major models,
        weighted by global daily consumption volume.

As models get cheaper (more tokens per dollar), FLX naturally appreciates.
```

### Layer 3: Payment Network
```
Alice sends 50 FLX to Bob.
Bob converts 30 FLX to Claude tokens, keeps 20 FLX.
The 30 FLX is settled through TokenPay's liquidity pool:
  → TokenPay uses its Claude API balance to fulfill Bob
  → Alice's GPT-4 balance is "reserved" as backing
  → TokenPay earns 1% spread on the exchange
```

---

## 3. FLX — The Unit of Account

### Definition
```
FLX = Σ (model_weight × token_price_per_million_output) / normalization

Where:
  model_weight = model's share of global daily token consumption
  token_price = API list price for output tokens (USD/1M tokens)
```

### Initial FLX Components (June 2026)

| Model | Daily Volume (est.) | $/1M out | Weight | Contribution |
|-------|-------------------|----------|--------|-------------|
| GPT-4o | 500B tokens | $10.00 | 30% | $3.00 |
| GPT-4.1 | 200B | $8.00 | 12% | $0.96 |
| Claude Sonnet 4 | 300B | $15.00 | 18% | $2.70 |
| Claude Opus 4 | 80B | $75.00 | 5% | $3.75 |
| Gemini 2.5 Pro | 200B | $10.00 | 12% | $1.20 |
| DeepSeek V3 | 400B | $1.10 | 24% | $0.26 |
| Llama 4 (via Groq) | 100B | $0.90 | 6% | $0.05 |
| Other | 100B | varied | 3% | $0.30 |

**1 FLX ≈ $12.22 USD** (weighted average of 1M output tokens across all models)

### FLX Exchange Rates

| Model | Tokens per 1 FLX |
|-------|-----------------|
| GPT-4o (output) | ~1,222,000 |
| Claude Opus (output) | ~163,000 |
| Claude Sonnet (output) | ~815,000 |
| DeepSeek V3 (output) | ~11,100,000 |
| Gemini 2.5 Pro (output) | ~1,222,000 |

---

## 4. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    TOKENPAY LAYERS                        │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Payment Network (REST/WS)             │   │
│  │  transfer(FLX) · settle() · invoice() · escrow()  │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────┼───────────────────────────┐   │
│  │              Exchange Engine                      │   │
│  │  price_oracle() · convert() · arbitrage_guard()   │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────┼───────────────────────────┐   │
│  │              Wallet Layer                          │   │
│  │  bind_key() · proof_of_balance() · mint_FLX()     │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│  ┌──────────────────────┼───────────────────────────┐   │
│  │              Ledger (immutable)                    │   │
│  │  Every transaction, settlement, mint recorded      │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  External APIs: OpenAI · Anthropic · Google · DeepSeek  │
└─────────────────────────────────────────────────────────┘
```

### Balance Proof (Proof of Token)

TokenPay never holds your API key long-term. It issues a **Balance Certificate**:

```
1. User provides API key (client-side, encrypted)
2. TokenPay makes ONE minimal API call (list models / check rate limit)
3. API returns: "You have access to GPT-4o, rate limit 500K TPM"
4. TokenPay records: "This key has GPT-4o access, verified at timestamp T"
5. User can now mint FLX up to their verified monthly spending limit
6. API key is discarded — only the certificate remains
```

### Settlement Engine

When User A sends FLX to User B and B wants Claude tokens:

```
1. B requests: "convert 30 FLX to Claude tokens"
2. Exchange computes: 30 FLX × 815K = 24.45M Claude Sonnet tokens
3. TokenPay uses its own Anthropic API key to credit B's account
4. A's GPT-4 balance is "locked" as backing (A can still use it,
   but if A's balance drops below locked amount, FLX is recalled)
5. TokenPay earns 0.3 FLX spread (1%)
```

---

## 5. Use Cases

### Case A: Freelancer Paid in Compute
```
Designer completes logo → Client pays ¥3000 in FLX
Designer needs to run a big Stable Diffusion batch tonight
→ Converts FLX to GPU compute credits (via RunPod/Replicate API)
→ No fiat conversion. No bank. Pure compute economy.
```

### Case B: Cross-Model Arbitrage
```
GPT-4.1 price drops 30% overnight (OpenAI promotion)
→ TokenPay oracle detects the shift
→ Alice's FLX is now worth 30% more GPT-4.1 tokens
→ Bob borrows FLX, buys cheap GPT-4.1 tokens, holds until price recovers
→ Like forex, but the underlying asset is intelligence
```

### Case C: API Liquidity Pool
```
DeepSeek is cheap but slow. GPT-4o is fast but expensive.
TokenPay's liquidity pool holds both.
Users can borrow from the pool (paying interest in FLX).
Liquidity providers earn yield.
```

---

## 6. Revenue Model

| Stream | Rate | When |
|--------|------|------|
| Exchange spread | 1% | Every cross-model conversion |
| Transfer fee | 0.1% | FLX transfers between users |
| Liquidity pool yield | 0.5% spread | Borrowers pay, providers earn |
| Enterprise API | $0.001/transaction | High-volume settlement |
| FLX issuance | 0.5% minting fee | New FLX minted from fresh API balance |

---

## 7. Economics of FLX

### Why FLX Appreciates

```
Year 0: 1 FLX = 1M GPT-4 tokens (GPT-4 = state of art)
Year 1: GPT-5 released, GPT-4 becomes cheaper
        → Same 1 FLX now buys 2M GPT-4 tokens
        → OR: 1 FLX buys 500K GPT-5 tokens (access to better intelligence)
        
FLX holders benefit from:
  1. Model commoditization (old models get cheaper)
  2. Compute efficiency (same intelligence needs fewer FLX)
  3. Network growth (more users → more FLX demand → price rises)
```

### Deflationary by Design

Unlike fiat (inflationary by design) or Bitcoin (artificially capped), FLX is **naturally deflationary** because:

- Moore's Law for AI: compute gets ~40% cheaper per year
- Model compression: GPT-4-level intelligence needs 10× fewer tokens each generation
- Network effects: more FLX users → more liquidity → tighter spreads → lower friction → more adoption

---

## 8. Competitive Landscape

| | TokenPay | OpenRouter | Venice (VVV) | Crypto Wallets |
|---|---|---|---|---|
| **Concept** | AI settlement layer | Model router | AI token | Crypto storage |
| **Cross-model** | ✅ Core | ❌ Routes only | ❌ | ❌ |
| **Balance proof** | ✅ | ❌ | ❌ | ❌ |
| **FLX currency** | ✅ | ❌ | VVV token | Various |
| **Backed by** | Real compute | None | Staking | Consensus |
| **P2P payment** | ✅ | ❌ | ❌ | ✅ |
| **Enterprise** | Settlement API | API proxy | Staking rewards | Wallet |

---

## 9. MVP Scope (This Repository)

### a) Concept & Architecture
→ PLAN.md + bilingual READMEs

### b) Core Engine
```
src/tokenpay/
├── models.py      # Data models: Account, Transaction, FLXBalance, ExchangeRate
├── wallet.py      # API key binding, balance verification, FLX minting
├── exchange.py    # Real-time pricing oracle, FLX conversion engine
├── ledger.py      # Transaction log, balance tracking, audit trail
├── payment.py     # Transfer, settlement, escrow
```

### c) Dashboard (Streamlit)
```
app/
└── streamlit_app.py     # Wallet dashboard:
                          - Bind API keys / view balances in FLX
                          - Live exchange rates
                          - Send FLX to another account
                          - Transaction history
```

---

## 10. Roadmap

| Phase | Milestone |
|-------|-----------|
| **Phase 0** (NOW) | Concept + prototype (this repo) |
| **Phase 1** | Working wallet: bind real API keys, verify balances, mint FLX |
| **Phase 2** | Live exchange: real-time pricing from 5+ providers |
| **Phase 3** | P2P payments: FLX transfers between verified accounts |
| **Phase 4** | Liquidity pool: borrow/lend FLX, earn yield |
| **Phase 5** | Enterprise API: settlement-as-a-service |
| **Phase 6** | Regulatory framework: partner with banks for fiat on/off ramp |

---

## 11. Why TokenPay Will Exist

Someone will build this. The question is who.

- Visa and Mastercard are watching. They know payment networks.
- Stripe is probably prototyping this already.
- OpenAI and Anthropic benefit from a shared settlement layer (less friction = more usage).
- Every AI-powered business will eventually need to pay and be paid in compute.

The first-mover advantage in AI payments is massive — because once tokens flow through your network, switching costs are as high as switching banks.

---

## 12. Inspirations

- **SWIFT** — Proved cross-border settlement works at global scale
- **Stripe** — Proved developer-first payments win
- **Uniswap** — Proved automated market making works
- **Visa** — Proved a 0.1% fee on trillions of transactions is a license to print money
- **Gold Standard** — Proved that backing a currency with a real asset creates trust
