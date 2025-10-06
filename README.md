# Custom GPT Project

This project contains a custom GPT implementation with the following structure:

## Directory Structure

- `/gpt` - Contains system prompts and prompt cards
- `/tools` - Tool implementations (xmetric, ymetric, file_upload)
- `/models` - API models
- `/schemas` - JSON schemas for data validation
- `/data/eval` - Evaluation scripts and data

## Getting Started

1. Install dependencies: `poetry install`
2. Run evaluation: `python data/eval/run_eval.py`