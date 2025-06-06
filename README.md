# ContribNavigator

ContribNavigator is an AI-assisted tool designed to help developers, especially newcomers, find and begin contributing to open-source projects on GitHub. It streamlines issue discovery and provides an intelligently generated onboarding kit.

## Core Features

*   **Targeted Issue Search:** Filters GitHub issues by programming language and user-specified topics (e.g., "python" + "machine-learning"), prioritizing beginner-friendly labels like "good first issue."
*   **AI-Powered Issue Suggestion:** Leverages an LLM (OpenAI GPT-4o class) to analyze fetched issues and recommend the most suitable starting point for a beginner, with clear reasoning.
*   **Intelligent Onboarding Kit:**
    *   **AI-Planned Components:** An LLM planner dynamically determines the most relevant sections to include in the kit based on the selected issue.
    *   **Essential Information:** Direct links to the issue and repository, `git clone` command.
    *   **Contribution Guidelines Analysis:**
        *   Link to the project's `CONTRIBUTING.md` (or similar).
        *   AI-generated summary of key contribution procedures (setup, coding style, PR process).
    *   **Repository Overview (via Modal):**
        *   Top-level file and directory listing from a sandboxed `git clone` operation executed on Modal.
        *   AI-suggested relevant files/folders to investigate for the specific issue.
*   **First Steps Checklist:** An interactive checklist in the UI to guide users through their initial contribution actions.
*   **Agentic Design:** Built with an agentic architecture where an LLM plans and orchestrates the use of internal "tools" (GitHub API client, Modal repo inspector, LLM analysis functions), aligning with Model Context Protocol (MCP) principles.

## Tech Stack

*   **UI:** Gradio
*   **Backend & Orchestration:** Python
*   **Language Models:** OpenAI API (GPT-4o class)
*   **Sandboxed Operations:** Modal (for `git clone`)
*   **Data Source:** GitHub API

## Local Development Setup

1.  **Prerequisites:**
    *   Git
    *   Python (3.10+)
    *   Modal Account & CLI (`modal token new`)

2.  **Clone & Install Dependencies:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/ContribNavigator.git # Replace with your repo URL
    cd ContribNavigator
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Environment Variables:**
    *   Create a `.env` file in the project root (refer to `.env.example` if provided).
    *   Add your API keys:
        ```env
        GITHUB_PAT="your_github_pat"
        OPENAI_API_KEY="sk-your_openai_key"
        # MODAL_TOKEN_ID="mi_..." # Optional for local if `modal token new` was used
        # MODAL_TOKEN_SECRET="ms_..." # Optional for local
        ```

4.  **Run the Application:**
    ```bash
    python app.py
    ```

## Hackathon Context

*   **Project:** ContribNavigator
*   **Event:** Agents & MCP Hackathon
*   **Primary Track Submission:** Agentic Demos Track
    *   *Demonstrates an end-to-end AI agent application using Gradio that assists with open-source contributions through intelligent planning and tool utilization (GitHub API, Modal, LLM analysis), reflecting MCP principles.*

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.