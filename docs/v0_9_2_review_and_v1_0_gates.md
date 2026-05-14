# VCM-OS v0.9.2 External Review & v1.0 Gate Definition

> **Date:** 2026-05-10  
> **Source:** Independent analysis of v0.9.2 results  
> **Status:** Review complete, v1.0 gates defined

---

## Executive Summary

**MemPal/RawVerbatim benchmark к VCM-OS применим не теоретически, а уже практически.** Вы встроили его как baseline в v0.9.2 и получили честное сравнение. Теперь главный вопрос уже не "можем ли использовать этот benchmark?", а **"доказывает ли v0.9.2, что structured VCM лучше сильного raw-verbatim retrieval?"**

**Ответ: частично да, но не полностью.**

---

## VCM-OS v0.9.2 стал намного убедительнее

Теперь у вас есть:

```text
VCM vs RawVerbatim
VCM vs StrongRAG
VCM vs Full Context
verbatim restore
exact-symbol fallback restore
semantic restore
threshold ablation
tuning win count
```

Это правильно. Но результат не означает, что VCM уже окончательно победил RawVerbatim.

### Главный честный вывод

```text
VCM лучше RawVerbatim там, где нужна структура:
- stale suppression
- project state
- multi-fact state restoration
- decision/state organization

RawVerbatim лучше VCM там, где важны:
- token efficiency
- raw exact text preservation
- некоторые exact-symbol scenarios
```

---

## Что теперь реально доказано

### 1. RawVerbatim benchmark применим

**Да.** Он применим как **обязательный baseline**.

v0.9.2 реализовал RawVerbatim baseline: raw events хранятся verbatim, retrieval использует dense + sparse + keyword boost + temporal boost + exact-symbol boost, а pack — chronological raw text dump без structured sections. StrongRAG тоже реализован как RAG + BM25 + metadata filters + rerank + stale-aware postprocess.

Это ровно то, что нужно было взять из MemPal benchmark: не просто "обычный RAG", а **сильный raw baseline**.

### 2. Exact-symbol fallback нельзя использовать как главный score

Это теперь доказано вашими же результатами.

На holdout:

```text
VCM:         1.000
RawVerbatim: 1.000
StrongRAG:   1.000
Full:        1.000
```

Но это происходит из-за exact-symbol fallback, и документ прямо говорит: **all methods get 1.000 via fallback**, значит score inflated.

**Вывод:**

```text
exact-symbol fallback полезен как diagnostic,
но нельзя публиковать его как основной restore metric.
```

Основной отчёт должен показывать отдельно:

```text
verbatim_restore
semantic_restore
exact_symbol_fallback_restore
decision_restore
project_state_restore
rationale_restore
```

### 3. Verbatim restore имеет потолок около 0.717

Это очень важное открытие.

На holdout все методы получают одинаковый verbatim restore **0.717**, потому что 17/20 сценариев имеют goals как semantic paraphrases, а не exact text в events.

**Это значит:**

```text
Если gold goal не встречается verbatim в raw events,
то RawVerbatim, VCM, StrongRAG и Full Context не могут выиграть по verbatim matching.
```

Поэтому semantic matcher нужен. Но semantic matcher надо использовать осторожно.

### 4. Semantic threshold 0.75 выглядит разумно, но требует human validation

Threshold ablation показывает:

```text
0.60–0.65: too lenient, everything matches
0.70: generous
0.75: recommended
0.80: too strict
0.85+: collapses
```

При threshold **0.75** VCM получает semantic_goal **0.700**, semantic_decision **1.000**, semantic_overall **0.900**.

**0.75 принимается как рабочий engineering threshold**, но не как финальная научная метрика без human annotation.

**Нужен mini-set:**

```text
100 goal/pack pairs
human labels: match / partial / no match
compare threshold 0.70, 0.75, 0.80
choose threshold by precision/recall, not intuition
```

### 5. На tuning VCM уже реально лучше RawVerbatim

На 29 tuning scenarios:

```text
VCM restore:       0.816
RawVerbatim:       0.747
StrongRAG:         0.747

VCM verbatim:      0.782
RawVerbatim:       0.724
StrongRAG:         0.724

VCM quality:       0.694
RawVerbatim:       0.631
StrongRAG:         0.608

VCM win count:     25/29
RawVerbatim wins:  4/29
StrongRAG wins:    0/29
```

Но tokens:

```text
VCM:         90.7
RawVerbatim: 54.9
StrongRAG:   133.2
```

То есть VCM побеждает по quality/restore, но проигрывает RawVerbatim по efficiency.

---

## Что НЕ доказано

### 1. VCM ещё не победил RawVerbatim по token efficiency

**Это главный blocker.**

```text
VCM uses 83.5 tokens on holdout / 90.7 on tuning
RawVerbatim uses 53–55
Target: ≤60 tokens
Root cause: structured sections add overhead
```

Если VCM требует почти в 1.6 раза больше tokens, то для production это проблема. Structured memory должна быть не только умнее, но и компактнее.

### 2. Exact-symbol scenarios всё ещё опасны

RawVerbatim выигрывает в tuning на exact-symbol scenarios:

```text
exact_config_key
exact_api_endpoint
exact_cicd_job
```

Причина: raw text сохраняет exact symbols verbatim, а VCM compression/structured memory иногда truncates или теряет exact match.

**Это критично для coding agent.** В реальном проекте exact symbols — это не мелочь:

```text
DATABASE_URL
AUTH_REFRESH_V2
processPaymentV2()
/api/v2/export/bulk
CVE-...
package@1.2.3
migration_20260510_add_index
```

Если VCM теряет такие символы, RawVerbatim будет выигрывать там, где агенту нужна точность.

### 3. Rationale recall пока слабый / stub-like

```text
Rationale Recall is Stub (0.200)
Need to extract rationale from events and check if present in pack
```

Это важно, потому что "помнить решение" недостаточно. Для coding agent часто нужно помнить:

```text
почему выбрали это решение
какие альтернативы отклонили
какой tradeoff был принят
какой риск остался
```

RawVerbatim часто сохраняет rationale естественно, потому что хранит весь разговор. VCM должен доказать, что structured compression не выкидывает "why".

### 4. Реальный codebase ещё не доказан

```text
All evals on synthetic scenarios
Real codebase restore historically 0.17–0.33
Need real-project dogfooding
```

Это значит: v0.9.2 — хороший synthetic/tuning/holdout milestone, но ещё не production proof.

---

## Как правильно использовать MemPal benchmark

MemPal benchmark показывает два важных принципа:

**Первый:** raw verbatim storage с embeddings — очень сильный baseline. В LongMemEval raw ChromaDB даёт **96.6% R@5** без LLM, а hybrid/rerank результаты выше, но документ честно предупреждает, что R@5 — это retrieval recall, не QA accuracy.

**Второй:** benchmark integrity важнее красивого headline. MemPal документ прямо признаёт, что 100% hybrid v4 частично teaching-to-the-test, потому что последние фиксы были сделаны после анализа конкретных failed questions; clean split — 50 dev / 450 held-out.

**Для VCM-OS это значит:**

```text
1. RawVerbatim должен остаться постоянным baseline.
2. Exact-symbol fallback нельзя смешивать с honest restore.
3. Semantic threshold нужно валидировать на human labels.
4. Tuning results нельзя выдавать за holdout proof.
5. В каждом eval нужен per-query audit JSONL.
```

---

## Пересмотренный v1.0 Roadmap

Текущий roadmap предлагает: Phase A token optimization, Phase B real codebase integration, Phase C learned router, Phase D multi-agent memory manager, Phase E GraphRAG, Phase F publication prep.

**Приоритеты пересмотрены:**

### Phase A — Token Optimization (первым)

Цель ≤60 tokens правильная. Но нельзя просто резать sections.

**Pass gate:**

```text
holdout tokens <= 60
tuning tokens <= 70
semantic_restore >= current - 0.02
decision_restore no regression
exact_symbol_recall no regression
stale_suppression stays 0.000
rationale_recall improves or stays measurable
```

**Опасность:**

```text
Вы можете сделать pack компактнее, но потерять why/decision rationale.
```

### Phase B — Real Codebase Integration (начинать параллельно)

Не ждать завершения learned router. Сначала dogfooding:

```text
VCM-OS должен использоваться для разработки VCM-OS.
```

**Минимальный реальный тест:**

```text
1. Завести 5 реальных dev sessions.
2. В каждой есть decisions, bugs, code diffs, TODO.
3. Через 24h/72h попросить агента восстановить состояние.
4. Сравнить:
   - VCM pack
   - RawVerbatim pack
   - raw chat history
   - StrongRAG
5. Метрики:
   - correct next task
   - correct files
   - correct active decisions
   - stale decision avoided
   - exact symbols retained
   - test/fix success
```

### Phase C — Learned Router (только после сбора trace data)

Learned router сейчас звучит логично, но рано, если данных мало.

**Сначала нужно накопить:**

```text
query
scenario type
retrieval plan
candidate memories
final pack
drop reasons
score breakdown
success/failure
```

Только потом обучать classifier. Иначе learned router просто выучит текущий synthetic distribution.

### Phase D/E — Multi-Agent + GraphRAG (не priority)

Multi-Agent Memory Manager и GraphRAG могут быть полезны, но сейчас главные blockers проще:

```text
tokens too high
exact symbols sometimes lost
rationale recall weak
real codebase not proven
live workflow not integrated
```

Если добавить multi-agent/GraphRAG до закрытия этих проблем, можно получить больше сложности без доказанного value.

---

## v1.0 Gate Definition

**v1.0 не выпускать, пока не выполнено:**

```text
1. VCM >= RawVerbatim+Hybrid on semantic_restore.
2. VCM > RawVerbatim+Hybrid on stale_suppression.
3. VCM > RawVerbatim+Hybrid on project_state_restore.
4. VCM >= RawVerbatim+Hybrid on exact_symbol_recall.
5. VCM tokens <= 60–70 average, or quality gain clearly justifies overhead.
6. Rationale recall is real, not stub.
7. Real-codebase dogfooding passes at least 10 sessions.
8. Kimi Code CLI actually calls VCM-OS in live workflow.
9. Per-query audit JSONL exists for every run.
10. Semantic threshold 0.75 is validated by human labels.
```

---

## Рекомендуемый порядок работы

```text
1. Phase A: Token optimization до ≤60–70 tokens.
2. Fix exact-symbol loss inside VCM compression.
3. Implement real rationale recall metric.
4. Start Phase B dogfooding immediately.
5. Compare VCM vs RawVerbatim on real VCM-OS coding sessions.
6. Only then start learned router.
```

---

## Финальный вывод одной строкой

```text
v0.9.2 доказал, что VCM имеет реальную структурную ценность против RawVerbatim, но ещё не доказал production superiority: RawVerbatim всё ещё дешевле, сильнее на некоторых exact-symbol cases, а real-codebase validation ещё впереди.
```
