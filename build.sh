#!/bin/bash
#
# This script runs the data preparation pipeline.
# It converts the markdown questions into the final JSON file
# used by the web application.
#
# Run this script whenever you change the source markdown file
# or the update logic in the python scripts.

echo "Step 1: Parsing markdown questions into questions_draft.json..."
python3 parser.py

echo "Step 2: Updating and cleaning draft into final questions.json..."
python3 update_questions.py

echo "Build complete! 'questions.json' is now up to date."