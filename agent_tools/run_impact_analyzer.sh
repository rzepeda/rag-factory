#!/bin/bash

# Impact Analyzer Runner
# Analyzes all source files and generates dependency YAML files
# Run this script from the agent_tools/ directory

set -e  # Exit on error

# Configuration (relative to project root, not this script)
SOURCE_DIR="../src"
TESTS_DIR="../tests"
MIRROR_DIR="../tests/dependency_graph"
ANALYZER_SCRIPT="impact_analyzer.py"  # In same directory as this script
LEVEL=0  # Default level

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --level)
            LEVEL="$2"
            shift 2
            ;;
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --mirror)
            MIRROR_DIR="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Run from agent_tools/ directory"
            echo ""
            echo "Options:"
            echo "  --level N        Dependency depth (default: 0)"
            echo "  --source DIR     Source directory (default: ../src)"
            echo "  --mirror DIR     Mirror directory (default: ../tests/dependency_graph)"
            echo "  --help           Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if analyzer script exists
if [ ! -f "$ANALYZER_SCRIPT" ]; then
    echo -e "${RED}Error: Analyzer script not found at $ANALYZER_SCRIPT${NC}"
    echo -e "${RED}Make sure you're running this from the agent_tools/ directory${NC}"
    exit 1
fi

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo -e "${RED}Error: Source directory not found at $SOURCE_DIR${NC}"
    exit 1
fi

# Print configuration
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Impact Analyzer - Full Project${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Source directory: ${GREEN}$SOURCE_DIR${NC}"
echo -e "Mirror directory: ${GREEN}$MIRROR_DIR${NC}"
echo -e "Analysis level:   ${GREEN}$LEVEL${NC}"
echo ""

# Create mirror directory if it doesn't exist
mkdir -p "$MIRROR_DIR"

# Run the analyzer
echo -e "${BLUE}Running analysis...${NC}"
python "$ANALYZER_SCRIPT" "$SOURCE_DIR" --level "$LEVEL" --format yaml --mirror-dir "$MIRROR_DIR"

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Analysis complete!${NC}"
    echo -e "Results saved to: ${GREEN}$MIRROR_DIR${NC}"
    
    # Count generated files
    YAML_COUNT=$(find "$MIRROR_DIR" -name "*.yaml" -type f | wc -l)
    echo -e "Generated ${GREEN}$YAML_COUNT${NC} dependency files"
else
    echo -e "${RED}✗ Analysis failed${NC}"
    exit 1
fi
