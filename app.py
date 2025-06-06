import gradio as gr # type:ignore
import os
from core.github_client import fetch_beginner_issues
from core.llm_handler import get_simple_issue_suggestion, plan_onboarding_kit_components
from core.kit_generator import generate_kit_from_plan
import utils.config_loader

# --- NEW/UPDATED CONSTANTS ---
# (Incorporating your suggestions and expanding slightly)
CURATED_TOPIC_SLUGS = sorted(list(set([
    # Your suggestions (some are single, some multi-word)
    "javascript", "css", "config", "python", "html", "cli", "typescript", "tailwindcss", "github config", "llm", # "github config"
    "deep neural networks", "deep learning", "neural network", # Changed to spaces
    "tensorflow", "pytorch", "ml",
    "distributed systems", # Changed to spaces

    # Broad Categories (changed to spaces where appropriate)
    "web development", "mobile development", "game development", "machine learning",
    "data science", "artificial intelligence", "devops", "cybersecurity", "blockchain",
    "iot", "cloud computing", "big data", "robotics", "bioinformatics", "ar vr", # "ar vr" might be better as "augmented reality", "virtual reality" or keep as is if it's a common tag
    "natural language processing", "computer vision", "data visualization",
    # Specific Technologies & Frameworks
    "react", "angular", "vue", "nextjs", "nodejs", "svelte",
    "django", "flask", "spring", "dotnet", "ruby on rails", # "ruby on rails"
    "android", "ios", "flutter", "react native", # "react native"
    "scikit learn", "keras", "pandas", "numpy", # "scikit learn"
    "docker", "kubernetes", "aws", "azure", "google cloud platform", "serverless", # "google cloud platform"
    "sql", "nosql", "mongodb", "postgresql", "mysql", "graphql",
    "api", "gui", "testing", "documentation", "education", "accessibility",
    "raspberry pi", "arduino", "linux", "windows", "macos", "gaming", "graphics", "fintech" # "raspberry pi"
])))

CURATED_LANGUAGE_SLUGS = sorted([
    "python", "javascript", "java", "c#", "c++", "c", "go", "rust", "ruby", "php",
    "swift", "kotlin", "typescript", "html", "css", "sql", "r", "perl", "scala",
    "haskell", "lua", "dart", "elixir", "clojure", "objective-c", "shell", "powershell",
    "assembly", "matlab", "groovy", "julia", "ocaml", "pascal", "fortran", "lisp",
    "prolog", "erlang", "f#", "zig", "nim", "crystal", "svelte", "vue" # Svelte/Vue also as languages for their specific file types
])
# --- END NEW/UPDATED CONSTANTS ---


# --- MODIFIED FUNCTION: find_and_suggest_issues ---
def find_and_suggest_issues(
    selected_language: str | None, # From language dropdown
    selected_curated_topics: list[str] | None, # From topics dropdown (multiselect)
    custom_topics_str: str | None # From topics textbox
):
    print(f"Gradio app received language: '{selected_language}', curated_topics: {selected_curated_topics}, custom_topics: '{custom_topics_str}'")

    # --- Default error/empty returns for 8 outputs ---
    # issues_markdown, llm_suggestion, raw_issues_state,
    # dropdown_update, button_update, controls_section_update, display_section_update,
    # language_searched_state
    empty_error_return = (
        "Error or no input.", None, None,
        gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        "" # language_searched_state
    )
    no_issues_found_return_factory = lambda lang, topics_str: (
        f"No beginner-friendly issues found for '{lang}'" +
        (f" with topics '{topics_str}'" if topics_str else "") +
        " using current labels. Try different criteria.",
        None, None,
        gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
        gr.update(visible=False), gr.update(visible=False),
        lang or ""
    )
    # ---

    if not selected_language: # Language is now from a dropdown, should always have a value if user interacts
        return ("Please select a programming language.", None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False),
                "")

    language_to_search = selected_language.strip().lower() # Already a slug from dropdown

    # --- Combine curated and custom topics ---
    final_topics_set = set()
    if selected_curated_topics: # This will be a list from multiselect dropdown
        for topic in selected_curated_topics:
            if topic and topic.strip():
                final_topics_set.add(topic.strip().lower()) # Already slugs
    if custom_topics_str:
        custom_topics_list = [ct.strip().lower() for ct in custom_topics_str.split(',') if ct.strip()]
        for topic in custom_topics_list:
            final_topics_set.add(topic) # Add directly, github_client handles quoting if needed
    
    final_topics_list = list(final_topics_set) if final_topics_set else None
    print(f"Final parsed topics for search: {final_topics_list}")
    # --- End Combine topics ---

    # --- REMOVED: is_common_language and language_warning_for_llm logic ---
    # Since language comes from a curated dropdown, we assume it's "common" or valid.
    # The GitHub API will be the ultimate judge if it finds anything.

    fetched_issues_list = fetch_beginner_issues(
        language_to_search,
        topics=final_topics_list,
        per_page=5 # Fetch 5 issues
    )

    if fetched_issues_list is None: # GitHub API call failed
        return ("Error: Could not fetch issues from GitHub. Check server logs.", None, None,
                gr.update(choices=[], value=None, visible=False), gr.update(visible=False),
                gr.update(visible=False), gr.update(visible=False),
                language_to_search)

    if not fetched_issues_list: # No issues found
        return no_issues_found_return_factory(language_to_search, ", ".join(final_topics_list) if final_topics_list else None)

    # --- REMOVED: issues_markdown_prefix related to uncommon language ---
    # This is no longer needed if language is from a curated dropdown.

    issues_display_list = []
    issue_titles_for_dropdown = []
    for i, issue in enumerate(fetched_issues_list[:5]): # Display up to 5
        title = issue.get('title', 'N/A')
        issues_display_list.append(
            f"{i+1}. **{title}**\n"
            f"   - Repo: [{issue.get('repository_html_url', '#')}]({issue.get('repository_html_url', '#')})\n"
            f"   - URL: [{issue.get('html_url', '#')}]({issue.get('html_url', '#')})\n"
            f"   - Labels: {', '.join(issue.get('labels', []))}\n"
        )
        issue_titles_for_dropdown.append(f"{i+1}. {title}")
    issues_markdown = "\n---\n".join(issues_display_list)

    issues_for_llm = fetched_issues_list[:3]
    llm_suggestion_text = "Could not get LLM suggestion at this moment."
    if issues_for_llm and utils.config_loader.OPENAI_API_KEY:
        suggestion = get_simple_issue_suggestion( # Pass language_to_search
            issues_for_llm, language_to_search, target_count=1
            # additional_prompt_context for uncommon language is removed
        )
        if suggestion: llm_suggestion_text = f"**🤖 AI Navigator's Suggestion:**\n\n{suggestion}"
        else: llm_suggestion_text = "LLM processed the request but gave an empty response or an error occurred."
    elif not utils.config_loader.OPENAI_API_KEY:
        llm_suggestion_text = "OpenAI API Key not configured. LLM suggestion skipped."
    elif not issues_for_llm :
         llm_suggestion_text = "No issues were available to provide a suggestion for."

    kit_dropdown_update = gr.update(choices=issue_titles_for_dropdown, value=issue_titles_for_dropdown[0] if issue_titles_for_dropdown else None, visible=True)
    kit_button_visibility_update = gr.update(visible=True)
    kit_controls_section_update = gr.update(visible=True)
    kit_display_section_update = gr.update(visible=True)

    return (issues_markdown, llm_suggestion_text, fetched_issues_list,
            kit_dropdown_update, kit_button_visibility_update,
            kit_controls_section_update, kit_display_section_update,
            language_to_search) # Return the searched language for state
# --- END MODIFIED FUNCTION ---


# handle_kit_generation function (This function should be your last correct version)
# ... (Ensure your full handle_kit_generation is here)
def handle_kit_generation(selected_issue_title_with_num: str, current_issues_state: list[dict], language_searched_state: str ):
    checklist_update_on_error = gr.update(value=[], visible=False)
    if not selected_issue_title_with_num or not current_issues_state:
        return "Please select an issue first...", checklist_update_on_error
    if not language_searched_state:
        language_searched_state = "the project's primary language"
    selected_issue_obj = None
    try:
        for i, issue_in_state in enumerate(current_issues_state):
            numbered_title_in_state = f"{i+1}. {issue_in_state.get('title', 'N/A')}"
            if numbered_title_in_state == selected_issue_title_with_num:
                selected_issue_obj = issue_in_state
                break
        if not selected_issue_obj:
            return f"Error: Could not find data for issue '{selected_issue_title_with_num}'.", checklist_update_on_error
        plan_response = plan_onboarding_kit_components(selected_issue_obj, language_searched_state)
        if not plan_response or "error" in plan_response:
            error_detail = plan_response.get("details", "") if plan_response else "Planner None"
            return f"Error planning kit: {plan_response.get('error', 'Unknown')}. {error_detail}", checklist_update_on_error
        components_to_include = plan_response.get("include_components", [])
        if not components_to_include:
            return "AI planner decided no kit components needed.", checklist_update_on_error
        kit_markdown_content = generate_kit_from_plan(selected_issue_obj, language_searched_state, components_to_include)
        checklist_update_on_success = gr.update(value=[], visible=True)
        return kit_markdown_content, checklist_update_on_success
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"Unexpected error generating kit: {str(e)}", checklist_update_on_error


with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 ContribNavigator: Your AI Guide to Open Source Contributions")
    gr.Markdown("Select a programming language and optional topics to find beginner-friendly open source issues.") # MODIFIED

    with gr.Row():
        with gr.Column(scale=1): # Input column
            # --- MODIFIED Language Input to Dropdown ---
            lang_dropdown_input = gr.Dropdown(
                label="Programming Language (*)",
                choices=CURATED_LANGUAGE_SLUGS,
                value=CURATED_LANGUAGE_SLUGS[CURATED_LANGUAGE_SLUGS.index("python")] if "python" in CURATED_LANGUAGE_SLUGS else CURATED_LANGUAGE_SLUGS[0] if CURATED_LANGUAGE_SLUGS else None, # Default to python or first in list
                interactive=True,
                # allow_custom_value=True # Consider this if you want users to type languages not in the list
            )
            # --- END MODIFIED Language Input ---

            # --- NEW/MODIFIED Topics Input ---
            curated_topics_dropdown = gr.Dropdown(
                label="Select Common Topics (Optional, Multi-Select)",
                choices=CURATED_TOPIC_SLUGS,
                multiselect=True,
                interactive=True
            )
            custom_topics_input = gr.Textbox(
                label="Or, Add Custom Topics (Optional, comma-separated slugs)",
                placeholder="e.g., my-niche-topic, another-custom-tag"
            )
            # --- END NEW/MODIFIED Topics Input ---

            find_button = gr.Button("🔍 Find Beginner Issues", variant="primary")

            with gr.Column(visible=False) as kit_controls_section:
                selected_issue_dropdown = gr.Dropdown(
                    label="Select an Issue to Generate Kit:", choices=[], interactive=True, visible=True
                )
                generate_kit_button = gr.Button("🛠️ Generate Onboarding Kit", visible=False)

        with gr.Column(scale=2): # Output column
            gr.Markdown("## Recommended Issues:")
            issues_output = gr.Markdown(value="Your recommended issues will appear here...")
            gr.Markdown("## Navigator's Insights:")
            llm_suggestion_output = gr.Markdown(value="AI-powered suggestions will appear here...")

            with gr.Column(visible=False) as kit_display_section:
                gr.Markdown("## 📖 Your Onboarding Kit:")
                kit_output = gr.Markdown("Your onboarding kit will appear here...")
                # --- Using INITIAL_CHECKLIST_ITEMS constant for choices ---
                INITIAL_CHECKLIST_ITEMS = [
                    "Understand the Issue: Read the issue description carefully.",
                    "Explore the Repository: Use the 'Quick Look' section in the kit to get familiar.",
                    "Read Contribution Guidelines: Review the project's contribution rules and setup (see kit).",
                    "Clone the Repository: Get the code on your local machine (see kit for command).",
                    "Set Up Development Environment: Follow any setup instructions in the guidelines.",
                    "Create a New Branch: For your changes (e.g., `git checkout -b my-fix-for-issue-123`).",
                    "Make Initial Contact (Optional but good): Leave a comment on the GitHub issue expressing your interest.",
                    "Start Investigating/Coding!",
                    "Ask Questions: If you're stuck, don't hesitate to ask for help on the issue or project's communication channels."
                ]
                checklist_group_output = gr.CheckboxGroup(
                    label="✅ Your First Steps Checklist:",
                    choices=INITIAL_CHECKLIST_ITEMS,
                    value=[],
                    interactive=True,
                    visible=False # Starts hidden
                )
                # --- END Using INITIAL_CHECKLIST_ITEMS ---

    raw_issues_state = gr.State([])
    language_searched_state = gr.State("")

    # --- MODIFIED find_button.click inputs ---
    find_button.click(
        fn=find_and_suggest_issues,
        inputs=[lang_dropdown_input, curated_topics_dropdown, custom_topics_input], # UPDATED
        outputs=[
            issues_output, llm_suggestion_output, raw_issues_state,
            selected_issue_dropdown, generate_kit_button,
            kit_controls_section, kit_display_section,
            language_searched_state
        ]
    )
    # --- END MODIFIED find_button.click ---

    generate_kit_button.click(
        fn=handle_kit_generation,
        inputs=[selected_issue_dropdown, raw_issues_state, language_searched_state],
        outputs=[kit_output, checklist_group_output] # Targets CheckboxGroup
    )

if __name__ == "__main__":
    print("Launching ContribNavigator Gradio App...")
    demo.launch()