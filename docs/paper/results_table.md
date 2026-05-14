# Results Tables (LaTeX-Ready) — v1.0 RC1

## Table 1: Main Results — Holdout Baseline Comparison (20 scenarios)

```latex
\begin{table}[h]
\centering
\caption{Session Restore Performance on Holdout Set}
\begin{tabular}{lccccccc}
\toprule
Method & Restore & Verbatim & Exact & Semantic & Tokens & Quality & Stale \\
\midrule
VCM (ours) & \textbf{0.958} & 0.675 & \textbf{0.958} & \textbf{0.650} & \textbf{65.8} & \textbf{1.917} & \textbf{0.000} \\
Full Context & 1.000 & 0.717 & 1.000 & 0.100 & 225.2 & 1.700 & 0.300 \\
RAG & 0.925 & 0.642 & 0.925 & 0.550 & 49.1 & 1.783 & 0.050 \\
Summary & 0.908 & 0.642 & 0.908 & 0.300 & 37.0 & 1.533 & 0.200 \\
RawVerbatim & 1.000 & 0.717 & 1.000 & 0.200 & 53.0 & 1.700 & 0.300 \\
StrongRAG & 1.000 & 0.717 & 1.000 & 0.250 & 137.7 & 2.000 & 0.000 \\
\bottomrule
\end{tabular}
\label{tab:main}
\end{table}
```

**Notes:**
- Restore = average of goal, decision, error recall (exact-substring)
- Verbatim = same as restore with verbatim-only matching
- Exact = restore with exact-symbol fallback (protected terms + critical gold)
- Semantic = semantic goal recall at threshold 0.75 (BGE embeddings)
- Quality = restore + keyword_coverage − stale_penalty

---

## Table 2: Component Ablations

```latex
\begin{table}[h]
\centering
\caption{Component Ablation on Holdout Set}
\begin{tabular}{lcc}
\toprule
Component Removed & $\Delta$ Restore & $\Delta$ Quality \\
\midrule
Stale filter & 0.000 & \textbf{−0.300} \\
Adaptive cap & −0.017 & −0.067 \\
Symbol vault & 0.000 & −0.025 \\
PSO & 0.000 & 0.000 \\
Reranker & 0.000 & 0.000 \\
\bottomrule
\end{tabular}
\label{tab:ablation}
\end{table}
```

---

## Table 3: Specialized Test Suites

```latex
\begin{table}[h]
\centering
\caption{Performance on Specialized Test Suites}
\begin{tabular}{lccc}
\toprule
Suite & Scenarios & Restore & Tokens \\
\midrule
Adversarial & 3 & 1.000 & 65.7 \\
Adversarial Hard & 5 & 1.000 & 60.0 \\
Real Codebase & 3 & 0.889 & 120.7 \\
Multi-Repo & 5 & 0.911 & 84.0 \\
Project Switch (H03) & 3 & 0.000 contamination & — \\
False Memory (S05) & 1 & 0.000 false rate & — \\
State Restore (I01) & 5 & 0.667 accuracy & 86.0 \\
\bottomrule
\end{tabular}
\label{tab:specialized}
\end{table}
```

---

## Table 4: Exact Symbol Recall

```latex
\begin{table}[h]
\centering
\caption{Exact Symbol Recall by Scenario Type}
\begin{tabular}{lcccc}
\toprule
Scenario & VCM & RawVerbatim & StrongRAG & Full \\
\midrule
Config key & 1.000 & 0.333 & 1.000 & 1.000 \\
API endpoint & 1.000 & 0.000 & 1.000 & 1.000 \\
CI/CD job & 1.000 & 0.667 & 0.667 & 1.000 \\
\midrule
Holdout avg & \textbf{0.930} & — & — & — \\
\bottomrule
\end{tabular}
\label{tab:exact}
\end{table}
```

---

## Table 5: Semantic Threshold Calibration

```latex
\begin{table}[h]
\centering
\caption{Semantic Matcher Threshold Calibration}
\begin{tabular}{cccc}
\toprule
Threshold & Precision & Recall & F1 \\
\midrule
0.70 & 0.158 & 1.000 & 0.273 \\
0.75 & 0.200 & 1.000 & 0.333 \\
0.80 & 0.300 & 1.000 & 0.462 \\
\bottomrule
\end{tabular}
\label{tab:semantic}
\end{table}
```
