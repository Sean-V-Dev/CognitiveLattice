# 🧠 TokenSight: Precision Scaffolding for LLMs

TokenSight is an experimental framework that solves one of the most overlooked problems in modern LLM design: **token drift and context overload**. Instead of brute-forcing larger context windows, TokenSight uses modular compression, intelligent routing, and secure input isolation to ensure that only the *right* data reaches the model — exactly when it’s needed.

Built for clarity, security, and extreme efficiency.

---

## 🚀 Why It Exists

Most LLM frameworks force models to reread entire context windows, wasting tokens and introducing drift or hallucinations. TokenSight was born from real frustration: after watching multiple AIs struggle to study a simple exam, the insight hit — the failure wasn’t intelligence. It was *architecture*.

This project reframes how LLMs consume input:
- **Don’t expand the window. Reroute the stream.**

---

## 🧩 Core Modules

| Module | Description |
|--------|-------------|
| `encoder/` | Converts raw text into PNG-style dictionary images for token-safe transmission |
| `decoder/` | Securely reverses image encoding to extract controlled input |
| `llm/` | Lightweight LLM that acts as librarian, gatekeeper, and summarizer |
| `memory/` | Stores summaries and contextual fragments for recall and drift prevention |
| `router/` | (Coming soon) Pre-LLM filter to intercept and redirect oversized pasted input |

---

## 🔐 Architectural Highlights

- **Token-aware intake**: Avoid wasted context — only feed models what they need
- **Secure passthrough**: Encode sensitive text into non-token formats before ingestion
- **Delegated summarization**: Lightweight LLM scaffolds memory and meaning
- **Modular by design**: Each component stands alone or integrates easily

---

## 💡 Future Modules

- Semantic drift detector  
- Overflow manager (kiddie pool logic)  
- Instruction reinforcement agent  
- Privilege-based context access  
- Visualizer dashboard for memory tracking

---

## 👋 About the Builder

Hi, I'm Sean — a systems-focused software engineering student who thinks friction points aren't bugs, they're blueprints. I built this framework during university while working full-time and raising three young kids. Turns out, curiosity beats curriculum.

I didn’t start with a plan to build a LangChain competitor — just a study helper that *didn’t get confused*. It turned into an architecture that might change how we think about token usage, security, and memory in AI design.

---

## 📌 License

MIT — open to explore, extend, improve.

---

## 🌐 Contact & More

LinkedIn coming soon. In the meantime, feel free to explore or leave feedback through GitHub Issues.
