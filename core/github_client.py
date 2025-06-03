import requests
import os # Good to have for potential future path manipulations, though not used yet.
from urllib.parse import quote # For safely encoding query parameters

# Import the GITHUB_PAT from our config loader
# The '..' means go up one directory level from core to the project root, then into utils
from utils.config_loader import GITHUB_PAT

BASE_SEARCH_URL = "https://api.github.com/search/issues"
BASE_REPO_URL = "https://api.github.com/repos" # For fetching repo details later

def _make_github_request(url: str, params: dict = None, headers: dict = None) -> dict | None:
    """
    Helper function to make authenticated GitHub API GET requests.
    Handles potential request errors.
    """
    if not GITHUB_PAT:
        print("ERROR: GITHUB_PAT is not configured. Cannot make GitHub API requests.")
        return None

    default_headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json", # Standard for GitHub API v3
        "X-GitHub-Api-Version": "2022-11-28" # Recommended by GitHub
    }
    if headers:
        default_headers.update(headers)

    try:
        response = requests.get(url, headers=default_headers, params=params, timeout=10) # 10 second timeout
        response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
        return response.json()
    except requests.exceptions.Timeout:
        print(f"GitHub API request timed out for URL: {url}")
        return None
    except requests.exceptions.HTTPError as http_err:
        print(f"GitHub API HTTP error for URL {url}: {http_err} - Response: {response.text}")
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"GitHub API request failed for URL {url}: {req_err}")
        return None
    except ValueError as json_err: # Includes JSONDecodeError
        print(f"Failed to decode JSON response from URL {url}: {json_err}")
        return None

def fetch_beginner_issues(
        language: str,
        labels: list[str] = None,
        sort: str = "updated",
        order: str = "desc",
        per_page: int = 10,
        page: int = 1
    ) -> list[dict] | None:

    # Let's use a more focused default list of labels.
    # "good first issue" is standard. "help wanted" is also common.
    # Too many might be too restrictive.
    if labels is None:
        labels = ["good first issue", "help wanted"] # More focused default
        # Or even just: labels = ["good first issue"] to start broadly

    query_parts = [
        f"language:{language}",
        "state:open",
        "is:issue",
        "is:public"
    ]

    # Add each label to the query.
    # The format label:"label name" is correct for labels with spaces.
    for label_name in labels:
        query_parts.append(f'label:"{label_name}"') # Ensure quotes around each label_name

    q_string = " ".join(query_parts)

    params = {
        "q": q_string,
        "sort": sort,
        "order": order,
        "per_page": per_page,
        "page": page
    }

    print(f"Fetching issues with q_string: '{q_string}', params dict: {params}") # Debug print
    data = _make_github_request(BASE_SEARCH_URL, params=params)

    # ... (rest of the parsing logic remains the same, it's working!) ...
    if data and "items" in data:
        issues_list = []
        for item in data["items"]:
            repo_html_url = "/".join(item.get("html_url", "").split('/')[:5])
            issues_list.append({
                "title": item.get("title"),
                "html_url": item.get("html_url"),
                "state": item.get("state"),
                "number": item.get("number"),
                "created_at": item.get("created_at"),
                "updated_at": item.get("updated_at"),
                "labels": [label_item.get("name") for label_item in item.get("labels", [])],
                "repository_api_url": item.get("repository_url"),
                "repository_html_url": repo_html_url,
                "user_login": item.get("user", {}).get("login"),
                "body_snippet": item.get("body", "")[:300] + "..." if item.get("body") else "No body provided."
            })
        # This check was from the temporary test, can be removed or kept for sanity
        # if not issues_list and data.get("total_count", 0) > 0 :
        #      print(f"Warning: 'items' array was empty, but total_count is {data.get('total_count')}.")
        # elif not issues_list:
        #      print("Info: 'items' array is empty and total_count is 0 or not present.")
        return issues_list
    elif data and "items" not in data: # This case means the API call was OK but data was unexpected
        print(f"No 'items' in response for query '{q_string}'. Full response: {data}")
        return [] # Return empty list as it's a valid API response but no items
    # If _make_github_request returned None (due to HTTPError, Timeout, etc.)
    return None # Indicates an error in the request itself

# --- Functions for LATER DAYS (stubs for now) ---

def get_repository_details(repo_api_url: str) -> dict | None:
    """
    Fetches details for a specific repository using its API URL.
    Primarily used to get the default_branch.
    Example repo_api_url: "https://api.github.com/repos/owner/repo"
    """
    if not repo_api_url:
        print("Error: No repository API URL provided to get_repository_details.")
        return None

    print(f"Fetching repository details from: {repo_api_url}")
    data = _make_github_request(repo_api_url) # This URL is already the full API endpoint
    if data:
        # We only need a subset of details, but returning the whole data is fine for now
        # Key field we often need: data.get("default_branch")
        return data
    return None

def get_file_url_from_repo(repo_full_name: str, file_paths_to_check: list[str], default_branch: str | None = None) -> str | None:
    """
    Checks for the existence of a file in a list of possible paths within a repository
    and returns its HTML URL if found.
    Args:
        repo_full_name: The repository name in "owner/repo" format.
        file_paths_to_check: A list of possible paths for the file (e.g., ["CONTRIBUTING.md", ".github/CONTRIBUTING.md"]).
        default_branch: The default branch of the repository. If None, attempts to fetch it.
    Returns:
        The HTML URL of the file if found, otherwise None.
    """
    if not repo_full_name:
        print("Error: No repository full name provided to get_file_url_from_repo.")
        return None

    if not default_branch:
        print(f"No default branch provided for {repo_full_name}, attempting to fetch it.")
        repo_api_url = f"{BASE_REPO_URL}/{repo_full_name}"
        repo_details = get_repository_details(repo_api_url)
        if repo_details and repo_details.get("default_branch"):
            default_branch = repo_details.get("default_branch")
            print(f"Fetched default branch for {repo_full_name}: {default_branch}")
        else:
            print(f"Could not determine default branch for {repo_full_name}. Cannot check for file.")
            # Fallback or try common branches if API fails for default_branch
            # For MVP, if default_branch isn't found, we might not find the file.
            # Or, we could try common names like 'main' or 'master' but this is less reliable.
            # Let's assume for now that if we can't get default_branch, we can't reliably get the file URL.
            # A more robust solution might try a few common branches if default_branch is unknown.
            print(f"Attempting with common branches 'main', then 'master' as fallback for {repo_full_name} if default_branch unknown.")
            branches_to_try = [default_branch] if default_branch else ["main", "master"]

    else: # default_branch was provided
        branches_to_try = [default_branch]

    for branch_to_try in branches_to_try:
        if not branch_to_try: continue # Skip if branch is None in the list

        for file_path in file_paths_to_check:
            # Construct the API URL to get metadata about the file (not its content directly yet)
            # This tells us if the file exists.
            file_api_url = f"{BASE_REPO_URL}/{repo_full_name}/contents/{file_path}?ref={branch_to_try}"
            print(f"Checking for file at API URL: {file_api_url}")

            # _make_github_request will return None if it's a 404 (file not found) or other error
            file_metadata = _make_github_request(file_api_url)

            if file_metadata and isinstance(file_metadata, dict) and file_metadata.get("html_url"):
                print(f"Found {file_path} in {repo_full_name} on branch {branch_to_try} at {file_metadata.get('html_url')}")
                return file_metadata.get("html_url") # Return the HTML URL of the file
            else:
                print(f"File {file_path} not found or error fetching metadata on branch {branch_to_try} for {repo_full_name}.")
        if default_branch : # If default branch was known and tried, don't try others.
            break

    print(f"Could not find any of the specified files {file_paths_to_check} in {repo_full_name} on attempted branches.")
    return None