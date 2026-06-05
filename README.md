> 🌐 [中文](README.zh-CN.md) | **English**

# TokenPay 💳

**The Settlement Layer of the AI Economy** — Universal wallet, FLX currency, cross-model payments.

## What Is TokenPay?

TokenPay is the payment network for AI tokens. Bind your OpenAI, Anthropic, Google, and DeepSeek API keys. TokenPay verifies your real balances and mints FLX — a universal settlement unit backed by actual compute. Send FLX. Receive FLX. Convert between any model at real-time rates.

**The first payment system where the currency is intelligence.**

## Quick Start

```bash
git clone https://github.com/SpencerRaw/tokenpay.git
cd tokenpay
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## Project Structure

```
tokenpay/
├── PLAN.md                   # Full product plan
├── README.md / README.zh-CN.md
├── requirements.txt
├── app/
│   └── streamlit_app.py      # Wallet dashboard
├── src/tokenpay/
│   ├── models.py             # Data models
│   ├── wallet.py             # API binding + balance proof + FLX minting
│   ├── exchange.py           # Real-time pricing oracle + FLX conversion
│   ├── ledger.py             # Transaction log + audit trail
│   └── payment.py            # Transfer, settlement, escrow
└── data/
```

## License

MIT

---

*Token is the new money. Compute is the new gold.*
