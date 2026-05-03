"""Clone GitHub or local repositories."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from git import Repo

from askmyrepo.config import Settings, get_settings


class RepoCloner:
    """Handles cloning GitHub repos and validating local paths."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.base_dir = Path(self.settings.default_repo_path)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def clone_or_use(self, source: str) -> Path:
        """Clone a GitHub repo or validate a local path.

        Args:
            source: GitHub URL or local filesystem path.

        Returns:
            Path to the repository root.
        """
        if self._is_github_url(source):
            return self._clone_github(source)
        return self._validate_local(source)

    def _is_github_url(self, source: str) -> bool:
        try:
            parsed = urlparse(source)
            return bool(parsed.netloc and "github.com" in parsed.netloc)
        except Exception:
            return False

    def _clone_github(self, url: str) -> Path:
        repo_name = urlparse(url).path.strip("/").split("/")[-1].rstrip(".git")
        dest = self.base_dir / repo_name

        git_dir = dest / ".git"
        if dest.exists() and git_dir.exists():
            print(f"Repo '{repo_name}' already cloned, fetching latest...")
            repo = Repo(dest)
            repo.remotes.origin.set_url(url)
            repo.remotes.origin.fetch()
            return dest

        print(f"Cloning {url} ...")
        Repo.clone_from(url, dest, depth=1)
        return dest

    def _validate_local(self, path_str: str) -> Path:
        path = Path(path_str).resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"Local path does not exist: {path}")
        if not (path / ".git").exists():
            raise NotADirectoryError(f"Path is not a git repo (no .git): {path}")
        return path

    def list_repos(self) -> list[Path]:
        """List all cloned repos in the base directory."""
        return [d for d in self.base_dir.iterdir() if d.is_dir() and (d / ".git").exists()]
