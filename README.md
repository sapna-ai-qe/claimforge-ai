# ClaimForge AI

An LLM-powered copilot for auto insurance claims adjusters. ClaimForge AI helps
adjusters process claims faster and more accurately by automating document
intake, coverage analysis, and fraud signal detection — while keeping the human
in the loop for every decision.

## The problem

Auto insurance claims are document-heavy and rule-heavy. Adjusters spend hours
per claim reading police reports, repair estimates, and policy documents,
then making coverage and settlement decisions. ClaimForge AI compresses that
work into a guided, AI-assisted workflow.

## Features (planned)

- **FNOL intake agent** — conversational first-notice-of-loss capture that
  produces a structured claim record.
- **Document extraction** — multi-modal pipeline that reads police reports,
  repair estimates, and damage photos into structured data.
- **Coverage RAG** — policy question-answering grounded in the actual policy
  document, with citations.
- **Fraud signal detection** — agent that flags inconsistencies across the
  narrative, history, and evidence.
- **Adjuster UI** — human-in-the-loop interface for reviewing and approving
  each step.
- **Evaluation harness** — accuracy and groundedness metrics for every
  component.

## Tech stack

- Python
- Claude / OpenAI for LLM reasoning and vision
- LangGraph (or hand-rolled agent loop) for orchestration
- Chroma / LanceDB for vector storage
- Streamlit for the UI
- Promptfoo / custom harness for evaluations

## Status

Early development. See `docs/` for architecture notes and the build plan.

## Author

[Your name] — building this to learn the insurance claims domain and modern
agentic LLM techniques.
