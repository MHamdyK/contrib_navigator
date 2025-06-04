# core/kit_generator.py
from .github_client import get_repository_details, get_file_url_from_repo
# --- NEW IMPORT ---
from .modal_processor import get_repo_file_listing_via_modal

def generate_basic_kit_content(issue_data: dict) -> str:
    """
    Generates Markdown content for an onboarding kit for a given issue,
    now including a file listing from Modal if successful.
    """
    if not issue_data:
        return "Error: No issue data provided to generate kit."

    issue_title = issue_data.get("title", "N/A")
    issue_html_url = issue_data.get("html_url", "#")
    repo_html_url = issue_data.get("repository_html_url", "#")
    repo_api_url = issue_data.get("repository_api_url")

    repo_full_name = None
    if repo_html_url and repo_html_url.startswith("https://github.com/"):
        parts = repo_html_url.split('/')
        if len(parts) >= 5:
            repo_full_name = f"{parts[3]}/{parts[4]}"

    contributing_url_markdown = "Not found or could not be determined."
    default_branch_name = "main (assumed)"
    branch_from_api = None # Initialize

    if repo_full_name:
        if repo_api_url:
            repo_details = get_repository_details(repo_api_url)
            if repo_details and repo_details.get("default_branch"):
                branch_from_api = repo_details.get("default_branch")
                default_branch_name = branch_from_api
        else:
            temp_repo_api_url = f"https://api.github.com/repos/{repo_full_name}"
            repo_details = get_repository_details(temp_repo_api_url)
            if repo_details and repo_details.get("default_branch"):
                branch_from_api = repo_details.get("default_branch")
                default_branch_name = branch_from_api
        
        contributing_paths = [
            "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
            "CONTRIBUTING.rst", ".github/CONTRIBUTING.rst"
        ]
        found_contrib_url = get_file_url_from_repo(repo_full_name, contributing_paths, default_branch=branch_from_api)
        if found_contrib_url:
            contributing_url_markdown = f"[{found_contrib_url}]({found_contrib_url})"
    else:
        print("Warning (kit_generator): Could not derive repo_full_name. Some details might be missing.")

    # --- MODAL INTEGRATION FOR FILE LISTING ---
    modal_file_listing_markdown = "Could not retrieve repository file listing at this time." # Default
    if repo_html_url and repo_html_url != "#": # Ensure we have a valid repo URL
        print(f"Kit Generator: Requesting file listing for {repo_html_url} via Modal...")
        modal_response = get_repo_file_listing_via_modal(repo_html_url + ".git") # Ensure .git suffix if needed by clone

        if modal_response and modal_response.get("status") == "success":
            files = modal_response.get("files", [])
            if files:
                # Limit the number of files displayed for brevity in the kit
                max_files_to_display = 15
                file_list_items = [f"- `{item}`" for item in files[:max_files_to_display]]
                if len(files) > max_files_to_display:
                    file_list_items.append(f"- ... and {len(files) - max_files_to_display} more.")
                
                modal_file_listing_markdown = (
                    "Here's a quick look at some top-level files and folders "
                    "(obtained via a sandboxed clone on Modal):\n" +
                    "\n".join(file_list_items)
                )
            else:
                modal_file_listing_markdown = "Repository cloned successfully via Modal, but no files were found at the top level (or the list was empty)."
        elif modal_response: # Error status from Modal
            modal_file_listing_markdown = f"Could not retrieve repository file listing via Modal: {modal_response.get('message', 'Unknown error')}"
        # If modal_response is None, the default message for modal_file_listing_markdown remains.
    else:
        modal_file_listing_markdown = "Repository URL not available to fetch file listing."
    # --- END MODAL INTEGRATION ---


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
- **Contribution Guidelines:** {contributing_url_markdown}

## 📂 Quick Look: Repository Structure (via Modal)
{modal_file_listing_markdown}

Happy contributing! Remember to communicate with the project maintainers if you have questions.
"""
    return kit_markdown.strip()