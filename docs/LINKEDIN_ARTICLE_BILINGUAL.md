# LinkedIn Article: VCM-OS

## Русская версия

### VCM-OS: почему AI-агентам нужна память, а не бесконечный prompt

Последние месяцы я работаю над VCM-OS — memory runtime для AI/coding agents.

Идея проекта простая: агент не должен каждый раз тащить всю историю проекта в prompt. Это дорого, шумно и плохо масштабируется. Вместо этого у агента должен быть отдельный memory-layer, который хранит важные решения, ошибки, цели, exact symbols, tool evidence и stale/superseded facts, а в текущий запрос отдаёт только минимально достаточный проверяемый context pack.

Обычный подход сегодня выглядит так:

```text
user request + huge chat history + files/tools -> model
```

VCM-OS предлагает другой цикл:

```text
events/tools/code/session
-> typed memories
-> linked project memory
-> compact context pack
-> verifier
-> correction/update
```

Это важно, потому что длинная история не равна хорошей памяти.

В длинной истории есть всё: старые гипотезы, отменённые решения, временные планы, failed fixes, случайные объяснения ассистента и устаревшие факты. Модель может найти там правильный сигнал, но может и воскресить старое решение, которое уже было отвергнуто. Чем длиннее проект, тем больше эта проблема.

VCM-OS пытается превратить историю разработки в состояние проекта:

```text
active goals
active decisions
rejected decisions
known errors
verified fixes
exact symbols
relevant files
tool evidence
open tasks
rationale
stale warnings
```

Недавно я проверил live integration с Kimi CLI через MCP. Kimi смог подключиться к VCM-OS, вызвать tools, записать memory event, затем извлечь context pack и восстановить exact symbol из памяти. В процессе теста нашёлся реальный баг: MCP tool для project state не видел active decisions из-за enum-сравнения и дополнительно обрезал exact symbols. Это было исправлено и покрыто тестом.

Этот результат важен не потому, что "интеграция запустилась", а потому что он показывает правильную архитектуру:

```text
agent = stateless executor
VCM-OS = long-term project memory
files/tools = source of details
verifier = guardrail against wrong memory usage
```

Следующий большой вопрос — экономия токенов.

Если агент просто использует VCM, но при этом продолжает resume старую Kimi/ChatGPT session history, экономия не доказана. Настоящий тест должен быть другим:

```text
fresh agent session
+ current task
+ recent 1-3 messages
+ VCM memory pack
+ files/tools inspected now
```

Без `--resume`, без `--continue`, без скрытой long-term chat history.

Тогда можно честно сравнить:

```text
FullHistory
Last-N
RawVerbatim
StrongRAG
VCM context pack
```

Для 40-100 turn'ов разработки full-history растёт очень быстро. Если на каждом шаге вставлять всю историю, суммарная стоимость становится близкой к O(n²). VCM pack остаётся почти постоянным: 300, 700, 1500 токенов в зависимости от сложности задачи.

То есть потенциальная экономия не в 10-20%, а в разы:

```text
full history: десятки/сотни тысяч токенов
VCM pack: сотни/тысячи токенов на шаг
```

Но экономия сама по себе не цель. Главный критерий — может ли свежий агент через 40, 100 или 300 сообщений продолжить проект лучше, чем агент без памяти:

- помнить старые решения;
- не использовать stale facts;
- не повторять failed fixes;
- находить exact symbols;
- понимать текущие цели;
- проверять claims против tool evidence;
- сохранять приватность через redaction.

Мой текущий вывод: VCM-OS уже выглядит не как "ещё один RAG", а как ранний runtime для project memory. Но следующий честный milestone — не красивый demo, а benchmark:

```text
stateless agent + VCM
vs
stateless agent without memory
vs
full-history agent
vs
RawVerbatim/StrongRAG
```

На реальных coding tasks, с измерением:

```text
task success
decision correctness
exact symbol recall
stale violations
tokens
latency
user corrections
```

Если VCM-OS сможет стабильно выигрывать у full-history или RawVerbatim по качеству/безопасности и при этом тратить кратно меньше токенов, это будет уже не просто оптимизация prompt'а.

Это будет инфраструктура долговременной памяти для AI-разработчика.

---

## English Version

### VCM-OS: Why AI Agents Need Memory, Not Infinite Prompts

Over the last few months, I have been working on VCM-OS — a memory runtime for AI and coding agents.

The idea is simple: an agent should not have to carry the entire project history in every prompt. That approach is expensive, noisy, and does not scale well. Instead, the agent should have a dedicated memory layer that stores important decisions, errors, goals, exact symbols, tool evidence, and stale or superseded facts, then retrieves only the minimal verified context needed for the current task.

The common approach today looks like this:

```text
user request + huge chat history + files/tools -> model
```

VCM-OS uses a different loop:

```text
events/tools/code/session
-> typed memories
-> linked project memory
-> compact context pack
-> verifier
-> correction/update
```

This matters because long history is not the same as good memory.

A long conversation contains everything: old hypotheses, rejected decisions, temporary plans, failed fixes, assistant speculation, and outdated facts. A model may find the right signal, but it may also revive a decision that was already rejected. The longer the project runs, the worse this problem gets.

VCM-OS tries to turn development history into project state:

```text
active goals
active decisions
rejected decisions
known errors
verified fixes
exact symbols
relevant files
tool evidence
open tasks
rationale
stale warnings
```

I recently tested live integration with Kimi CLI through MCP. Kimi connected to VCM-OS, called the VCM tools, wrote a memory event, retrieved a context pack, and restored an exact symbol from memory. During the test, I found a real bug: the MCP project-state tool did not return active decisions because of enum comparison logic, and it also truncated exact symbols. That was fixed and covered with a regression test.

The important part is not just that the integration worked. The important part is the architecture:

```text
agent = stateless executor
VCM-OS = long-term project memory
files/tools = source of details
verifier = guardrail against wrong memory usage
```

The next big question is token economy.

If an agent uses VCM but still resumes its own full Kimi or ChatGPT session history, then token savings are not proven. The real test should look different:

```text
fresh agent session
+ current task
+ recent 1-3 messages
+ VCM memory pack
+ files/tools inspected now
```

No `--resume`, no `--continue`, no hidden long-term chat history.

Only then can we fairly compare:

```text
FullHistory
Last-N
RawVerbatim
StrongRAG
VCM context pack
```

Across 40-100 development turns, full-history prompting grows very quickly. If every step includes the entire prior conversation, cumulative token usage trends toward O(n²). A VCM pack stays almost constant: 300, 700, or 1500 tokens depending on task complexity.

So the potential savings are not just 10-20%. They can be multiples:

```text
full history: tens or hundreds of thousands of tokens
VCM pack: hundreds or low thousands of tokens per step
```

But token savings alone are not the goal. The real test is whether a fresh agent can resume a project after 40, 100, or 300 messages better than an agent without memory:

- remember old decisions;
- avoid stale facts;
- avoid repeating failed fixes;
- recover exact symbols;
- understand current goals;
- verify claims against tool evidence;
- preserve privacy through redaction.

My current view: VCM-OS is no longer just "another RAG". It is starting to look like a runtime for project memory.

The next honest milestone is not a polished demo. It is a benchmark:

```text
stateless agent + VCM
vs
stateless agent without memory
vs
full-history agent
vs
RawVerbatim/StrongRAG
```

On real coding tasks, measured by:

```text
task success
decision correctness
exact symbol recall
stale violations
tokens
latency
user corrections
```

If VCM-OS can consistently beat full-history or RawVerbatim on quality and safety while using significantly fewer tokens, then it is not just prompt optimization.

It becomes long-term memory infrastructure for AI developers.
