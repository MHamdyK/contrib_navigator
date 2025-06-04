# core/kit_generator.py
from .github_client import get_repository_details, get_file_url_from_repo, get_file_content # ADDED get_file_content
from .modal_processor import get_repo_file_listing_via_modal
# --- NEW IMPORTS ---
from .llm_handler import summarize_text_content, suggest_relevant_code_locations

# --- MODIFIED FUNCTION SIGNATURE ---
def generate_basic_kit_content(issue_data: dict, language_searched: str) -> str:
    """
    Generates Markdown content for an onboarding kit for a given issue,
    now including LLM summaries of contribution guidelines and AI-suggested relevant files.
    """
    if not issue_data:
        return "Error: No issue data provided to generate kit."

    issue_title = issue_data.get("title", "N/A")
    issue_html_url = issue_data.get("html_url", "#")
    # --- ADDED: Get issue_body_snippet for LLM context ---
    issue_body_snippet = issue_data.get("body_snippet", "No issue description snippet available.")
    repo_html_url = issue_data.get("repository_html_url", "#")
    repo_api_url = issue_data.get("repository_api_url")

    repo_full_name = None
    if repo_html_url and repo_html_url.startswith("https://github.com/"):
        parts = repo_html_url.split('/')
        if len(parts) >= 5:
            repo_full_name = f"{parts[3]}/{parts[4]}"

    # --- Contribution Guidelines Section Enhancement ---
    # (This section's heading will be added later in the final markdown)
    contribution_guidelines_details_markdown = "" # Will hold link and summary
    found_contrib_url_display = "_Could not find contribution guidelines in common locations._" # Default for link display
    
    branch_from_api = None
    default_branch_name = "main (assumed)"

    if repo_full_name:
        # Determine default branch
        if repo_api_url:
            repo_details = get_repository_details(repo_api_url)
            if repo_details and repo_details.get("default_branch"):
                branch_from_api = repo_details.get("default_branch")
                default_branch_name = branch_from_api
        else: # Fallback if repo_api_url wasn't directly in issue_data
            temp_repo_api_url = f"https://api.github.com/repos/{repo_full_name}"
            repo_details = get_repository_details(temp_repo_api_url)
            if repo_details and repo_details.get("default_branch"):
                branch_from_api = repo_details.get("default_branch")
                default_branch_name = branch_from_api
        
        contributing_paths_to_check = [
            "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
            "CONTRIBUTING.rst", ".github/CONTRIBUTING.rst", "CONTRIBUTING" # Added generic "CONTRIBUTING"
        ]
        
        # Find URL for display
        # And determine path_that_worked for fetching content
        path_that_worked = None
        # First, try to get the URL (which also confirms existence and branch)
        found_contrib_display_url = get_file_url_from_repo(repo_full_name, contributing_paths_to_check, default_branch=branch_from_api)

        if found_contrib_display_url:
            found_contrib_url_display = f"[{found_contrib_display_url}]({found_contrib_display_url})"
            # Try to infer the path that worked from the URL to fetch its content
            # This is a heuristic; a more robust get_file_url_from_repo could return the path.
            for p in contributing_paths_to_check:
                if p.lower() in found_contrib_display_url.lower():
                    path_that_worked = p
                    break
            
            if path_that_worked:
                print(f"Kit Generator: Found contribution file at '{path_that_worked}'. Fetching content for summary...")
                # Use branch_from_api if available, otherwise let get_file_content try its fallbacks
                contrib_content_text = get_file_content(repo_full_name, path_that_worked, branch=branch_from_api)
                if contrib_content_text:
                    print("Kit Generator: Contribution guidelines content fetched. Requesting LLM summary...")
                    summary = summarize_text_content(contrib_content_text, purpose="contribution guidelines")
                    if summary and "LLM Client not initialized" not in summary and "LLM API error" not in summary and "No content provided" not in summary:
                        contribution_guidelines_details_markdown += f"\n\n**Key Takeaways (AI Summary):**\n{summary}"
                    else:
                        contribution_guidelines_details_markdown += "\n\n_AI summary for contribution guidelines could not be generated at this time._"
                        print(f"Kit Generator: LLM summary for guidelines failed or returned error: {summary}")
                else:
                    print(f"Kit Generator: Could not fetch content of '{path_that_worked}' for summary.")
                    contribution_guidelines_details_markdown += "\n\n_Could not fetch content of contribution guidelines for AI summary._"
            else:
                contribution_guidelines_details_markdown += "\n\n_Could not determine the exact path of the contribution file for AI summary, but a link was found._"
        # else: # found_contrib_display_url is None, so default message for found_contrib_url_display is used
             # No need for additional prints here, get_file_url_from_repo logs its attempts.

    contribution_guidelines_section = f"""## 📖 Contribution Guidelines
It's highly recommended to read the project's contribution guidelines before you start coding.
- **Guidelines Link:** {found_contrib_url_display}{contribution_guidelines_details_markdown}"""
    # --- End Contribution Guidelines Enhancement ---


    # --- Modal File Listing & AI Suggested Files Enhancement ---
    # (This section's heading will be added later in the final markdown)
    repo_structure_details_markdown = "" # Will hold file list and AI suggestions
    modal_file_listing_text = "_Could not retrieve repository file listing at this time._" # Default for basic listing

    if repo_html_url and repo_html_url != "#":
        print(f"Kit Generator: Requesting file listing for '{repo_html_url}' via Modal...")
        clone_url = repo_html_url if repo_html_url.endswith(".git") else repo_html_url + ".git"
        modal_response = get_repo_file_listing_via_modal(clone_url)

        if modal_response and modal_response.get("status") == "success":
            files_from_modal = modal_response.get("files", [])
            if files_from_modal:
                max_files_to_display = 15
                file_list_items = [f"- `{item}`" for item in files_from_modal[:max_files_to_display]]
                if len(files_from_modal) > max_files_to_display:
                    file_list_items.append(f"- ... and {len(files_from_modal) - max_files_to_display} more.")
                modal_file_listing_text = ("Here's a quick look at some top-level files and folders "
                                           "(obtained via a sandboxed clone on Modal):\n" +
                                           "\n".join(file_list_items))

                # --- NEW: Get LLM suggestion for relevant files ---
                print("Kit Generator: Sending file list and issue snippet to LLM for relevant file suggestions.")
                ai_suggested_files = suggest_relevant_code_locations(
                    issue_snippet=issue_body_snippet, # Use the fetched issue snippet
                    file_list=files_from_modal,       # Full list from Modal
                    language=language_searched        # Language context from user search
                )
                if ai_suggested_files and "LLM Client not initialized" not in ai_suggested_files and "LLM API error" not in ai_suggested_files:
                    repo_structure_details_markdown += f"\n\n**💡 AI Suggested Starting Points (based on issue & file list):**\n{ai_suggested_files}"
                else:
                    repo_structure_details_markdown += "\n\n_AI could not suggest specific files to start with for this issue at this time._"
                    print(f"Kit Generator: LLM suggestion for relevant files failed or returned error: {ai_suggested_files}")
                # --- END NEW ---
            else: # Successfully cloned but file list from Modal was empty
                modal_file_listing_text = "_Repository cloned successfully via Modal, but no files were found at the top level (or the list was empty)._"
        elif modal_response: # Error status from Modal itself
            modal_file_listing_text = f"_Could not retrieve repository file listing via Modal: {modal_response.get('message', 'Unknown error from Modal')}_"
        # If modal_response is None, the default message for modal_file_listing_text remains.
    else: # repo_html_url was not valid
        modal_file_listing_text = "_Repository URL not available to fetch file listing._"
    
    repo_structure_section = f"""## 📂 Quick Look: Repository Structure (via Modal)
{modal_file_listing_text}{repo_structure_details_markdown}"""
    # --- End Modal File Listing & AI Suggested Files Enhancement ---


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

{contribution_guidelines_section}

{repo_structure_section}

Happy contributing! Remember to communicate with the project maintainers if you have questions.
"""
    return kit_markdown.strip()