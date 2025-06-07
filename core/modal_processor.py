from modal_definitions import stub as an_individual_modal_app_instance_name
from modal_definitions import clone_and_list_files_on_modal


def get_repo_file_listing_via_modal(repo_url: str) -> dict | None:
    if not repo_url:
        print("Error (modal_processor): No repository URL provided.")
        return {"status": "error", "message": "No repository URL provided."}

    print(f"Modal Processor: Attempting to get file listing for {repo_url} via Modal...")
    try:
        with an_individual_modal_app_instance_name.run():
            result_dict = clone_and_list_files_on_modal.remote(repo_url)
        print(f"Modal Processor: Result received from Modal for {repo_url}: {result_dict}")
        return result_dict
    except Exception as e:
        print(f"Error (modal_processor): Failed to invoke or communicate with Modal function for {repo_url}. Exception: {e}")
        return {"status": "error", "message": f"Failed to invoke Modal function: {str(e)}"}


if __name__ == '__main__':


    print("Running modal_processor.py directly for testing...")
    test_url_gradio = "https://github.com/gradio-app/gradio.git"

    print(f"\nTesting with URL: {test_url_gradio}")
    response = get_repo_file_listing_via_modal(test_url_gradio)
    if response and response.get("status") == "success":
        print(f"Success! Files for {test_url_gradio}: {response.get('files')[:5]}...") # Print first 5 files
    else:
        print(f"Failed or got unexpected response for {test_url_gradio}: {response}")
