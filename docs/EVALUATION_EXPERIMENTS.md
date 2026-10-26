# Offline evaluation and reproducible experiments (P1)

The evaluation infrastructure runs without hosted models, databases, or network
access. It measures existing retrieval strategies **before** algorithm changes.
Bad retrieval scores are useful baselines; by default only framework correctness
is a CI gate.

## Working example

After \`python -m pip install -e ".[test]"\`, run:

\`\`\`bash
python examples/offline_evaluation_example.py
\`\`\`

The example loads two versioned fixtures:

- \`examples/evaluation/animals.v1.json\` — graded question/document judgments.
- \`examples/evaluation/experiment.v1.json\` — strategy names, k, code revision,
  strategy settings, and provenance metadata.

It indexes documents using the **unified factory**, evaluates keyword and hybrid
retrieval with deterministic offline stores, saves a report, and reloads it.
The local toy embedder is **not** a realistic embedding benchmark.

## Evaluation API

\`\`\`python
from dataclasses import replace
from rag_factory.evaluation.dataset import EvaluationDataset
from rag_factory.evaluation.experiment import (
    ExperimentConfig, ExperimentRun, run_experiment,
)
from rag_factory.evaluation.comparison import compare_runs

dataset = EvaluationDataset.load("examples/evaluation/animals.v1.json")
config = ExperimentConfig.load("examples/evaluation/experiment.v1.json")

# Inject configured retrievers, e.g. wrappers around UnifiedPipeline.retrieve.
retrievers = {
    "lexical": lambda query, k: lexical_retriever(query, k),
    "fusion": lambda query, k: fusion_retriever(query, k),
}
baseline = run_experiment(dataset, config, retrievers)
baseline.save("baseline.json")

# After a code/config/provider change, capture the new revision and settings.
candidate_config = replace(config, code_revision="next-commit")
candidate = run_experiment(dataset, candidate_config, retrievers)
candidate.save("candidate.json")

comparison = compare_runs(
    ExperimentRun.load("baseline.json"),
    ExperimentRun.load("candidate.json"),
)
comparison.save("comparison.json")
print(comparison.regressions)  # Advisory: does not fail CI.

# An opt-in gate can explicitly fail when metrics regress:
# comparison.require_no_regressions()
\`\`\`

The injected callables must yield document IDs in ranked order. Wrapping a
unified pipeline is straightforward:
\`lambda query, k: [hit.document_id for hit in pipeline.retrieve("lexical", query, k)]\`.
Callers own the lifecycle and configuration of those retrievers.

## Metric definitions

All metrics share a top-k contract. Document IDs must be nonempty strings.
Repeated document IDs are collapsed, **keeping the first occurrence**, before
applying k. Documents with grade > 0 are relevant; grade 0 and documents absent
from judgments are nonrelevant. Every evaluated query needs at least one
positive judgment.

| Metric | Definition | What higher scores mean |
| --- | --- | --- |
| Recall@K | Relevant IDs in top-k divided by all positive judgments | More coverage of judged-relevant documents |
| Precision@K | Relevant IDs in top-k divided by **k**, even for short result lists | More useful documents per available slot |
| MRR@K | Mean over queries of 1 / rank of first relevant document, or 0 | First relevant document appears earlier |
| nDCG@K | DCG (gain = 2^grade - 1, log2 discount) divided by ideal DCG | Higher-grade documents appear earlier |

Values are computed per query, then averaged equally across all queries. A
retrieval score is **not** a proof of factual correctness or answer quality.

## Reproducibility and provenance

- Dataset JSON has \`format_version: 1\`, a logical name and a version.
- \`EvaluationDataset.sha256\` fingerprints the canonical dataset contents,
  independent of key order and pretty-printing.
- \`ExperimentConfig\` records the experiment name, cutoff k, strategy names,
  explicit \`code_revision\`, strategy settings, and caller-supplied metadata.
  Configurations also have a versioned JSON save/load API.
- Runs record both the dataset fingerprint and a configuration fingerprint
  that incorporates the dataset fingerprint. Results include raw ranked IDs
  and **per-query** metrics as well as aggregates.
- Strategies run in declared order and evaluation queries run in sorted order.
  Identical deterministic retrievers and unchanged inputs serialize to the
  same JSON. This does **not** force seeded/deterministic behavior on arbitrary
  LLMs or other external providers.
- \`capture_latency=True\` records per-query elapsed time in milliseconds.
  Latency is opt-in because real timings vary across runs; tests may inject a
  monotonic clock. Comparisons report average measured latency separately,
  without treating it as an automatic quality gate.
- JSON writes use same-directory atomic replacement; a failed replacement
  does not truncate an existing report or dataset.

\`compare_runs\` refuses to compare different dataset versions/fingerprints,
cutoff k, strategy sets, or evaluated query sets. It reports all four metric
deltas and flags drops beyond optional \`tolerated_drops\` thresholds. Neither
\`run_experiment\` nor \`compare_runs\` raises for low or regressed relevance
scores by default. Invoke \`require_no_regressions()\` explicitly to opt in
to CI quality gates.

The pre-existing \`compare_strategies\` and \`EvaluationReport\` APIs remain
supported; they now include Precision@K in aggregate experiment results.
