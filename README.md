# ML & BA Multiagent system for solving business problems

System to solve various business tasks with different data types 

## Installation Guide

### Set Up the Python Environment

1. **Install `uv` package**\
   [Installation guide](https://docs.astral.sh/uv/getting-started/installation/)

2. **Create and activate a virtual environment**

    ```bash
    uv venv .venv
    .venv\Scripts\activate
    ```

3. **Install dependencies**

    ```bash
    uv sync
    ```
### Add API keys

1. Add a file `.env` in the root of a directory

2. Get keys from [Anthropic API](https://console.anthropic.com/) (for LLM) and [E2B API](https://e2b.dev/dashboard?tab=keys) (for Python code execution)

3. Fill the file `.env` in the following way:
    ```
    ANTHROPIC_API_KEY=sk-ant...
    E2B_API_KEY=e2b_...
    ```

### Run the app

1. Write in the terminal
    ```
    task demoweb
    ```

2. Run the problem solving
- Press `Run` button for running on test data and problem
- Add data and prompts for solving of a custom problem
