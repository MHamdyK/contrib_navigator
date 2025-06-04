import requests
import os # Good practice
# from urllib.parse import quote # We are letting requests handle most param encoding

# Import the GITHUB_PAT from our config loader
from utils.config_loader import GITHUB_PAT # Make sure this path is correct for your setup

BASE_SEARCH_URL = "https://api.github.com/search/issues"
BASE_REPO_URL = "https://api.github.com/repos"

def _make_github_request(url: str, params: dict = None, headers: dict = None) -> dict | None:
    """
    Helper function to make authenticated GitHub API GET requests expecting JSON response.
    Handles potential request errors.
    """
    if not GITHUB_PAT:
        print("ERROR (github_client._make_github_request): GITHUB_PAT is not configured.")
        return None

    default_headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if headers:
        default_headers.update(headers)

    try:
        # print(f"Debug GitHub Request: URL={url}, Params={params}, Headers={default_headers}") # Uncomment for deep debugging
        response = requests.get(url, headers=default_headers, params=params, timeout=15) # Increased timeout slightly
        response.raise_for_status()
        return response.json() # Expecting JSON
    except requests.exceptions.Timeout:
        print(f"ERROR (github_client._make_github_request): GitHub API request timed out for URL: {url}")
        return None
    except requests.exceptions.HTTPError as http_err:
        # Log specific error details, especially for common issues like 401, 403, 404, 422
        error_message = f"ERROR (github_client._make_github_request): GitHub API HTTP error for URL {url}: {http_err}."
        try:
            # Attempt to get more detailed error message from GitHub's JSON response
            error_details = http_err.response.json()
            error_message += f" Details: {error_details.get('message', 'No specific message')} Docs: {error_details.get('documentation_url', 'N/A')}"
        except ValueError: # If response is not JSON
            error_message += f" Response: {http_err.response.text}"
        print(error_message)
        return None # For HTTP errors, generally return None
    except requests.exceptions.RequestException as req_err:
        print(f"ERROR (github_client._make_github_request): GitHub API request failed for URL {url}: {req_err}")
        return None
    except ValueError as json_err: # Includes JSONDecodeError if response.json() fails
        print(f"ERROR (github_client._make_github_request): Failed to decode JSON response from URL {url}: {json_err}")
        return None

def fetch_beginner_issues(
        language: str,
        topics: list[str] | None = None, # ADDED topics parameter
        labels: list[str] | None = None,
        sort: str = "updated",
        order: str = "desc",
        per_page: int = 10,
        page: int = 1
    ) -> list[dict] | None:
    """
    Fetches beginner-friendly issues for a given language and optional topics
    from GitHub's public repositories.
    """
    if not language: # Basic validation
        print("ERROR (github_client.fetch_beginner_issues): Language parameter is required.")
        return None

    if labels is None:
        labels = ["good first issue", "help wanted"]

    query_parts = [
        f"language:{language.strip().lower()}", # Normalize language
        "state:open",
        "is:issue",
        "is:public"
    ]

    for label_name in labels:
        if label_name.strip(): # Ensure label is not just whitespace
            query_parts.append(f'label:"{label_name.strip()}"')

    # --- ADDED TOPICS TO QUERY ---
    if topics:
        for topic_name_raw in topics:
            topic_name = topic_name_raw.strip().lower()
            if topic_name: # Ensure topic is not just whitespace
                # GitHub topics with spaces are typically hyphenated (e.g., "web-development")
                # or can be searched with quotes if they are actual multi-word tags.
                # We'll assume topics are passed as GitHub expects them (e.g., "machine-learning" or "web development")
                if " " in topic_name:
                    query_parts.append(f'topic:"{topic_name}"')
                else:
                    query_parts.append(f'topic:{topic_name}')
    # --- END ADDED TOPICS ---

    q_string = " ".join(query_parts)
    params = {"q": q_string, "sort": sort, "order": order, "per_page": per_page, "page": page}

    print(f"GitHub Client: Fetching issues with q_string: '{q_string}'") # Removed params from this print for brevity
    data = _make_github_request(BASE_SEARCH_URL, params=params)

    if data and "items" in data:
        issues_list = []
        for item in data["items"]:
            repo_html_url = "/".join(item.get("html_url", "").split('/')[:5])
            issues_list.append({
                "title": item.get("title"), "html_url": item.get("html_url"),
                "state": item.get("state"), "number": item.get("number"),
                "created_at": item.get("created_at"), "updated_at": item.get("updated_at"),
                "labels": [label_item.get("name") for label_item in item.get("labels", [])],
                "repository_api_url": item.get("repository_url"),
                "repository_html_url": repo_html_url,
                "user_login": item.get("user", {}).get("login"),
                "body_snippet": item.get("body", "")[:300] + "..." if item.get("body") else "No body provided."
            })
        return issues_list
    elif data and "items" not in data:
        print(f"GitHub Client: No 'items' in API response for query '{q_string}'. API Message: {data.get('message', 'N/A')}")
        return [] # Valid response from API, but no matching items
    # If data is None, _make_github_request already printed an error
    return None


def get_repository_details(repo_api_url: str) -> dict | None:
    """
    Fetches details for a specific repository using its API URL.
    Primarily used to get the default_branch.
    """
    if not repo_api_url:
        print("ERROR (github_client.get_repository_details): No repository API URL provided.")
        return None
    print(f"GitHub Client: Fetching repository details from: {repo_api_url}")
    return _make_github_request(repo_api_url)


def get_file_url_from_repo(repo_full_name: str, file_paths_to_check: list[str], default_branch: str | None = None) -> str | None:
    """
    Checks for the existence of a file in a list of possible paths within a repository
    and returns its HTML URL if found.
    """
    if not repo_full_name or not file_paths_to_check:
        print("ERROR (github_client.get_file_url_from_repo): repo_full_name and file_paths_to_check are required.")
        return None

    branch_to_use = default_branch
    if not branch_to_use:
        print(f"GitHub Client (get_file_url): No default branch provided for {repo_full_name}, attempting to fetch it.")
        repo_api_url_for_details = f"{BASE_REPO_URL}/{repo_full_name}"
        repo_details = get_repository_details(repo_api_url_for_details)
        if repo_details and repo_details.get("default_branch"):
            branch_to_use = repo_details.get("default_branch")
            print(f"GitHub Client (get_file_url): Fetched default branch '{branch_to_use}' for {repo_full_name}.")
        else:
            print(f"GitHub Client (get_file_url): Could not determine default branch for {repo_full_name}. Will try common fallbacks.")
            # If default branch still not found, function will iterate through fallbacks next.

    # Define branches to try: the determined/passed one, then common fallbacks if needed.
    branches_to_attempt = []
    if branch_to_use:
        branches_to_attempt.append(branch_to_use)
    # Add fallbacks if the initial branch_to_use was None OR if we want to always check fallbacks (but usually not)
    if not branch_to_use: # Only add fallbacks if we couldn't determine one
        branches_to_attempt.extend(["main", "master"])


    for current_branch_attempt in branches_to_attempt:
        print(f"GitHub Client (get_file_url): Trying branch '{current_branch_attempt}' for {repo_full_name}.")
        for file_path in file_paths_to_check:
            file_api_url = f"{BASE_REPO_URL}/{repo_full_name}/contents/{file_path}?ref={current_branch_attempt}"
            # print(f"GitHub Client (get_file_url): Checking for file at API URL: {file_api_url}") # Can be verbose
            file_metadata = _make_github_request(file_api_url) # This expects JSON
            if file_metadata and isinstance(file_metadata, dict) and file_metadata.get("html_url"):
                print(f"GitHub Client (get_file_url): Found '{file_path}' in {repo_full_name} on branch '{current_branch_attempt}'.")
                return file_metadata.get("html_url")
            # else: # No need to print "not found" for every path/branch combination, becomes too noisy.
                 # _make_github_request will print if it's a 404 or other HTTP error.
    
    print(f"GitHub Client (get_file_url): Could not find any of {file_paths_to_check} in {repo_full_name} on attempted branches.")
    return None

# --- NEW FUNCTION ---
def get_file_content(repo_full_name: str, file_path: str, branch: str | None = None) -> str | None:
    """
    Fetches the raw text content of a specific file from a repository.
    Args:
        repo_full_name: The repository name in "owner/repo" format.
        file_path: The path to the file within the repository (e.g., "CONTRIBUTING.md").
        branch: The branch to fetch from. If None, attempts to find default branch.
    Returns:
        The text content of the file, or None if not found or an error occurs.
    """
    if not repo_full_name or not file_path:
        print("ERROR (github_client.get_file_content): repo_full_name and file_path are required.")
        return None

    current_branch = branch
    if not current_branch:
        print(f"GitHub Client (get_file_content): No branch specified for {repo_full_name}/{file_path}, finding default.")
        repo_api_url_for_details = f"{BASE_REPO_URL}/{repo_full_name}"
        repo_details = get_repository_details(repo_api_url_for_details)
        if repo_details and repo_details.get("default_branch"):
            current_branch = repo_details.get("default_branch")
            print(f"GitHub Client (get_file_content): Using default branch '{current_branch}' for {repo_full_name}/{file_path}")
        else:
            # Try common fallbacks if default cannot be determined
            print(f"GitHub Client (get_file_content): Could not determine default branch for {repo_full_name}. Trying 'main', then 'master' for {file_path}.")
            # Attempt 'main' first for get_file_content call
            current_branch = "main" 
            # If 'main' fails, we could try 'master' subsequently, but let's try one at a time.
            # The request below will try current_branch. If it fails with 404, we could then retry with 'master'.
            # For now, let's simplify: try determined default, else 'main'. If that 404s, the user gets None.

    file_api_url = f"{BASE_REPO_URL}/{repo_full_name}/contents/{file_path}?ref={current_branch}"
    print(f"GitHub Client (get_file_content): Fetching raw content for '{file_path}' from '{repo_full_name}' on branch '{current_branch}'.")

    if not GITHUB_PAT:
        print("ERROR (github_client.get_file_content): GITHUB_PAT is not configured.")
        return None
    
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.raw", # Key header for raw content
        "X-GitHub-Api-Version": "2022-11-28"
    }

    try:
        response = requests.get(file_api_url, headers=headers, timeout=15) # Increased timeout
        response.raise_for_status()
        return response.text # Return raw text content
    except requests.exceptions.Timeout:
        print(f"ERROR (github_client.get_file_content): GitHub API request timed out for URL: {file_api_url}")
        return None
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            print(f"INFO (github_client.get_file_content): File not found (404) at {file_api_url}")
            # If default branch was 'main' and failed, we could try 'master' here as a fallback
            if current_branch == "main" and (not branch or branch == "main"): # Check if we already tried specific branch or if 'main' was a fallback
                print(f"GitHub Client (get_file_content): '{file_path}' not found on 'main', trying 'master' as fallback.")
                return get_file_content(repo_full_name, file_path, branch="master") # Recursive call with 'master'
        else:
            error_message = f"ERROR (github_client.get_file_content): GitHub API HTTP error for URL {file_api_url}: {http_err}."
            try:
                error_details = http_err.response.json() # Some errors might still be JSON
                error_message += f" Details: {error_details.get('message', http_err.response.text)}"
            except ValueError:
                error_message += f" Response: {http_err.response.text}"
            print(error_message)
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"ERROR (github_client.get_file_content): GitHub API request failed for URL {file_api_url}: {req_err}")
        return None