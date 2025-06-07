# Contributing to ContribNavigator

Thank you for your interest in contributing to ContribNavigator! We welcome improvements and ideas from the community.

## Getting Started

1.  **Fork the Repository:** Start by forking the [ContribNavigator repository](https://github.com/MHamdyK/contrib_navigator.git)
2.  **Clone Your Fork:**
    ```bash
    git clone https://github.com/MHamdyK/contrib_navigator.git
    cd contrib_navigator
    ```
3.  **Set Up a Virtual Environment (Recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```
4.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
5.  **Set Up Environment Variables:**
    *   Create a `.env` file in the project root.
    *   You will need to add your own `GITHUB_PAT` and `OPENAI_API_KEY`. See the main `README.md` for details on these keys.
    *   If you plan to test or modify Modal functions locally, ensure your Modal CLI is authenticated (`modal token new`).

6.  **Create a New Branch:** For any new feature or bug fix, please create a new branch:
    ```bash
    git checkout -b my-awesome-feature
    ```

## Making Changes

*   Ensure your code follows the general style of the existing codebase.
*   If you add new dependencies, please update `requirements.txt`.
*   Test your changes locally by running `python app.py`.

## Submitting Contributions

1.  **Commit Your Changes:** Write clear and concise commit messages.
    ```bash
    git add .
    git commit -m "feat: Briefly describe your feature or fix"
    ```
2.  **Push to Your Fork:**
    ```bash
    git push origin my-awesome-feature
    ```
3.  **Open a Pull Request:**
    *   Go to the original [ContribNavigator repository](https://github.com/MHamdyK/contrib_navigator.git) on GitHub. 
    *   Click on the "Pull requests" tab and then "New pull request."
    *   Choose your fork and the branch containing your changes.
    *   Provide a clear title and description for your pull request, explaining the changes you've made and why. Reference any related issues.


## Questions or Suggestions?

Feel free to open an issue on the GitHub repository if you have questions, find a bug, or want to suggest an enhancement.

We appreciate your help in making ContribNavigator even better!