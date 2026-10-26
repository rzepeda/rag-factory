"""Offline unified pipeline CLI.

Each command starts a fresh in-memory pipeline. Retrieval/evaluation *replay*
the index payloads supplied on that invocation; metadata bundles never contain
physical index contents. External providers are deliberately not provisioned.
"""
import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from rag_factory.factory.service_registry import default_registry
from rag_factory.factory.unified import INDEXED, build_unified
from rag_factory.factory.unified_config import load_validated_unified_config
from rag_factory.evaluation.dataset import EvaluationDataset
from rag_factory.evaluation.experiment import ExperimentConfig, run_experiment


def _configuration(path):
    return load_validated_unified_config(path, default_registry())


def _payloads(path, configuration):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or set(data) != {"format_version", "indexes"}
        or type(data["format_version"]) is not int or data["format_version"] != 1
        or not isinstance(data["indexes"], dict) or not data["indexes"]):
        raise ValueError("Index payload file needs format_version=1 and nonempty indexes mapping")
    prepared = {}
    for name, payload in data["indexes"].items():
        if name not in configuration.strategies:
            raise ValueError(f"Unknown index strategy: {name}")
        if configuration.strategies[name].kind not in INDEXED:
            raise ValueError(f"Strategy {name} does not implement indexing")
        if not isinstance(payload, dict):
            raise ValueError(f"Index payload for {name} must be a mapping")
        converted = dict(payload)
        if configuration.strategies[name].kind == "late_chunking":
            if isinstance(converted.get("spans"), dict):
                converted["spans"] = {
                    key: tuple(bounds) if isinstance(bounds, list) else bounds
                    for key, bounds in converted["spans"].items()
                }
        prepared[name] = converted
    return prepared


def _index(pipeline, payloads):
    for name, payload in payloads.items():
        pipeline.index(name, payload)


def _print(payload):
    print(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False))


def build_parser():
    parser = argparse.ArgumentParser(
        prog="rag-factory", description="Offline unified RAG pipeline tools"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "index", "retrieve", "evaluate"):
        item = sub.add_parser(command)
        item.add_argument("--config", required=True, help="Unified pipeline YAML")
        if command != "validate":
            item.add_argument(
                "--payloads", required=True,
                help="Versioned JSON index payloads, replayed in this command",
            )
        if command == "index":
            item.add_argument("--bundle", help="Write manifest/hierarchy metadata only")
        if command == "retrieve":
            item.add_argument("--strategy", required=True)
            item.add_argument("--query", required=True)
            item.add_argument("--limit", type=int, default=5)
        if command == "evaluate":
            item.add_argument("--dataset", required=True)
            item.add_argument("--experiment", required=True)
            item.add_argument("--output", required=True)
            item.add_argument("--capture-latency", action="store_true")
    return parser


def execute(args):
    config = _configuration(args.config)
    if args.command == "validate":
        _print({
            "status": "valid",
            "services": sorted(config.services),
            "strategies": {name: spec.kind for name, spec in sorted(config.strategies.items())},
        })
        return
    payloads = _payloads(args.payloads, config)
    if args.command == "retrieve":
        if args.strategy not in config.strategies:
            raise ValueError(f"Unknown retrieval strategy: {args.strategy}")
    if args.command == "evaluate":
        dataset = EvaluationDataset.load(args.dataset)
        experiment = ExperimentConfig.load(args.experiment)
        missing = [name for name in experiment.strategies if name not in config.strategies]
        if missing:
            raise ValueError("Experiment references unknown strategies: " + ", ".join(missing))
    with build_unified(config, default_registry()) as pipeline:
        _index(pipeline, payloads)
        if args.command == "index":
            if args.bundle:
                pipeline.export_artifact_bundle(args.bundle)
            _print({
                "status": "indexed",
                "ephemeral": True,
                "artifacts": {
                    name: artifact.artifact_id
                    for name, artifact in sorted(pipeline._artifacts.items())
                },
                "bundle": args.bundle,
            })
        elif args.command == "retrieve":
            hits = pipeline.retrieve(args.strategy, args.query, args.limit)
            _print({"strategy": args.strategy, "hits": [asdict(hit) for hit in hits]})
        else:
            retrievers = {
                name: (lambda query, k, name=name: [
                    hit.document_id for hit in pipeline.retrieve(name, query, k)
                ])
                for name in experiment.strategies
            }
            result = run_experiment(
                dataset, experiment, retrievers, capture_latency=args.capture_latency
            )
            result.save(args.output)
            _print({
                "report": args.output,
                "dataset_sha256": result.dataset_sha256,
                "config_sha256": result.config_sha256,
                "results": [asdict(item.summary) for item in result.results],
            })


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        execute(args)
    except (ValueError, TypeError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"rag-factory: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
