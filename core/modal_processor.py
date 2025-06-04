# core/modal_processor.py

# CHANGE THIS IMPORT:
# from ..modal_definitions import stub as an_individual_modal_app_instance_name
# from ..modal_definitions import clone_and_list_files_on_modal
# TO THIS (assuming modal_definitions.py is in the project root):
from modal_definitions import stub as an_individual_modal_app_instance_name
from modal_definitions import clone_and_list_files_on_modal

# (get_repo_file_listing_via_modal function definition remains the same)
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
    # This block is for when you run `python core/modal_processor.py` OR `python -m core.modal_processor`
    # FROM THE PROJECT ROOT (contrib_navigator/)
    # The imports at the top of the file (`from modal_definitions import ...`) should now work
    # because Python adds the directory of the script being run (or -m target) to sys.path.
    # If running `python -m core.modal_processor` from `contrib_navigator/`, then `contrib_navigator/` is in sys.path.

    print("Running modal_processor.py directly for testing...")
    test_url_gradio = "https://github.com/gradio-app/gradio.git"

    print(f"\nTesting with URL: {test_url_gradio}")
    response = get_repo_file_listing_via_modal(test_url_gradio)
    if response and response.get("status") == "success":
        print(f"Success! Files for {test_url_gradio}: {response.get('files')[:5]}...") # Print first 5 files
    else:
        print(f"Failed or got unexpected response for {test_url_gradio}: {response}")

    # You can add back other test cases here if desired, for example:
    # test_url_problematic = "https://github.com/git-guides/install-git.git"
    # print(f"\nTesting with problematic URL: {test_url_problematic}")
    # response_problem = get_repo_file_listing_via_modal(test_url_problematic)
    # if response_problem and response_problem.get("status") == "error":
    #     print(f"Correctly received error for {test_url_problematic}: {response_problem.get('message')}")
    # else:
    #     print(f"Unexpected response for {test_url_problematic}: {response_problem}")