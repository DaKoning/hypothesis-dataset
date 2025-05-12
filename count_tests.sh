#!/bin/bash

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

DIRECTORY=$1

if [ ! -d "$DIRECTORY" ]; then
    echo "Error: Directory '$DIRECTORY' does not exist."
    exit 1
fi

PBT_COUNT=$(grep -r --binary-files=without-match -o -E '@given|@.*\.given' "$DIRECTORY" | wc -l)
TOTAL_TEST_COUNT=$(grep -r --binary-files=without-match -o -E 'def test_' "$DIRECTORY" | wc -l)

if [ "$TOTAL_TEST_COUNT" -eq 0 ]; then
    echo "No tests found in the directory."
    exit 0
fi

PBT_PERCENTAGE=$(echo "scale=5; ($PBT_COUNT / $TOTAL_TEST_COUNT) * 100" | bc)

echo "Number of property-based tests: $PBT_COUNT"
echo "Total number of tests: $TOTAL_TEST_COUNT"
echo "Percentage of property-based tests: $PBT_PERCENTAGE%"