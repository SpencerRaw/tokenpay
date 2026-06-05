> 🌐 [English](README.md) | **中文**

# TokenPay 通付 💳

**AI经济的清算层**——统一钱包、FLX货币、跨模型支付。

## 这是什么？

TokenPay 是 AI token 的支付网络。绑定你的 OpenAI、Anthropic、Google、DeepSeek API 密钥。TokenPay 验证你的真实余额，铸造成 FLX——以真实算力为锚定的统一结算单位。发送 FLX。接收 FLX。按实时汇率在任意模型间兑换。

**第一个以智能为储备货币的支付系统。**

## 快速开始

```bash
git clone https://github.com/SpencerRaw/tokenpay.git
cd tokenpay
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

## 项目结构

```
tokenpay/
├── PLAN.md                   # 完整产品计划
├── README.md / README.zh-CN.md
├── requirements.txt
├── app/
│   └── streamlit_app.py      # 钱包仪表盘
├── src/tokenpay/
│   ├── models.py             # 数据模型
│   ├── wallet.py             # API绑定 + 余额证明 + FLX铸造
│   ├── exchange.py           # 实时定价预言机 + FLX兑换
│   ├── ledger.py             # 交易账本 + 审计追踪
│   └── payment.py            # 转账、结算、托管
└── data/
```

## 许可证

MIT

---

*Token 是新货币。算力是新黄金。*
