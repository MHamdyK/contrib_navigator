import gradio as gr # type: ignore
import os
from core.github_client import fetch_beginner_issues # Updated to handle topics
from core.llm_handler import get_simple_issue_suggestion
from core.kit_generator import generate_basic_kit_content
import utils.config_loader


COMMON_PROGRAMMING_LANGUAGES = {
    "python", "javascript", "java", "c#", "c++", "c", "go", "rust", "ruby", "php",
    "swift", "kotlin", "typescript", "html", "css", "sql", "r", "perl", "scala",
    "haskell", "lua", "dart", "elixir", "clojure", "objective-c"
}

# --- MODIFIED FUNCTION SIGNATURE AND LOGIC ---
def find_and_suggest_issues(language_input_str: str, topics_input_str: str | None = None):
    print(f"Gradio app received language: '{language_input_str}', topics: '{topics_input_str}'")
    language_input_lower = language_input_str.strip().lower() if language_input_str else ""

    # --- NEW: Parse topics ---
    parsed_topics_list = None
    if topics_input_str:
        parsed_topics_list = [topic.strip().lower() for topic in topics_input_str.split(',') if topic.strip()]
        if not parsed_topics_list: # If string was just commas or whitespace resulting in empty list
            parsed_topics_list = None
    print(f"Parsed topics: {parsed_topics_list}")
    # --- END NEW: Parse topics ---

    if not language_input_lower:
        return ("Please enter a programming language.", None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False))

    is_common_language = language_input_lower in COMMON_PROGRAMMING_LANGUAGES
    language_warning_for_llm = ""
    if not is_common_language and len(language_input_lower) > 1:
        print(f"Warning: '{language_input_str}' is not in the common languages list.")
        language_warning_for_llm = (
            f"The user searched for language '{language_input_str}', which isn't common. "
            "Issues found are label-based (and topic-based if topics were provided); "
            "assess language match if possible."
        )

    # --- MODIFIED CALL: Pass parsed_topics_list to fetch_beginner_issues ---
    fetched_issues_list = fetch_beginner_issues(
        language_input_lower,
        topics=parsed_topics_list, # Pass parsed topics
        per_page=5
    )

    if fetched_issues_list is None:
        error_msg = "Error: Could not fetch issues from GitHub. Check server logs for details from github_client."
        return (error_msg, None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False))

    if not fetched_issues_list:
        no_issues_msg = f"No beginner-friendly issues found for '{language_input_str}'"
        if parsed_topics_list: # MODIFIED: Include topics in the message
            no_issues_msg += f" with topics '{', '.join(parsed_topics_list)}'"
        no_issues_msg += " using current labels. Try different criteria."
        return (no_issues_msg, None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False))

    issues_markdown_prefix = ""
    if not is_common_language and len(language_input_lower) > 1:
        issues_markdown_prefix = (
            f"⚠️ **Note:** '{language_input_str}' is not a commonly recognized programming language. "
            f"The issues below were found based on labels and topics and may not be specific to '{language_input_str}'.\n\n---\n"
        )

    issues_display_list = []
    issue_titles_for_dropdown = []
    for i, issue in enumerate(fetched_issues_list[:5]):
        title = issue.get('title', 'N/A')
        issues_display_list.append(
            f"{i+1}. **{title}**\n"
            f"   - Repo: [{issue.get('repository_html_url', '#')}]({issue.get('repository_html_url', '#')})\n"
            f"   - URL: [{issue.get('html_url', '#')}]({issue.get('html_url', '#')})\n"
            f"   - Labels: {', '.join(issue.get('labels', []))}\n"
        )
        issue_titles_for_dropdown.append(f"{i+1}. {title}")
    issues_markdown = issues_markdown_prefix + "\n---\n".join(issues_display_list)

    issues_for_llm = fetched_issues_list[:3]
    llm_suggestion_text = "Could not get LLM suggestion at this moment." # Default
    if issues_for_llm and utils.config_loader.OPENAI_API_KEY:
        # print(f"App.py: Sending {len(issues_for_llm)} issues to LLM...") # Already printed in llm_handler
        suggestion = get_simple_issue_suggestion(
            issues_for_llm,
            language_input_str,
            target_count=1,
            additional_prompt_context=language_warning_for_llm
        )
        if suggestion:
            llm_suggestion_text = f"**🤖 AI Navigator's Suggestion:**\n\n{suggestion}"
        else:
            llm_suggestion_text = "LLM processed the request but gave an empty response or an error occurred (see server logs)."
    elif not utils.config_loader.OPENAI_API_KEY:
        llm_suggestion_text = "OpenAI API Key not configured. LLM suggestion skipped."
    elif not issues_for_llm: # This case should be caught by "if not fetched_issues_list" earlier
         llm_suggestion_text = "No issues were available to provide a suggestion for."

    kit_dropdown_update = gr.update(choices=issue_titles_for_dropdown, value=issue_titles_for_dropdown[0] if issue_titles_for_dropdown else None)
    kit_button_visibility_update = gr.update(visible=True)
    kit_controls_section_update = gr.update(visible=True)
    kit_display_section_update = gr.update(visible=True)
    return (
        issues_markdown,                    # 1
        llm_suggestion_text,                # 2
        fetched_issues_list,                # 3 (for raw_issues_state)
        kit_dropdown_update,                # 4 (for selected_issue_dropdown)
        kit_button_visibility_update,       # 5 (for generate_kit_button)
        kit_controls_section_update,        # 6 (for kit_controls_section)
        kit_display_section_update,          # 7 (for kit_display_section)
        language_input_lower
    )


def handle_kit_generation(
    selected_issue_title_with_num: str,
    current_issues_state: list[dict],
    language_searched_state: str # NEW parameter from gr.State
):
    if not selected_issue_title_with_num or not current_issues_state:
        return "Please select an issue first, or fetch issues if the list is empty."
    if not language_searched_state: # Should not happen if flow is correct
        print("Warning (handle_kit_generation): Language searched was not found in state.")
        # Fallback or use a default, though ideally this state should always be populated
        language_searched_state = "the project's language" # Generic fallback

    try:
        selected_issue_obj = None
        # ... (logic to find selected_issue_obj remains the same) ...
        for i, issue_in_state in enumerate(current_issues_state):
            numbered_title_in_state = f"{i+1}. {issue_in_state.get('title', 'N/A')}"
            if numbered_title_in_state == selected_issue_title_with_num:
                selected_issue_obj = issue_in_state
                break
        if not selected_issue_obj:
            return f"Error: Could not find data for selected issue '{selected_issue_title_with_num}'."

        print(f"App.py: Generating kit for: {selected_issue_obj.get('title')} (Language context: {language_searched_state})")
        # --- MODIFIED CALL: Pass language_searched_state ---
        kit_markdown_content = generate_basic_kit_content(selected_issue_obj, language_searched_state)
        return kit_markdown_content
    except Exception as e:
        print(f"App.py: Error during kit generation: {e}")
        return f"An error occurred while generating the kit: {str(e)}"


with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 ContribNavigator: Your AI Guide to Open Source Contributions")
    gr.Markdown("Enter a programming language and optional topics (comma-separated) to find beginner-friendly open source issues.") # MODIFIED

    with gr.Row():
        with gr.Column(scale=1): # Input column
            lang_input = gr.Textbox(label="Programming Language (*)", placeholder="e.g., python, javascript") # Added (*) for required
            # --- NEW INPUT FIELD for Topics ---
            topics_input = gr.Textbox(label="Topics of Interest (Optional, comma-separated)", placeholder="e.g., machine-learning, web-dev, cli")
            # --- END NEW INPUT FIELD ---
            find_button = gr.Button("🔍 Find Beginner Issues", variant="primary")

            with gr.Column(visible=False) as kit_controls_section:
                selected_issue_dropdown = gr.Dropdown(
                    label="Select an Issue to Generate Kit:",
                    choices=[],
                    interactive=True
                )
                generate_kit_button = gr.Button("🛠️ Generate Onboarding Kit", visible=False)

        with gr.Column(scale=2): # Output column (issues and LLM)
            gr.Markdown("## Recommended Issues:")
            issues_output = gr.Markdown(value="Your recommended issues will appear here...")
            gr.Markdown("## Navigator's Insights:")
            llm_suggestion_output = gr.Markdown(value="AI-powered suggestions will appear here...")

            with gr.Column(visible=False) as kit_display_section:
                gr.Markdown("## 📖 Your Onboarding Kit:")
                kit_output = gr.Markdown("Your onboarding kit will appear here...")

    raw_issues_state = gr.State([])

    language_searched_state = gr.State("") # To store the last searched language

    find_button.click(
        fn=find_and_suggest_issues,
        inputs=[lang_input, topics_input],
        outputs=[
            issues_output, llm_suggestion_output, raw_issues_state,
            selected_issue_dropdown, generate_kit_button,
            kit_controls_section, kit_display_section,
            language_searched_state # ADDED: output to the new state
        ]
    )

    generate_kit_button.click(
        fn=handle_kit_generation,
        # --- MODIFIED INPUTS ---
        inputs=[selected_issue_dropdown, raw_issues_state, language_searched_state],
        outputs=[kit_output]
    )

if __name__ == "__main__":
    print("Launching ContribNavigator Gradio App...")
    demo.launch()