"""
GitHub API tool.

Wraps PyGithub calls to push a README file to a dedicated branch and open
(or reuse) a pull request. All GitHub I/O is isolated here so nodes remain
free of API client details.
"""
from __future__ import annotations

import logging

from github import Github, GithubException

from ..prompts import COMMIT_MSG, PR_BODY, PR_BRANCH, PR_TITLE

logger = logging.getLogger(__name__)


def push_readme_and_open_pr(
    owner: str,
    repo_name: str,
    base_branch: str,
    readme_content: str,
    token: str,
) -> str:
    """
    Push *readme_content* to ``README.md`` on the ``docs/auto-generated-readme``
    branch and open (or reuse) a pull request against *base_branch*.

    Args:
        owner:          GitHub owner (user or organisation).
        repo_name:      Repository name.
        base_branch:    Branch the PR targets (e.g. ``"main"``).
        readme_content: Full markdown text of the generated README.
        token:          GitHub personal access token with ``repo`` scope.

    Returns:
        HTML URL of the opened (or existing) pull request.

    Raises:
        GithubException: If any GitHub API call fails.
    """
    gh = Github(token)
    gh_repo = gh.get_repo(f"{owner}/{repo_name}")

    # Anchor the docs branch to the current tip of base_branch
    base_sha = gh_repo.get_branch(base_branch).commit.sha

    # Create or reset the docs branch
    try:
        existing_ref = gh_repo.get_git_ref(f"heads/{PR_BRANCH}")
        logger.info("Branch %s exists — updating to %s.", PR_BRANCH, base_sha)
        existing_ref.edit(sha=base_sha, force=True)
    except GithubException:
        logger.info("Creating branch %s from %s.", PR_BRANCH, base_sha)
        gh_repo.create_git_ref(ref=f"refs/heads/{PR_BRANCH}", sha=base_sha)

    # Create or update README.md on the docs branch
    readme_path = "README.md"
    try:
        existing_file = gh_repo.get_contents(readme_path, ref=PR_BRANCH)
        gh_repo.update_file(
            path=readme_path,
            message=COMMIT_MSG,
            content=readme_content,
            sha=existing_file.sha,
            branch=PR_BRANCH,
        )
        logger.info("Updated README.md on branch %s.", PR_BRANCH)
    except GithubException:
        gh_repo.create_file(
            path=readme_path,
            message=COMMIT_MSG,
            content=readme_content,
            branch=PR_BRANCH,
        )
        logger.info("Created README.md on branch %s.", PR_BRANCH)

    # Open or reuse the pull request
    open_prs = gh_repo.get_pulls(
        state="open",
        head=f"{owner}:{PR_BRANCH}",
        base=base_branch,
    )
    existing_pr = next(iter(open_prs), None)

    if existing_pr:
        pr_url = existing_pr.html_url
        logger.info("PR already exists: %s", pr_url)
    else:
        pr = gh_repo.create_pull(
            title=PR_TITLE,
            body=PR_BODY,
            head=PR_BRANCH,
            base=base_branch,
        )
        pr_url = pr.html_url
        logger.info("Pull request created: %s", pr_url)

    return pr_url
