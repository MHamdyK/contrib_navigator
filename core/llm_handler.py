import openai # Using the openai library for Nebius's OpenAI-compatible API
import os     # For environment variables if not using config_loader directly here
import json
# Import API key and base URL from our config loader
from utils.config_loader import OPENAI_API_KEY

# Initialize the OpenAI client
client = None
if OPENAI_API_KEY:
    try:
        client = openai.OpenAI(
            api_key=OPENAI_API_KEY
            # No base_url needed for direct OpenAI
        )
        print("OpenAI client initialized successfully in llm_handler.")
    except Exception as e:
        print(f"Error initializing OpenAI client in llm_handler: {e}")
        client = None
else:
    print("WARNING (llm_handler): OPENAI_API_KEY not configured. LLM calls will fail.")


def get_simple_issue_suggestion(
        issues_data: list[dict],
        language: str,
        target_count: int = 1,
        model_name: str = "gpt-4o-mini", # Or your preferred model
        additional_prompt_context: str = "" # NEW parameter
    ) -> str | None:
    """
    Sends issue data to OpenAI API to suggest which one(s) might be best for a beginner.
    """
    if not client:
        print("LLM client (OpenAI) in get_simple_issue_suggestion is not initialized.")
        return "LLM client (OpenAI) not initialized. Check API Key configuration."
    if not issues_data:
        print("No issues provided to LLM for suggestion.")
        return "No issues provided to LLM for suggestion."

    prompt_issues_str = "" # Rebuild this based on your existing logic
    for i, issue in enumerate(issues_data):
        snippet = issue.get('body_snippet', 'No description available.')
        title = issue.get('title', 'No title')
        url = issue.get('html_url', '#')
        labels = ", ".join(issue.get('labels', [])) if issue.get('labels') else "No labels"
        prompt_issues_str += (
            f"\n--- Issue {i+1} ---\n"
            f"Title: {title}\nURL: {url}\nLabels: {labels}\nSnippet from body: {snippet}\n-----------------\n"
        )

    system_prompt = (
        "You are an expert assistant helping a new open-source contributor. "
        "Your task is to analyze the provided list of GitHub issues and recommend "
        f"the top {target_count} that would be most suitable for a beginner ideally in {language} (if specified and makes sense for the issues). "
        "Consider factors like clarity, labels, and apparent scope. "
        f"{additional_prompt_context}" # ADDED additional context here
        " If the user-specified language seems mismatched with the provided issues, please make your best judgment "
        "based on the issue content itself or note the potential mismatch in your recommendation."
    )
    user_prompt = (
        # ... (user prompt construction as before, including prompt_issues_str) ...
        f"Here is a list of GitHub issues found when searching for the language '{language}'. "
        # (The additional_prompt_context is now in the system prompt)
        f"Please review them and suggest the top {target_count} issue(s) that seem most suitable for a beginner. "
        f"For each suggested issue, provide a concise explanation (1-2 sentences) stating *why* it's a good choice for a beginner. "
        f"If you suggest an issue, please refer to it by its number (e.g., 'Issue 1')."
        f"\nHere are the issues:\n{prompt_issues_str}"
    )

    temperature_val = 0.4
    max_tokens_val = 200 + (target_count * 150)
    top_p_val = 0.9 # Usually 1.0 for temperature-based sampling, or 0.9 if also using top_p

    print(f"\nSending request to OpenAI LLM for issue suggestion...")
    print(f"Model: {model_name}, Temp: {temperature_val}, MaxTokens: {max_tokens_val}")

    try:
        completion = client.chat.completions.create( # Ensure client is defined
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            # ... other params
            temperature=0.4,
            max_tokens=200 + (target_count * 150),
            top_p=0.9
        )

        suggestion_text = completion.choices[0].message.content
        print("OpenAI LLM Suggestion Received.")
        return suggestion_text.strip()

    except openai.APIConnectionError as e:
        print(f"OpenAI API Connection Error: {e}")
        return f"LLM suggestion failed due to connection error: {e}"
    except openai.RateLimitError as e: # Good to handle this explicitly
        print(f"OpenAI API Rate Limit Error: {e}")
        return f"LLM suggestion failed due to rate limit: {e}. Check your OpenAI plan and usage."
    except openai.AuthenticationError as e: # Added for bad API key
        print(f"OpenAI API Authentication Error: {e}. Check your OPENAI_API_KEY.")
        return f"LLM suggestion failed due to authentication error: {e}."
    except openai.APIStatusError as e:
        print(f"OpenAI API Status Error: Status {e.status_code} - Response: {e.response}")
        return f"LLM suggestion failed due to API status error: {e.status_code}"
    except Exception as e:
        print(f"LLM API call to OpenAI failed with an unexpected error: {e}")
        print(f"Type of error: {type(e)}")
        return f"LLM suggestion failed with an unexpected error: {e}"

# --- NEW FUNCTION 1: Summarize Text Content ---
def summarize_text_content(
        text_content: str,
        purpose: str = "contribution guidelines", # e.g., "issue description", "documentation section"
        max_summary_tokens: int = 200, # Adjust as needed
        model_name: str = "gpt-4o-mini" # Or your preferred model
    ) -> str | None:
    """
    Summarizes a given text content using an LLM.
    """
    if not client:
        print("ERROR (llm_handler.summarize_text_content): LLM client not initialized.")
        return "LLM Client not initialized. Cannot summarize."
    if not text_content or not text_content.strip():
        print("Warning (llm_handler.summarize_text_content): No text content provided to summarize.")
        return "No content provided for summarization."

    # Heuristic: If text is already short, just return it or a small part.
    # This avoids wasting API calls on tiny texts. (Count words approx)
    if len(text_content.split()) < 75 : # Arbitrary threshold for "short"
        print("Info (llm_handler.summarize_text_content): Content too short, returning as is or snippet.")
        return f"The {purpose} document is brief: \"{text_content[:500]}...\"" if len(text_content) > 500 else text_content


    system_prompt = (
        f"You are an expert summarizer. Your task is to provide a concise summary of the following '{purpose}' document. "
        "Focus on the most critical information a new contributor would need. "
        "For contribution guidelines, highlight key setup steps, coding style conventions, testing requirements, and pull request procedures. "
        "Keep the summary brief and actionable."
    )
    user_prompt = (
        f"Please summarize the key points of the following {purpose} document:\n\n"
        f"```text\n{text_content[:8000]}\n```" # Limit context sent to LLM
        # Using 8000 characters as a rough limit to fit within context windows & manage cost.
        # Adjust this based on typical CONTRIBUTING.md length and model context limits.
    )

    print(f"LLM Handler: Sending request to summarize {purpose}. Model: {model_name}")
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.2, # Lower temperature for factual summarization
            max_tokens=max_summary_tokens,
            top_p=1.0
        )
        summary_text = completion.choices[0].message.content
        print(f"LLM Handler: Summary for {purpose} received.")
        return summary_text.strip()
    except Exception as e:
        print(f"ERROR (llm_handler.summarize_text_content): LLM API call failed: {e}")
        return f"Could not summarize the {purpose}: LLM API error."

# --- NEW FUNCTION 2: Suggest Relevant Code Locations ---
def suggest_relevant_code_locations(
        issue_snippet: str,
        file_list: list[str],
        language: str, # Language of the project
        max_suggestion_tokens: int = 200, # Adjust as needed
        model_name: str = "gpt-4o-mini" # Or your preferred model
    ) -> str | None:
    """
    Suggests relevant files/folders based on an issue snippet and a list of files.
    """
    if not client:
        print("ERROR (llm_handler.suggest_relevant_code_locations): LLM client not initialized.")
        return "LLM Client not initialized. Cannot suggest locations."
    if not issue_snippet or not issue_snippet.strip():
        return "No issue description provided to suggest locations."
    if not file_list:
        return "No file list provided to suggest locations from."

    # Format file list for the prompt
    formatted_file_list = "\n".join([f"- `{f}`" for f in file_list])
    if not formatted_file_list: # Should not happen if file_list is not empty
        formatted_file_list = "No files listed."

    system_prompt = (
        f"You are an AI assistant helping a software developer navigate a new '{language}' codebase. "
        "Your goal is to identify potentially relevant files or folders for a given issue, based on a provided list of top-level project files/folders."
    )
    user_prompt = (
        f"A developer is starting work on an issue with the following description snippet:\n"
        f"'''\n{issue_snippet}\n'''\n\n"
        f"The top-level files and folders available in the repository are:\n"
        f"{formatted_file_list}\n\n"
        f"Based *only* on the issue snippet and this file list, please suggest 2-3 files or folders that might be most relevant for investigating this issue. "
        f"For each suggestion, provide a brief (1-sentence) explanation of why it might be relevant. "
        f"If no files seem obviously relevant from the top-level list, say so."
    )

    print(f"LLM Handler: Sending request to suggest relevant code locations. Model: {model_name}")
    try:
        completion = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.5, # Moderate temperature for some reasoning
            max_tokens=max_suggestion_tokens,
            top_p=1.0
        )
        suggestion_text = completion.choices[0].message.content
        print("LLM Handler: Code location suggestions received.")
        return suggestion_text.strip()
    except Exception as e:
        print(f"ERROR (llm_handler.suggest_relevant_code_locations): LLM API call failed: {e}")
        return f"Could not suggest code locations: LLM API error."

def plan_onboarding_kit_components(
        issue_data: dict,
        language_searched: str,
        model_name: str = "gpt-4.1-mini" # Or your preferred model
    ) -> dict | None:
    """
    Uses an LLM to decide which onboarding kit components are most relevant for a given issue.
    Returns a dictionary based on the LLM's JSON output.
    """
    if not client:
        print("ERROR (llm_handler.plan_kit): LLM client not initialized.")
        return None # Or: {"error": "LLM Client not initialized"}
    if not issue_data:
        print("ERROR (llm_handler.plan_kit): No issue data provided for planning.")
        return None # Or: {"error": "No issue data"}

    issue_title = issue_data.get("title", "N/A")
    issue_snippet = issue_data.get("body_snippet", "No description available.")
    issue_labels = issue_data.get("labels", [])

    # Define available kit components for the LLM to choose from
    available_components = [
        "repo_details_and_clone_command",      # Basic repo info, clone command
        "contribution_guidelines_link",        # Link to CONTRIBUTING.md
        "contribution_guidelines_summary_ai",  # AI Summary of CONTRIBUTING.md
        "repository_structure_modal_ai",       # File listing via Modal + AI suggested files
        # We could break down "repository_structure_modal_ai" further if needed:
        # "repository_files_modal_raw_list",
        # "ai_suggested_start_files_from_list"
    ]
    components_description = (
        "- repo_details_and_clone_command: Basic repository information and git clone command.\n"
        "- contribution_guidelines_link: A direct link to the project's CONTRIBUTING.md file (if found).\n"
        "- contribution_guidelines_summary_ai: An AI-generated summary of the key points from CONTRIBUTING.md.\n"
        "- repository_structure_modal_ai: A top-level file/folder listing from a repository clone (via Modal), followed by AI suggestions for relevant files based on the issue."
    )

    system_prompt = (
        "You are an expert onboarding assistant for open-source contributors. Your task is to intelligently plan "
        "the components of an onboarding kit that would be most helpful for a developer tackling a specific GitHub issue. "
        "You must respond ONLY with a valid JSON object containing a single key 'include_components' whose value is a list of strings, "
        "where each string is one of the component names provided."
    )
    user_prompt = (
        f"Based on the following GitHub issue details for a project searched under the language context '{language_searched}':\n"
        f"Issue Title: \"{issue_title}\"\n"
        f"Issue Snippet: \"{issue_snippet}\"\n"
        f"Issue Labels: {issue_labels}\n\n"
        f"And considering the following available onboarding kit components and their descriptions:\n"
        f"{components_description}\n\n"
        f"Which components should be included in the onboarding kit for this specific issue to be most helpful? "
        f"For example, if the issue is a very simple documentation typo, a full 'repository_structure_modal_ai' might be overkill. "
        f"If no contribution guidelines are typically found for a project, 'contribution_guidelines_summary_ai' would not be applicable. (You don't know this yet, but keep it in mind for general reasoning). "
        f"Prioritize helpfulness for a beginner. Respond ONLY with a JSON object in the format: "
        f"{{\"include_components\": [\"component_name_1\", \"component_name_2\", ...]}}"
    )

    print(f"LLM Handler (plan_kit): Sending request to plan kit components. Model: {model_name}")
    try:
        # Forcing JSON response mode if available and model supports it well
        # gpt-4o-mini and newer gpt-3.5-turbo models usually handle "Respond ONLY with a valid JSON" well.
        # For stronger enforcement, you can use response_format={"type": "json_object"} with compatible models.
        completion_params = {
            "model": model_name,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            "temperature": 0.2, # Low temperature for more deterministic structural output
            "max_tokens": 200, # JSON output should be relatively small
            "top_p": 1.0,
        }
        # Check if the model might be one that supports explicit JSON mode via response_format
        if "gpt-4o" in model_name or "gpt-3.5-turbo-0125" in model_name or "gpt-3.5-turbo-1106" in model_name: # Add other compatible models if known
             completion_params["response_format"] = {"type": "json_object"}


        completion = client.chat.completions.create(**completion_params)
        
        raw_response_content = completion.choices[0].message.content
        print(f"LLM Handler (plan_kit): Raw JSON response received: {raw_response_content}")

        # Attempt to parse the JSON
        parsed_plan = json.loads(raw_response_content)
        if "include_components" in parsed_plan and isinstance(parsed_plan["include_components"], list):
            # Further validation: ensure all component names are valid (optional but good)
            valid_components = [comp for comp in parsed_plan["include_components"] if comp in available_components]
            if len(valid_components) != len(parsed_plan["include_components"]):
                print("Warning (llm_handler.plan_kit): LLM returned some invalid component names.")
            
            final_plan = {"include_components": valid_components}
            print(f"LLM Handler (plan_kit): Parsed plan: {final_plan}")
            return final_plan
        else:
            print("ERROR (llm_handler.plan_kit): LLM response was not in the expected JSON format (missing 'include_components' list).")
            return {"error": "LLM response format error", "details": "Missing 'include_components' list."}

    except json.JSONDecodeError as json_e:
        print(f"ERROR (llm_handler.plan_kit): Failed to decode JSON from LLM response. Error: {json_e}. Response was: {raw_response_content}")
        return {"error": "JSON decode error", "details": str(json_e), "raw_response": raw_response_content}
    except Exception as e:
        print(f"ERROR (llm_handler.plan_kit): LLM API call failed: {e}")
        return {"error": f"LLM API call failed: {str(e)}"}