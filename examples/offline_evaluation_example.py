"""Execute a reproducible, all-offline evaluation of unified RAG strategies.

Run from a checkout after installing: python examples/offline_evaluation_example.py
The tiny deterministic embedder is for wiring tests, not realistic embeddings.
"""
from pathlib import Path
from tempfile import TemporaryDirectory

from rag_factory.core.service_contracts import ProviderDescriptor
from rag_factory.evaluation.dataset import EvaluationDataset
from rag_factory.evaluation.experiment import ExperimentConfig, ExperimentRun, run_experiment
from rag_factory.factory.service_registry import ServiceConfig, default_registry
from rag_factory.factory.unified import StrategySpec, UnifiedConfiguration, build_unified


class OfflineEmbedding:
    def embed(self, texts):
        return [
            [float(text.lower().count("cat")), float(text.lower().count("dog")),
             float(text.lower().count("planet"))]
            for text in texts
        ]


def main() -> None:
    fixtures = Path(__file__).parent / "evaluation"
    dataset = EvaluationDataset.load(fixtures / "animals.v1.json")
    experiment = ExperimentConfig.load(fixtures / "experiment.v1.json")

    registry = default_registry()
    registry.register(
        ProviderDescriptor("embedding", "toy", frozenset({"embed"})),
        OfflineEmbedding,
    )
    config = UnifiedConfiguration(
        services={
            "keywords": ServiceConfig("keyword_store", "memory"),
            "tokens": ServiceConfig("tokenizer", "regex"),
            "embedding": ServiceConfig("embedding", "toy"),
            "vectors": ServiceConfig("vector_store", "memory"),
        },
        strategies={
            "lexical": StrategySpec(
                "keyword", {"keyword_store": "keywords"},
                {"keyword_store": "keywords", "tokenizer": "tokens"},
            ),
            "semantic": StrategySpec(
                "semantic", {"embedding": "embedding", "vector_store": "vectors"},
                {"embedding": "embedding", "vector_store": "vectors"},
                {"embedding_model": "toy"},
            ),
            "fusion": StrategySpec("hybrid", parameters={"sources": ["lexical", "semantic"]}),
        },
    )
    documents = {
        "cat-document": "Cats purr and are pets",
        "dog-document": "Dogs bark and are pets",
        "planet-document": "Planets orbit stars",
    }
    with build_unified(config, registry) as pipeline:
        pipeline.index("lexical", {"documents": documents})
        pipeline.index("semantic", {"documents": documents})
        retrievers = {
            name: (lambda query, k, name=name: [
                hit.document_id for hit in pipeline.retrieve(name, query, k)
            ])
            for name in experiment.strategies
        }
        result = run_experiment(dataset, experiment, retrievers)
        with TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            result.save(output)
            restored = ExperimentRun.load(output)
            print(f"Dataset: {restored.dataset} v{restored.dataset_version}")
            print(f"Fingerprint: {restored.dataset_sha256}")
            for item in restored.results:
                score = item.summary
                print(
                    f"{score.strategy}: Recall@{score.k}={score.recall_at_k:.3f}, "
                    f"Precision@{score.k}={score.precision_at_k:.3f}, "
                    f"MRR@{score.k}={score.mean_reciprocal_rank_at_k:.3f}, "
                    f"nDCG@{score.k}={score.mean_ndcg_at_k:.3f}"
                )


if __name__ == "__main__":
    main()
