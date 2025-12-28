import os
import sys
import ast
import json
import yaml
import glob
import argparse
from pathlib import Path
from collections import deque

# Configuration
SOURCE_DIR = "rag_factory"
TEST_DIR = "tests"
MIRROR_DIR = "tests/mirror"
TEMPLATE_PATH = "templates/test_config_scaffold.yaml"

def find_imports(file_path):
    """
    Parses a python file and returns a list of absolute imports.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=file_path)
    except Exception as e:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports

def build_reverse_dependency_map():
    """
    Builds the full graph:
    { 'rag_factory/file.py': { 'tests': [], 'dependents': [] } }
    """
    mapping = {}

    def register_link(target_file, source_file, link_type):
        if target_file not in mapping:
            mapping[target_file] = {"tests": set(), "mocks": set(), "dependents": set()}
        mapping[target_file][link_type].add(source_file)

    # Scan Tests (find what source files they test)
    for f in glob.glob(f"{TEST_DIR}/**/*.py", recursive=True):
        if "mirror" in f: continue
        is_mock = "mocks" in f
        link_type = "mocks" if is_mock else "tests"
        
        for module in find_imports(f):
            if module.startswith(f"{SOURCE_DIR}."):
                target = module.replace(".", "/") + ".py"
                if os.path.exists(target):
                    register_link(target, f, link_type)

    # Scan Source (find what other source files rely on them)
    for f in glob.glob(f"{SOURCE_DIR}/**/*.py", recursive=True):
        for module in find_imports(f):
            if module.startswith(f"{SOURCE_DIR}."):
                target = module.replace(".", "/") + ".py"
                # Prevent self-referencing if present
                if os.path.exists(target) and target != f:
                    register_link(target, f, "dependents")

    return mapping

def get_impact_radius(target_file, level, dependency_map):
    """
    Returns a dictionary of all affected source files and tests up to `level` depth.
    target_file: The file being changed.
    level: Depth of recursion (0 = just direct dependents, 1+ = recursive dependents in impact_by_level).
    
    impacted_source: Source files that directly import target
    impacted_tests: Test files that directly import target  
    impact_by_level: For level >= 1, shows next levels of dependencies
    """
    # These are ALWAYS the direct dependents of the target, regardless of level
    impacted_source = set()
    impacted_tests = set()
    impacted_mocks = set()
    
    # Get direct dependents (files that import the target)
    if target_file in dependency_map:
        # Source files that import target
        impacted_source.update(dependency_map[target_file]["dependents"])
        
        # Test files that import target
        impacted_tests.update(dependency_map[target_file]["tests"])
        impacted_mocks.update(dependency_map[target_file]["mocks"])
    
    # impact_by_level only gets filled if level > 0
    impact_by_level = {}
    
    if level == 0:
        # At level 0, impact_by_level stays empty
        return {
            "source_files": sorted(list(impacted_source)),
            "test_files": sorted(list(impacted_tests)),
            "mock_files": sorted(list(impacted_mocks)),
            "impact_by_level": impact_by_level
        }
    
    # For level >= 1, we need to traverse deeper and fill impact_by_level
    visited = set(impacted_source)  # Already processed direct dependents
    visited.add(target_file)
    
    # Queue stores: (current_file_path, current_depth)
    # Start from direct dependents at depth 1
    queue = deque([(dep, 1) for dep in impacted_source])
    
    while queue:
        current_file, current_depth = queue.popleft()
        
        # Stop if we've gone beyond requested depth
        if current_depth > level:
            continue
        
        if current_file in dependency_map:
            # Get files that depend on the current file
            dependents = dependency_map[current_file]["dependents"]
            
            # Initialize this level in impact_by_level if needed
            if current_depth not in impact_by_level:
                impact_by_level[current_depth] = {"source": set(), "tests": set(), "mocks": set()}
            
            for dependent in dependents:
                # Add to this level's tracking
                impact_by_level[current_depth]["source"].add(dependent)
                
                # Continue traversing if not visited and within depth
                if dependent not in visited and current_depth < level:
                    visited.add(dependent)
                    queue.append((dependent, current_depth + 1))
            
            # Add tests for the current file to this level
            impact_by_level[current_depth]["tests"].update(dependency_map[current_file]["tests"])
            impact_by_level[current_depth]["mocks"].update(dependency_map[current_file]["mocks"])
    
    # Convert sets to sorted lists
    impact_by_level = {k: {
        "source": sorted(list(v["source"])),
        "tests": sorted(list(v["tests"])),
        "mocks": sorted(list(v["mocks"]))
    } for k, v in impact_by_level.items()}
    
    return {
        "source_files": sorted(list(impacted_source)),
        "test_files": sorted(list(impacted_tests)),
        "mock_files": sorted(list(impacted_mocks)),
        "impact_by_level": impact_by_level
    }



def output_human_readable(target_file, impact_data, dependency_map, level):
    """
    Print human-readable output.
    """
    print(f"\n--- Impact Report (Depth {level}) ---")
    
    # Test coverage
    has_tests = target_file in dependency_map and len(dependency_map[target_file]["tests"]) > 0
    has_mocks = target_file in dependency_map and len(dependency_map[target_file]["mocks"]) > 0
    
    print(f"\nTarget: {target_file}")
    print(f"Has tests: {has_tests}")
    if has_mocks:
        print(f"Has mocks: {has_mocks}")
    
    # Impact - show files that depend on target
    print(f"\nFiles that depend on target ({len(impact_data['source_files'])}):")
    for s in impact_data['source_files']:
        print(f"  - {s}")
    
    # Tests to run
    print(f"\nTests to run ({len(impact_data['test_files'])}):")
    for t in impact_data['test_files']:
        print(f"  - {t}")
    
    if impact_data['mock_files']:
        print(f"\nMock files ({len(impact_data['mock_files'])}):")
        for m in impact_data['mock_files']:
            print(f"  - {m}")

def output_json(target_file, impact_data, dependency_map, level):
    """
    Output machine-readable JSON for agent consumption.
    """
    has_tests = target_file in dependency_map and len(dependency_map[target_file]["tests"]) > 0
    has_mocks = target_file in dependency_map and len(dependency_map[target_file]["mocks"]) > 0
    test_files = sorted(list(dependency_map[target_file]["tests"])) if target_file in dependency_map else []
    mock_files = sorted(list(dependency_map[target_file]["mocks"])) if target_file in dependency_map else []
    
    output = {
        "target_file": target_file,
        "depth_level": level,
        "has_tests": has_tests,
        "has_mocks": has_mocks,
        "test_files": test_files,
        "mock_files": mock_files,
        "impacted_source": impact_data["source_files"],
        "impacted_tests": impact_data["test_files"],
        "impacted_mocks": impact_data["mock_files"],
        "impact_by_level": impact_data["impact_by_level"]
    }
    
    return json.dumps(output, indent=2)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="Path to source file or directory")
    parser.add_argument("--level", type=int, default=0, help="Dependency depth (default: 0)")
    parser.add_argument("--format", choices=["human", "json", "yaml"], default="human", help="Output format (default: human)")
    parser.add_argument("--output", "-o", help="Output file for single YAML (optional for directory)")
    parser.add_argument("--mirror-dir", default=MIRROR_DIR, help=f"Directory for individual YAML files (default: {MIRROR_DIR})")
    args = parser.parse_args()

    target = Path(args.path)
    
    # Check if path is a directory
    if target.is_dir():
        # Process all Python files in directory
        if args.format != "yaml":
            print("Error: Directory processing only supported with --format yaml", file=sys.stderr)
            sys.exit(1)
        
        # Build dependency map once
        print("Building dependency graph...")
        full_map = build_reverse_dependency_map()
        
        # Collect all Python files
        py_files = sorted(target.rglob("*.py"))
        
        print(f"Processing {len(py_files)} files...")
        
        # If --output is specified, build single YAML file
        if args.output:
            results = {}
            for py_file in py_files:
                file_str = str(py_file)
                if os.path.exists(file_str):
                    impact_data = get_impact_radius(file_str, args.level, full_map)
                    
                    has_tests = file_str in full_map and len(full_map[file_str]["tests"]) > 0
                    has_mocks = file_str in full_map and len(full_map[file_str]["mocks"]) > 0
                    test_files = sorted(list(full_map[file_str]["tests"])) if file_str in full_map else []
                    mock_files = sorted(list(full_map[file_str]["mocks"])) if file_str in full_map else []
                    
                    results[file_str] = {
                        "has_tests": has_tests,
                        "has_mocks": has_mocks,
                        "test_files": test_files,
                        "mock_files": mock_files,
                        "impacted_source": impact_data["source_files"],
                        "impacted_tests": impact_data["test_files"],
                        "impacted_mocks": impact_data["mock_files"]
                    }
            
            # Write single YAML file
            with open(args.output, "w") as f:
                yaml.dump(results, f, default_flow_style=False, sort_keys=False)
            
            print(f"✓ Written {len(results)} file analyses to {args.output}")
        
        else:
            # Generate individual YAML files in mirror directory structure
            mirror_base = Path(args.mirror_dir)
            mirror_base.mkdir(parents=True, exist_ok=True)
            
            files_created = 0
            for py_file in py_files:
                file_str = str(py_file)
                if os.path.exists(file_str):
                    impact_data = get_impact_radius(file_str, args.level, full_map)
                    
                    has_tests = file_str in full_map and len(full_map[file_str]["tests"]) > 0
                    has_mocks = file_str in full_map and len(full_map[file_str]["mocks"]) > 0
                    test_files = sorted(list(full_map[file_str]["tests"])) if file_str in full_map else []
                    mock_files = sorted(list(full_map[file_str]["mocks"])) if file_str in full_map else []
                    
                    result = {
                        "target_file": file_str,
                        "has_tests": has_tests,
                        "has_mocks": has_mocks,
                        "test_files": test_files,
                        "mock_files": mock_files,
                        "impacted_source": impact_data["source_files"],
                        "impacted_tests": impact_data["test_files"],
                        "impacted_mocks": impact_data["mock_files"]
                    }
                    
                    # Create mirror directory structure
                    relative_path = py_file.relative_to(target)
                    mirror_file = mirror_base / relative_path.parent / f"{relative_path.stem}.yaml"
                    mirror_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Write individual YAML file
                    with open(mirror_file, "w") as f:
                        yaml.dump(result, f, default_flow_style=False, sort_keys=False)
                    
                    files_created += 1
            
            print(f"✓ Created {files_created} YAML files in {mirror_base}")
        
        return
    
    # Original single-file processing
    if not target.exists():
        print(f"Error: File {target} not found", file=sys.stderr)
        sys.exit(1)
    
    target_str = str(target)
    
    # Build Graph
    if args.format == "human":
        print("Building dependency graph...")
    full_map = build_reverse_dependency_map()
    
    # Calculate Impact
    if args.format == "human":
        print(f"Calculating impact for {target_str} at Level {args.level}...")
    impact_data = get_impact_radius(target_str, args.level, full_map)
    
    # Output
    if args.format == "json":
        output_str = output_json(target_str, impact_data, full_map, args.level)
        print(output_str)
    elif args.format == "yaml":
        # Build YAML structure for single file
        has_tests = target_str in full_map and len(full_map[target_str]["tests"]) > 0
        has_mocks = target_str in full_map and len(full_map[target_str]["mocks"]) > 0
        test_files = sorted(list(full_map[target_str]["tests"])) if target_str in full_map else []
        mock_files = sorted(list(full_map[target_str]["mocks"])) if target_str in full_map else []
        
        result = {
            "target_file": target_str,
            "depth_level": args.level,
            "has_tests": has_tests,
            "has_mocks": has_mocks,
            "test_files": test_files,
            "mock_files": mock_files,
            "impacted_source": impact_data["source_files"],
            "impacted_tests": impact_data["test_files"],
            "impacted_mocks": impact_data["mock_files"],
            "impact_by_level": impact_data["impact_by_level"]
        }
        
        # If output file specified, write there
        if args.output:
            with open(args.output, "w") as f:
                yaml.dump(result, f, default_flow_style=False, sort_keys=False)
            print(f"✓ Written analysis to {args.output}")
        # If mirror-dir specified, write to mirror structure
        elif args.mirror_dir:
            mirror_base = Path(args.mirror_dir)
            
            # Determine the source directory (e.g., "rag_factory")
            target_path = Path(target_str)
            parts = target_path.parts
            if len(parts) > 1:
                # Find the base directory (first part of path)
                base_dir = parts[0]
                relative_path = target_path.relative_to(base_dir)
                mirror_file = mirror_base / relative_path.parent / f"{relative_path.stem}.yaml"
            else:
                mirror_file = mirror_base / f"{target_path.stem}.yaml"
            
            mirror_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(mirror_file, "w") as f:
                yaml.dump(result, f, default_flow_style=False, sort_keys=False)
            print(f"✓ Written analysis to {mirror_file}")
        else:
            # No output specified, print to stdout
            print(yaml.dump(result, default_flow_style=False, sort_keys=False))
    else:
        output_human_readable(target_str, impact_data, full_map, args.level)

if __name__ == "__main__":
    main()
