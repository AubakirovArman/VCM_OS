# VCM-OS: Event-Sourced Context Management for LLM Agents

## Abstract

Large language model (LLM) agents suffer from context window limitations and catastrophic forgetting during long-running development sessions. We present **VCM-OS**, an event-sourced context management system that maintains a structured memory of goals, decisions, errors, and project state across sessions. VCM-OS achieves **95.8% session restore accuracy** with **63.4 tokens** per context pack—**4.9× fewer tokens** than full-context baselines—while maintaining zero stale-fact contamination and zero cross-project memory leakage. Key innovations include: (1) a typed memory schema with 8 semantic categories; (2) hybrid retrieval (dense + sparse) with Reciprocal Rank Fusion; (3) an Exact Symbol Vault for protected terms; (4) stale-fact suppression via validity tracking; and (5) a compact inline assembly format that reduces tokens by 19% without quality loss. We evaluate on 52 synthetic and real-codebase scenarios, including adversarial tests with 20+ distractors, and demonstrate live integration with a 31B-parameter model.

## Keywords

Context management, LLM agents, session restoration, memory systems, retrieval-augmented generation

## Core Contributions

1. **Event-sourced typed memory**: Structured capture of 8 memory types (intent, decision, goal, error, bug, file, procedure, constraint) with validity tracking and supersession chains.
2. **Hybrid retrieval with RRF**: Combines dense vector similarity with sparse BM25 via Reciprocal Rank Fusion, achieving robust retrieval across paraphrase and exact-match queries.
3. **Exact Symbol Vault**: SQLite-backed vault with fuzzy matching that protects critical terms (API endpoints, config keys, CI/CD jobs) from truncation.
4. **Stale suppression**: Automatic filtering of deprecated/superseded facts, improving quality by 0.300 (ablation-confirmed).
5. **Compact assembly**: Inline format (`g=`, `d=`, `b=`) reduces tokens by 19% while preserving all critical information.
6. **Live workflow integration**: End-to-end CLI adapter for Gemma 4 31B demonstrating real-world usability.
