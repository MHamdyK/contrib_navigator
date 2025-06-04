import gradio as gr # type: ignore
import os
from core.github_client import fetch_beginner_issues
from core.llm_handler import get_simple_issue_suggestion
from core.kit_generator import generate_basic_kit_content
import utils.config_loader


COMMON_PROGRAMMING_LANGUAGES = {
    "python", "javascript", "java", "c#", "c++", "c", "go", "rust", "ruby", "php",
    "swift", "kotlin", "typescript", "html", "css", "sql", "r", "perl", "scala",
    "haskell", "lua", "dart", "elixir", "clojure", "objective-c"

}
# Function: find_and_suggest_issues(language_input: str)
# (Your full function code as we just reviewed - it was correct)
def find_and_suggest_issues(language_input: str):
    print(f"Gradio app received language: {language_input}")
    language_input_lower = language_input.strip().lower() # Normalize

    if not language_input_lower:
        return ("Please enter a programming language.", None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False))

    # Check if the language is common, prepare a potential warning for the LLM/user
    is_common_language = language_input_lower in COMMON_PROGRAMMING_LANGUAGES
    language_warning_for_llm = ""
    if not is_common_language and len(language_input_lower) > 1 : # Avoid warning for single letters like 'c' or 'r' if not in list
        print(f"Warning: '{language_input}' is not in the common languages list. GitHub API might return broad results.")
        # This warning could also be displayed in the UI if we add another output component for general status.
        # For the LLM prompt, we might want to make it aware.
        language_warning_for_llm = (
            f"The user searched for the language '{language_input}', which is not in our common list. "
            "The following issues were found based on labels, but may not strictly be for this language. "
            "Please base your suggestion on the apparent language of the issues themselves if possible, "
            "or note if the language seems mismatched."
        )

    fetched_issues_list = fetch_beginner_issues(language_input_lower, per_page=5) # Use normalized language

    if fetched_issues_list is None:
        error_msg = "Error: Could not fetch issues from GitHub. Check server logs."
        return (error_msg, None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False))

    # THIS IS THE KEY CHANGE: If GitHub returns issues for a language we suspect isn't real,
    # it means it ignored the language filter. We should inform the user.
    if not fetched_issues_list: # No issues at all
        no_issues_msg = f"No beginner-friendly issues found for '{language_input}' with current labels."
        return (no_issues_msg, None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False))

    # If issues were found, but the language was not common, prepend a warning to the issue display
    issues_markdown_prefix = ""
    if not is_common_language and len(language_input_lower) > 1:
        issues_markdown_prefix = (
            f"⚠️ **Note:** '{language_input}' is not a commonly recognized programming language. "
            f"The issues below were found based on labels like 'good first issue' and may not be specific to '{language_input}'.\n\n---\n"
        )

    issues_display_list = []
    issue_titles_for_dropdown = []
    for i, issue in enumerate(fetched_issues_list[:5]):
        # ... (formatting issues as before) ...
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
    llm_suggestion_text = "Could not get LLM suggestion."
    if issues_for_llm and utils.config_loader.OPENAI_API_KEY:
        print(f"Sending {len(issues_for_llm)} issues to LLM for suggestion...")
        # Pass the language warning to the LLM handler, which can then prepend it to the system/user prompt
        suggestion = get_simple_issue_suggestion(
            issues_for_llm,
            language_input, # Original input for context
            target_count=1,
            additional_prompt_context=language_warning_for_llm # NEW parameter
        )
        if suggestion:
            llm_suggestion_text = f"**🤖 AI Navigator's Suggestion:**\n\n{suggestion}"
        else:
            llm_suggestion_text = "LLM gave an empty response or error."
    elif not utils.config_loader.OPENAI_API_KEY:
        llm_suggestion_text = "OpenAI API Key not configured. LLM suggestion skipped."
    elif not issues_for_llm: # Should be caught by `if not fetched_issues_list` earlier
         llm_suggestion_text = "No issues were found to provide a suggestion for."


    kit_dropdown_update = gr.update(choices=issue_titles_for_dropdown, value=issue_titles_for_dropdown[0] if issue_titles_for_dropdown else None)
    kit_button_visibility_update = gr.update(visible=True)
    kit_controls_section_update = gr.update(visible=True)
    kit_display_section_update = gr.update(visible=True)
    return (issues_markdown, llm_suggestion_text, fetched_issues_list,
            kit_dropdown_update, kit_button_visibility_update,
            kit_controls_section_update, kit_display_section_update)


# Function: handle_kit_generation(selected_issue_title_with_num: str, current_issues_state: list[dict])
# (Your full function code - it was correct)
def handle_kit_generation(selected_issue_title_with_num: str, current_issues_state: list[dict]):
    if not selected_issue_title_with_num or not current_issues_state:
        return "Please select an issue first, or fetch issues if the list is empty."
    try:
        selected_issue_obj = None
        for i, issue_in_state in enumerate(current_issues_state):
            numbered_title_in_state = f"{i+1}. {issue_in_state.get('title', 'N/A')}"
            if numbered_title_in_state == selected_issue_title_with_num:
                selected_issue_obj = issue_in_state
                break
        if not selected_issue_obj:
            return f"Error: Could not find data for selected issue '{selected_issue_title_with_num}'. State might be stale."
        print(f"Generating kit for: {selected_issue_obj.get('title')}")
        kit_markdown_content = generate_basic_kit_content(selected_issue_obj)
        return kit_markdown_content
    except Exception as e:
        print(f"Error during kit generation: {e}")
        return f"An error occurred while generating the kit: {str(e)}"


# Define the Gradio interface
# 'demo' is defined by this 'with' statement and is in scope for 'demo.launch()' below
with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 ContribNavigator: Your AI Guide to Open Source Contributions")
    gr.Markdown("Enter a programming language to find beginner-friendly open source issues and get an AI-powered suggestion.")

    with gr.Row():
        with gr.Column(scale=1): # Input column
            lang_input = gr.Textbox(label="Enter Programming Language", placeholder="e.g., python, javascript")
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

    find_button.click(
        fn=find_and_suggest_issues,
        inputs=[lang_input],
        outputs=[
            issues_output, llm_suggestion_output, raw_issues_state,
            selected_issue_dropdown, generate_kit_button,
            kit_controls_section, kit_display_section
        ]
    )

    generate_kit_button.click(
        fn=handle_kit_generation,
        inputs=[selected_issue_dropdown, raw_issues_state],
        outputs=[kit_output]
    )

# Launch the Gradio app
if __name__ == "__main__":
    print("Launching ContribNavigator Gradio App...")
    demo.launch() # 'demo' from the 'with gr.Blocks() as demo:' line is now in scope here