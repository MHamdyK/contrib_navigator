# core/kit_generator.py
from .github_client import get_repository_details, get_file_url_from_repo # Use . for same-package import

def generate_basic_kit_content(issue_data: dict) -> str:
    """
    Generates basic Markdown content for an onboarding kit for a given issue.
    """
    if not issue_data:
        return "Error: No issue data provided to generate kit."

    issue_title = issue_data.get("title", "N/A")
    issue_html_url = issue_data.get("html_url", "#")
    repo_html_url = issue_data.get("repository_html_url", "#") # e.g., https://github.com/owner/repo
    repo_api_url = issue_data.get("repository_api_url") # e.g., https://api.github.com/repos/owner/repo

    # Derive repo_full_name (owner/repo) from repo_html_url for get_file_url_from_repo
    repo_full_name = None
    if repo_html_url and repo_html_url.startswith("https://github.com/"):
        parts = repo_html_url.split('/')
        if len(parts) >= 5:
            repo_full_name = f"{parts[3]}/{parts[4]}" # owner/repo

    contributing_url = "Not found or could not be determined."
    default_branch_name = "main (assumed)" # Fallback

    if repo_full_name:
        # Try to get default branch from repo_api_url if available
        branch_from_api = None
        if repo_api_url:
            repo_details = get_repository_details(repo_api_url)
            if repo_details and repo_details.get("default_branch"):
                branch_from_api = repo_details.get("default_branch")
                default_branch_name = branch_from_api # Update if found
        else: # Fallback if repo_api_url wasn't in issue_data (should be, but good to be safe)
            temp_repo_api_url = f"https://api.github.com/repos/{repo_full_name}"
            repo_details = get_repository_details(temp_repo_api_url)
            if repo_details and repo_details.get("default_branch"):
                branch_from_api = repo_details.get("default_branch")
                default_branch_name = branch_from_api


        # Common paths for CONTRIBUTING.md
        contributing_paths = [
            "CONTRIBUTING.md",
            ".github/CONTRIBUTING.md",
            "docs/CONTRIBUTING.md",
            "CONTRIBUTING.rst", # Also check for reStructuredText
            ".github/CONTRIBUTING.rst"
        ]
        found_contrib_url = get_file_url_from_repo(repo_full_name, contributing_paths, default_branch=branch_from_api)
        if found_contrib_url:
            contributing_url = f"[{found_contrib_url}]({found_contrib_url})"
    else:
        print("Warning: Could not derive repo_full_name from issue_data. Contribution guidelines link might be missing.")


    kit_markdown = f"""
# 👋 Onboarding Kit for: {issue_title}

Congratulations on choosing this issue! Here's some information to help you get started.

## 🔗 Issue Details
- **Issue Link:** [{issue_title}]({issue_html_url})
- **Repository:** [{repo_html_url}]({repo_html_url})

## 🛠️ Initial Setup Guide
1.  **Clone the Repository:**
    Open your terminal and run the following command to clone the repository to your local machine:
    ```bash
    git clone {repo_html_url}.git
    ```
    *(Note: Ensure you have Git installed. The repository might use a different default branch name than '{default_branch_name}'.)*

2.  **Navigate into the Project Directory:**
    ```bash
    cd {repo_html_url.split('/')[-1]}
    ```
    *(This assumes the directory name matches the repository name. Adjust if needed.)*

## 📖 Contribution Guidelines
It's highly recommended to read the project's contribution guidelines before you start coding.
- **Contribution Guidelines:** {contributing_url}

## 🚀 Next Steps with Modal (Coming on Day 4!)
- Analysis of top-level files and project structure.
- Automated checks or environment setup suggestions.

Happy contributing! Remember to communicate with the project maintainers if you have questions.
"""
    return kit_markdown.strip()