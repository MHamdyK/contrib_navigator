# modal_definitions.py
import modal
import subprocess
import tempfile
import os

# (stub and git_image definitions remain the same)
stub = modal.App(name="contrib-navigator-repo-inspector")
git_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("git")
)

# (clone_and_list_files_on_modal function remains the same)
@stub.function(
    image=git_image,
    timeout=120,
    retries=modal.Retries(max_retries=1, initial_delay=2.0, backoff_coefficient=1.0)
)
def clone_and_list_files_on_modal(repo_url: str) -> dict:
    # ... (function body is correct as you have it) ...
    print(f"Modal function received URL to clone: {repo_url}")
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_subdir_name = "cloned_repo"
        clone_target_path = os.path.join(tmpdir, repo_subdir_name)
        try:
            command = ["git", "clone", "--depth", "1", repo_url, clone_target_path]
            print(f"Executing command in Modal: {' '.join(command)}")
            result = subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=90
            )
            cloned_files = os.listdir(clone_target_path)
            print(f"Successfully cloned and listed files for {repo_url}. Files: {cloned_files}")
            return {"status": "success", "files": cloned_files, "cloned_path_on_modal": clone_target_path}
        except subprocess.TimeoutExpired:
            error_message = f"Git clone command timed out in Modal for {repo_url}."
            print(error_message)
            return {"status": "error", "message": error_message}
        except subprocess.CalledProcessError as e:
            error_message = (
                f"Failed to clone {repo_url} in Modal. "
                f"Git command return code: {e.returncode}. "
                f"Stderr: {e.stderr.strip() if e.stderr else 'N/A'}. "
                f"Stdout: {e.stdout.strip() if e.stdout else 'N/A'}."
            )
            print(error_message)
            return {"status": "error", "message": error_message}
        except FileNotFoundError:
            error_message = "Git command not found in Modal environment. Image build issue."
            print(error_message)
            return {"status": "error", "message": error_message}
        except Exception as e:
            error_message = f"An unexpected error occurred in Modal function for {repo_url}: {str(e)}"
            print(error_message)
            return {"status": "error", "message": error_message}


# --- Optional: Local testing entrypoint for this Modal function ---
@stub.local_entrypoint()
async def test_clone_function_on_modal():

    test_repo_url_successful = "https://github.com/gradio-app/gradio.git"
    print(f"\n[Local Test] Calling Modal function for successful clone: {test_repo_url_successful}")
    result_successful = await clone_and_list_files_on_modal.remote.aio(test_repo_url_successful)
    print(f"[Local Test] Result from Modal for successful clone: {result_successful}\n")
