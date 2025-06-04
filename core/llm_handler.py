import openai # Using the openai library for Nebius's OpenAI-compatible API
import os     # For environment variables if not using config_loader directly here

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