import requests
import os

from utils.config_loader import GITHUB_PAT

BASE_SEARCH_URL = "https://api.github.com/search/issues"
BASE_REPO_URL = "https://api.github.com/repos"

def _make_github_request(url: str, params: dict = None, headers: dict = None) -> dict | None:

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
        response = requests.get(url, headers=default_headers, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print(f"ERROR (github_client._make_github_request): GitHub API request timed out for URL: {url}")
        return None
    except requests.exceptions.HTTPError as http_err:
        error_message = f"ERROR (github_client._make_github_request): GitHub API HTTP error for URL {url}: {http_err}."
        try:
            error_details = http_err.response.json()
            error_message += f" Details: {error_details.get('message', 'No specific message')} Docs: {error_details.get('documentation_url', 'N/A')}"
        except ValueError:
            error_message += f" Response: {http_err.response.text}"
        print(error_message)
        return None
    except requests.exceptions.RequestException as req_err:
        print(f"ERROR (github_client._make_github_request): GitHub API request failed for URL {url}: {req_err}")
        return None
    except ValueError as json_err:
        print(f"ERROR (github_client._make_github_request): Failed to decode JSON response from URL {url}: {json_err}")
        return None


def _construct_label_query(labels_list: list[str]) -> str:
    """Constructs a single, comma-separated string for OR logic on labels."""
    if not labels_list:
        return ""
    
    # Quote any labels that contain spaces
    quoted_labels = []
    for label in labels_list:
        clean_label = label.strip()
        if " " in clean_label:
            quoted_labels.append(f'"{clean_label}"')
        else:
            quoted_labels.append(clean_label)
    
    # Return in the format: label:label1,"label two",label3
    return f'label:{",".join(quoted_labels)}'




def fetch_beginner_issues(
        language: str,
        topics: list[str] | None = None,
        labels: list[str] | None = None,
        sort: str = "updated",
        order: str = "desc",
        per_page: int = 10,
        page: int = 1
    ) -> list[dict] | None:
    """
    Fetches beginner-friendly issues. If multiple topics are provided, it
    searches for each topic individually (OR logic). Labels are also combined
    with OR logic.
    """
    if not language:
        print("ERROR (github_client.fetch_beginner_issues): Language parameter is required.")
        return None

    def _parse_issue_item(item: dict) -> dict:
        repo_html_url = "/".join(item.get("html_url", "").split('/')[:5])
        return {
            "title": item.get("title"), "html_url": item.get("html_url"),
            "state": item.get("state"), "number": item.get("number"),
            "created_at": item.get("created_at"), "updated_at": item.get("updated_at"),
            "labels": [label_item.get("name") for label_item in item.get("labels", [])],
            "repository_api_url": item.get("repository_url"),
            "repository_html_url": repo_html_url,
            "user_login": item.get("user", {}).get("login"),
            "body_snippet": item.get("body", "")[:300] + "..." if item.get("body") else "No body provided."
        }

    if topics:
        print(f"GitHub Client: Performing OR search for topics: {topics}")
        all_issues_map = {}
        per_topic_per_page = max(3, per_page // len(topics) if len(topics) > 0 else per_page)
        
        current_labels_to_use = ["good first issue", "help wanted"] if labels is None else labels
        label_query_part = _construct_label_query(current_labels_to_use)
        
        for topic in topics:
            query_parts = [
                f"language:{language.strip().lower()}", "state:open", "is:issue", "is:public"
            ]
            if label_query_part: query_parts.append(label_query_part)
            
            topic_name = topic.strip().lower()
            if " " in topic_name: query_parts.append(f'topic:"{topic_name}"')
            else: query_parts.append(f'topic:{topic_name}')
            
            q_string = " ".join(query_parts)
            params = {"q": q_string, "sort": sort, "order": order, "per_page": int(per_topic_per_page), "page": page}

            print(f"GitHub Client: Fetching for sub-query: '{q_string}'")
            data = _make_github_request(BASE_SEARCH_URL, params=params)

            if data and "items" in data:
                for item in data["items"]:
                    issue_url = item.get("html_url")
                    if issue_url and issue_url not in all_issues_map:
                        all_issues_map[issue_url] = _parse_issue_item(item)
        
        combined_issues = list(all_issues_map.values())
        combined_issues.sort(key=lambda x: x.get('updated_at', ''), reverse=(order == 'desc'))
        
        print(f"GitHub Client: Combined and de-duplicated {len(combined_issues)} issues from topic search.")
        return combined_issues[:per_page]

    else:
        print("GitHub Client: Performing search with no topics specified.")
        default_labels = [
            "good first issue", "help wanted", "beginner", "first-timers-only",
            "contributions welcome", "contribution", "contribute"
        ] if labels is None else labels
        
        label_query_part = _construct_label_query(default_labels)

        query_parts = [
            f"language:{language.strip().lower()}", "state:open", "is:issue", "is:public"
        ]
        if label_query_part: query_parts.append(label_query_part)
        
        q_string = " ".join(query_parts)
        params = {"q": q_string, "sort": sort, "order": order, "per_page": per_page, "page": page}

        print(f"GitHub Client: Fetching with q_string: '{q_string}'")
        data = _make_github_request(BASE_SEARCH_URL, params=params)

        if data and "items" in data:
            return [_parse_issue_item(item) for item in data["items"]]
        elif data and "items" not in data:
            print(f"GitHub Client: No 'items' in API response for query '{q_string}'. API Message: {data.get('message', 'N/A')}")
            return []
        return None



def get_repository_details(repo_api_url: str) -> dict | None:

    if not repo_api_url:
        print("ERROR (github_client.get_repository_details): No repository API URL provided.")
        return None
    print(f"GitHub Client: Fetching repository details from: {repo_api_url}")
    return _make_github_request(repo_api_url)


def get_file_url_from_repo(repo_full_name: str, file_paths_to_check: list[str], default_branch: str | None = None) -> str | None:

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
    branches_to_attempt = []
    if branch_to_use: branches_to_attempt.append(branch_to_use)
    if not branch_to_use: branches_to_attempt.extend(["main", "master"])
    branches_to_attempt = [b for b in branches_to_attempt if b]
    for current_branch_attempt in branches_to_attempt:
        print(f"GitHub Client (get_file_url): Trying branch '{current_branch_attempt}' for {repo_full_name}.")
        for file_path in file_paths_to_check:
            file_api_url = f"{BASE_REPO_URL}/{repo_full_name}/contents/{file_path}?ref={current_branch_attempt}"
            file_metadata = _make_github_request(file_api_url)
            if file_metadata and isinstance(file_metadata, dict) and file_metadata.get("html_url"):
                print(f"GitHub Client (get_file_url): Found '{file_path}' in {repo_full_name} on branch '{current_branch_attempt}'.")
                return file_metadata.get("html_url")
    print(f"GitHub Client (get_file_url): Could not find any of {file_paths_to_check} in {repo_full_name} on attempted branches.")
    return None


def get_file_content(repo_full_name: str, file_path: str, branch: str | None = None) -> str | None:

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
            print(f"GitHub Client (get_file_content): Could not determine default branch for {repo_full_name}. Trying 'main', then 'master' for {file_path}.")
            current_branch = "main"
    file_api_url = f"{BASE_REPO_URL}/{repo_full_name}/contents/{file_path}?ref={current_branch}"
    print(f"GitHub Client (get_file_content): Fetching raw content for '{file_path}' from '{repo_full_name}' on branch '{current_branch}'.")
    if not GITHUB_PAT:
        print("ERROR (github_client.get_file_content): GITHUB_PAT is not configured.")
        return None
    headers = {
        "Authorization": f"token {GITHUB_PAT}",
        "Accept": "application/vnd.github.raw",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    try:
        response = requests.get(file_api_url, headers=headers, timeout=15)
        response.raise_for_status()
        return response.text
    except requests.exceptions.HTTPError as http_err:
        if http_err.response.status_code == 404:
            print(f"INFO (github_client.get_file_content): File not found (404) at {file_api_url}")
            if current_branch == "main" and (not branch or branch == "main"):
                print(f"GitHub Client (get_file_content): '{file_path}' not found on 'main', trying 'master' as fallback.")
                return get_file_content(repo_full_name, file_path, branch="master")
        else:
            error_message = f"ERROR (github_client.get_file_content): GitHub API HTTP error for URL {file_api_url}: {http_err}."
            try:
                error_details = http_err.response.json()
                error_message += f" Details: {error_details.get('message', http_err.response.text)}"
            except ValueError:
                error_message += f" Response: {http_err.response.text}"
            print(error_message)
        return None
    except Exception as e:
        print(f"ERROR (github_client.get_file_content): An unexpected error occurred: {e}")
        return None