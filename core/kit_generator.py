# core/kit_generator.py
from .github_client import get_repository_details, get_file_url_from_repo, get_file_content
from .modal_processor import get_repo_file_listing_via_modal
from .llm_handler import summarize_text_content, suggest_relevant_code_locations

# --- Helper function to get common repo info needed by multiple sections ---
def _get_common_repo_info(issue_data: dict) -> tuple[str | None, str | None, str]:
    """Extracts/derives repo_full_name, repo_api_url, and default_branch_name."""
    repo_html_url = issue_data.get("repository_html_url", "#")
    repo_api_url = issue_data.get("repository_api_url")
    
    repo_full_name = None
    if repo_html_url and repo_html_url.startswith("https://github.com/"):
        parts = repo_html_url.split('/')
        if len(parts) >= 5:
            repo_full_name = f"{parts[3]}/{parts[4]}"

    branch_from_api = None
    default_branch_name = "main (assumed)" # Fallback
    if repo_full_name:
        # Use the direct repo_api_url from issue_data if available and valid
        current_repo_api_url = repo_api_url
        if not current_repo_api_url or not current_repo_api_url.startswith("https://api.github.com/repos/"):
            # If not valid, construct it from repo_full_name
            current_repo_api_url = f"https://api.github.com/repos/{repo_full_name}"
            print(f"Kit Generator (_get_common_repo_info): Constructed repo_api_url: {current_repo_api_url}")

        repo_details = get_repository_details(current_repo_api_url)
        if repo_details and repo_details.get("default_branch"):
            branch_from_api = repo_details.get("default_branch")
            default_branch_name = branch_from_api
    
    return repo_full_name, branch_from_api, default_branch_name

# --- Helper functions for generating individual kit sections ---

def _generate_repo_details_section(issue_data: dict, default_branch_name: str) -> str:
    issue_title = issue_data.get("title", "N/A")
    issue_html_url = issue_data.get("html_url", "#")
    repo_html_url = issue_data.get("repository_html_url", "#")
    
    # Ensure .git suffix for clone command displayed to user
    clone_url_display = repo_html_url if repo_html_url.endswith(".git") else repo_html_url + ".git"
    repo_name_for_cd = repo_html_url.split('/')[-1] if repo_html_url != "#" else "repository-name"


    return f"""
## 🔗 Issue Details
- **Issue Link:** [{issue_title}]({issue_html_url})
- **Repository:** [{repo_html_url}]({repo_html_url})

## 🛠️ Initial Setup Guide
1.  **Clone the Repository:**
    Open your terminal and run the following command to clone the repository to your local machine:
    ```bash
    git clone {clone_url_display}
    ```
    *(Note: Ensure you have Git installed. The repository might use a different default branch name than '{default_branch_name}'.)*

2.  **Navigate into the Project Directory:**
    ```bash
    cd {repo_name_for_cd}
    ```
    *(This assumes the directory name matches the repository name. Adjust if needed.)*
"""

def _generate_contribution_guidelines_section(
    repo_full_name: str | None,
    branch_from_api: str | None
) -> str:
    section_title = "## 📖 Contribution Guidelines\nIt's highly recommended to read the project's contribution guidelines before you start coding.\n"
    guidelines_link_markdown = "- **Guidelines Link:** _Could not find contribution guidelines in common locations._"
    summary_markdown = ""

    if repo_full_name:
        contributing_paths_to_check = [
            "CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md",
            "CONTRIBUTING.rst", ".github/CONTRIBUTING.rst", "CONTRIBUTING"
        ]
        
        found_contrib_display_url = get_file_url_from_repo(repo_full_name, contributing_paths_to_check, default_branch=branch_from_api)
        
        if found_contrib_display_url:
            guidelines_link_markdown = f"- **Guidelines Link:** [{found_contrib_display_url}]({found_contrib_display_url})"
            
            path_that_worked = None
            for p in contributing_paths_to_check: # Try to infer path for content fetching
                if p.lower() in found_contrib_display_url.lower():
                    path_that_worked = p
                    break
            
            if path_that_worked:
                print(f"Kit Generator (_contrib_guidelines): Found guidelines at '{path_that_worked}'. Fetching content...")
                contrib_content_text = get_file_content(repo_full_name, path_that_worked, branch=branch_from_api)
                if contrib_content_text:
                    print("Kit Generator (_contrib_guidelines): Content fetched. Requesting LLM summary...")
                    summary = summarize_text_content(contrib_content_text, purpose="contribution guidelines")
                    if summary and "LLM Client not initialized" not in summary and "LLM API error" not in summary and "No content provided" not in summary:
                        summary_markdown = f"\n\n**Key Takeaways (AI Summary):**\n{summary}"
                    else:
                        summary_markdown = "\n\n_AI summary for contribution guidelines could not be generated at this time._"
                        print(f"Kit Generator (_contrib_guidelines): LLM summary failed or returned error: {summary}")
                else:
                    summary_markdown = "\n\n_Could not fetch content of contribution guidelines for AI summary._"
            else:
                summary_markdown = "\n\n_Could not determine specific path of contribution file for AI summary, but a link was found._"
    
    return f"{section_title}{guidelines_link_markdown}{summary_markdown}"

def _generate_modal_repo_structure_section(
    issue_data: dict, # Contains repo_html_url and issue_body_snippet
    language_searched: str
) -> str:
    section_title = "## 📂 Quick Look: Repository Structure (via Modal)\n"
    modal_file_listing_text = "_Could not retrieve repository file listing at this time._"
    ai_suggested_files_text = ""

    repo_html_url = issue_data.get("repository_html_url", "#")
    issue_body_snippet = issue_data.get("body_snippet", "No issue description snippet available.")

    if repo_html_url and repo_html_url != "#":
        print(f"Kit Generator (_modal_structure): Requesting file listing for '{repo_html_url}' via Modal...")
        clone_url_for_modal = repo_html_url if repo_html_url.endswith(".git") else repo_html_url + ".git"
        modal_response = get_repo_file_listing_via_modal(clone_url_for_modal)

        if modal_response and modal_response.get("status") == "success":
            files_from_modal = modal_response.get("files", [])
            if files_from_modal:
                max_files_to_display = 15
                file_list_items = [f"- `{item}`" for item in files_from_modal[:max_files_to_display]]
                if len(files_from_modal) > max_files_to_display:
                    file_list_items.append(f"- ... and {len(files_from_modal) - max_files_to_display} more.")
                modal_file_listing_text = ("Here's a quick look at some top-level files and folders:\n" +
                                           "\n".join(file_list_items))

                print("Kit Generator (_modal_structure): Sending file list and issue snippet to LLM for relevant file suggestions.")
                ai_suggestions = suggest_relevant_code_locations(
                    issue_snippet=issue_body_snippet,
                    file_list=files_from_modal,
                    language=language_searched
                )
                if ai_suggestions and "LLM Client not initialized" not in ai_suggestions and "LLM API error" not in ai_suggestions:
                    ai_suggested_files_text = f"\n\n**💡 AI Suggested Starting Points (based on issue & file list):**\n{ai_suggestions}"
                else:
                    ai_suggested_files_text = "\n\n_AI could not suggest specific files to start with for this issue at this time._"
            else:
                modal_file_listing_text = "_Repository cloned successfully via Modal, but no files were found at the top level._"
        elif modal_response:
            modal_file_listing_text = f"_Could not retrieve repository file listing via Modal: {modal_response.get('message', 'Unknown error from Modal')}_"
    else:
        modal_file_listing_text = "_Repository URL not available to fetch file listing._"
        
    return f"{section_title}{modal_file_listing_text}{ai_suggested_files_text}"


# --- Main New Orchestrating Function ---
def generate_kit_from_plan(
    issue_data: dict,
    language_searched: str,
    components_to_include: list[str]
) -> str:
    """
    Generates Markdown content for an onboarding kit for a given issue,
    based on a plan specifying which components to include.
    """
    if not issue_data:
        return "Error: No issue data provided to generate kit."
    if not components_to_include:
        return "Error: No components specified for kit generation plan."

    print(f"Kit Generator (plan): Starting kit generation with components: {components_to_include}")

    # Fetch common repo info once
    repo_full_name, branch_from_api, default_branch_name = _get_common_repo_info(issue_data)
    
    # Header for the kit
    issue_title = issue_data.get("title", "N/A")
    kit_header = f"""
# 👋 Onboarding Kit for: {issue_title}

Congratulations on choosing this issue! Here's some information to help you get started.
"""
    markdown_parts = [kit_header.strip()]

    # Generate sections based on the plan
    if "repo_details_and_clone_command" in components_to_include:
        print("Kit Generator (plan): Adding repo details and clone command.")
        markdown_parts.append(_generate_repo_details_section(issue_data, default_branch_name))

    # For guidelines, we handle link and summary together if summary is requested
    # The LLM planner should ideally request "contribution_guidelines_summary_ai" which implies needing the link.
    # If only "contribution_guidelines_link" is requested, we can adapt.
    generate_guidelines_link = "contribution_guidelines_link" in components_to_include
    generate_guidelines_summary = "contribution_guidelines_summary_ai" in components_to_include

    if generate_guidelines_link or generate_guidelines_summary:
        print("Kit Generator (plan): Adding contribution guidelines section (link and/or summary).")
        # The helper function _generate_contribution_guidelines_section now handles both
        # and will only generate summary if content is fetched.
        # We can refine it to only fetch/summarize if generate_guidelines_summary is true.
        # For now, let's make the helper smarter or adjust the planner.
        #
        # Simplified: Let _generate_contribution_guidelines_section do its thing.
        # If only link was asked, it will still try to get content for summary but summary_markdown will be empty if not asked.
        # This needs further refinement if we want to strictly adhere to planner *not* doing summary if not asked.
        #
        # Let's adjust the helper to accept a flag for summary.
        # For now, the existing _generate_contribution_guidelines_section will attempt summary if content is found.
        # We will rely on the LLM planner to be smart. If it asks for summary, it implies link is also useful.
        guidelines_section_md = _generate_contribution_guidelines_section(repo_full_name, branch_from_api)
        
        # Temporary fix: if only link is requested, strip summary if it was generated.
        # This is a bit hacky, better to pass a flag to the helper.
        if generate_guidelines_link and not generate_guidelines_summary:
            if "**Key Takeaways (AI Summary):**" in guidelines_section_md:
                guidelines_section_md = guidelines_section_md.split("**Key Takeaways (AI Summary):**")[0].strip()
        
        markdown_parts.append(guidelines_section_md)


    if "repository_structure_modal_ai" in components_to_include:
        print("Kit Generator (plan): Adding repository structure (Modal) and AI file suggestions.")
        markdown_parts.append(_generate_modal_repo_structure_section(issue_data, language_searched))

    # Footer
    markdown_parts.append("\nHappy contributing! Remember to communicate with the project maintainers if you have questions.")
    
    return "\n\n".join(markdown_parts).strip()


# --- Keep your old generate_basic_kit_content for now, or comment out/remove if fully replaced ---
# def generate_basic_kit_content(issue_data: dict, language_searched: str) -> str:
#    # ... your previous full implementation ...
#    # This will eventually be replaced by calls to generate_kit_from_plan
#    print("WARNING: generate_basic_kit_content is called, should be generate_kit_from_plan")
#    # For now, let it be, app.py will call the new one once updated.
#    # To avoid breaking app.py immediately, we can have it call the new function with a default plan.
    default_plan_for_basic = [
        "repo_details_and_clone_command",
        "contribution_guidelines_link", # Basic just wants the link
        # "contribution_guidelines_summary_ai", # Not in "basic"
        "repository_structure_modal_ai" # Basic had the modal files and AI suggestions
    ]
    return generate_kit_from_plan(issue_data, language_searched, default_plan_for_basic)