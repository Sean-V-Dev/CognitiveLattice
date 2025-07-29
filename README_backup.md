# 🧠 TokenSight: Token Discipline for Intelligent Inference

**TokenSight** is a modular framework that tackles one of the root causes of LLM drift, hallucination, and inefficiency: uncontrolled token usage.

Rather than expanding context windows or stacking memory blobs, TokenSight implements surgical input management — selectively compressing, encrypting, and routing information to ensure only the *right* data reaches a large model, at the *right* time.

Its mission is simple:  
> 🔍 *Watch every token. Limit waste. Maximize meaning.*

---

## 🚀 Why It Exists

Most LLM architectures suffer from token sprawl:
- Context windows flooded with raw input
- Unfiltered task data bleeding into unrelated inference
- Sensitive content exposed before it’s needed

**TokenSight prevents this** by introducing a buffer layer — a secure staging ground where input is cleaned, chunked, and *summarized by a small local LLM* before entering the attention-heavy realm of a larger model.

This results in:
- ✅ Reduced hallucination
- ✅ Sharpened attention
- ✅ Enhanced privacy
- ✅ Lower token consumption

You don’t need bigger windows.  
You need better doors.

---

## 🧩 Pipeline Modules

| Module        | Description                                                                 |
|---------------|-----------------------------------------------------------------------------|
| `encoder/`    | Converts cleaned text into encrypted image artifacts (uses XOR for demo)    |
| `decoder/`    | Recovers plaintext from image artifacts, validating semantic fidelity       |
| `utils/`      | Handles dictionary logic, input cleanup, and chunk fidelity scoring         |
| `main.py`     | Full-cycle orchestration: encode → decode → summarize → store               |
| `llm_server/` | Lightweight LLaMA server interface for chunk summarization                  |
| `memory/`     | Retains summaries for retrieval, searching, and context scaffolding         |
| `config/`     | Holds encryption key and customizable chunking parameters                   |

Planned additions:
- `router/`: Pre-LLM input interceptor and dispatch manager
- `redactor/`: Rule-based content filter for sensitive context exposure

---

## 🔐 Core Design Philosophy

TokenSight treats input like a **hazmat material** — not because data is dangerous, but because careless exposure is.

- 🔥 **No raw input enters the big LLM unexamined**
- 🧠 **Small LLM acts as a security guard, deciding what gets passed on**
- 🖼️ **Encrypted image transmission keeps input cold until explicitly decoded**
    ⚠️ TokenSight currently uses a basic XOR-based encryption for proof of concept. While it successfully obscures input and verifies decode integrity, it is not suitable for secure production use. Future versions will support stronger cryptographic standards (e.g., AES, Fernet), environment-based key handling, and compliance-aware input processing.

- 🧮 **Chunking optimizes token footprint — no bloated context windows**
- 🧬 **Redaction rules allow for selective privacy: redact, truncate, or reject**

In short:  
> 📦 *The big LLM sees nothing until the small one says it’s safe.*

---

## 🎯 Milestone: Chapter-Level Summary Success

- ✔️ Successfully processed Chapter 1 of *Pride and Prejudice*
- ✔️ 100+ lines sanitized, encrypted, chunked, and summarized
- ✔️ Fidelity validated >99% on encode/decode
- ✔️ Summaries were accurate, tone-aware, and contextually rich

Memory log and agent behavior matched expectations for scalable multi-chunk input handling.

---

## 🛠️ Future Enhancements

- Context chaining between chunk summaries
- Multi-chapter document inference with persistent memory
- Semantic search across memory blocks
- PDF ingestion with compliance filtering
- CLI and API interface for secure input management

---

## 👋 About the Builder

Hi, I’m Sean — a systems architect with a passion for frictionless design. TokenSight wasn’t born to compete with LangChain or replicate AutoGPT — it was built to solve one quiet, persistent problem: why do smart models burn tokens like they’re free?

As a parent, student, and full-time engineer, I believe architecture is intelligence. I’m building frameworks that respect context, compression, and collaboration.

---

## 📜 License

MIT — fork freely, contribute generously, break things carefully.

---

## 🌐 Contact

LinkedIn coming soon.  
Feel free to open issues or drop feedback directly in the repo.
