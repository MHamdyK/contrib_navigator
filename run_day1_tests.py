from core.github_client import fetch_beginner_issues
from core.llm_handler import get_simple_issue_suggestion
import utils.config_loader # This loads .env and makes variables available

def main_test_runner():
    print("--- ContribNavigator Day 1 Test Runner ---")

    # Check for GitHub PAT
    if not utils.config_loader.GITHUB_PAT:
        print("CRITICAL: GITHUB_PAT not loaded. Please check your .env file.")
        return # Stop if GitHub PAT is missing, as it's essential for the first step

    # Check for OpenAI API Key
    if not utils.config_loader.OPENAI_API_KEY: # CHANGED from Nebius check
        print("CRITICAL: OPENAI_API_KEY not loaded. LLM calls will fail. Please check your .env file.")
        # We might still want to see GitHub issues, so we don't return immediately,
        # but the LLM part will be skipped or will show an error from llm_handler.
    else:
        print("OpenAI API Key found. Ready for LLM tests.")


    print("\n--- Testing GitHub Issue Fetching ---")
    target_language = "python"
    print(f"Attempting to fetch up to 5 '{target_language}' issues with default labels...")
    # Using default labels from fetch_beginner_issues: ["good first issue", "help wanted"]
    issues = fetch_beginner_issues(target_language, per_page=5)

    if issues is None:
        print("Failed to fetch issues from GitHub. There might have been an API request error. Check console for details from github_client.")
    elif not issues:
        print(f"No issues found for '{target_language}' with the default labels. Cannot proceed to LLM test.")
    else:
        print(f"\nSuccessfully fetched {len(issues)} issues for '{target_language}':")
        for i, issue_item in enumerate(issues):
            print(f"  {i+1}. Title: {issue_item.get('title')}")
            print(f"      URL: {issue_item.get('html_url')}")
            print(f"      Repo: {issue_item.get('repository_html_url')}")
            print(f"      Labels: {issue_item.get('labels')}")
            print("-" * 20)

        # --- NOW TESTING LLM Handler with OpenAI ---
        print("\n--- Testing LLM Suggestion (OpenAI) ---")
        if not utils.config_loader.OPENAI_API_KEY: # CHANGED from Nebius check
            print("OPENAI_API_KEY not configured in .env. Skipping LLM test.")
        else:
            # Let's send the first 2 or 3 issues to the LLM for suggestion
            issues_for_llm = issues[:3] # Send up to the first 3 issues
            if issues_for_llm:
                print(f"\nSending {len(issues_for_llm)} issue(s) to OpenAI LLM for suggestion (expecting 1 suggestion)...")
                # Get 1 suggestion for these issues
                suggestion = get_simple_issue_suggestion(issues_for_llm, target_language, target_count=1) # Uses default model "gpt-3.5-turbo"

                print("\nLLM Suggestion Output:")
                if suggestion:
                    print(suggestion)
                else:
                    # llm_handler should print specific errors if any occurred during the API call
                    print("LLM did not return a suggestion or an error occurred (see logs above from llm_handler).")
            else:
                # This case should not happen if 'issues' list was populated
                print("No issues were available to send to LLM for suggestion.")

    print("\n--- Day 1 Full Test Complete ---")

if __name__ == "__main__":
    main_test_runner()