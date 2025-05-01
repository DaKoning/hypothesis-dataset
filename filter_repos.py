import json
import re
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from subprocess import run, DEVNULL, TimeoutExpired
from tqdm import tqdm

# === CONFIG ===
CACHE_DIR = Path("repo_cache")
RESULTS_FILE = Path("filtered_repos.json")
MAX_WORKERS = 8 # Number of threads to use for cloning and analyzing repos
TIMEOUT_SECONDS = 300  # 5 minutes


def clone_repo_if_needed(repo_url, local_path):
    # Check if the repo is already cloned
    if local_path.exists():
        return True
    
    # Clone the repo
    try:
        run([
            "git", "clone", "--depth", "1", repo_url, str(local_path) # Use a shallow clone to save time
        ], check=True, stdout=DEVNULL, stderr=DEVNULL, timeout=TIMEOUT_SECONDS) # Use a timeout to avoid hanging indefinitely
        return True
    except (TimeoutExpired, Exception):
        return False

def count_property_tests(code: str) -> int:
    # Look for any decorator ending in .given or @given
    pattern = re.compile(r"@(?:\w+\.)?given\s*\(")
    # Return the number of matches
    return len(pattern.findall(code))

def analyze_repo(repo):
    name = repo["name"]
    repo_url = f"https://github.com/{name}.git"
    repo_dir = CACHE_DIR / name.replace("/", "_")

    try:
        # Clone the repo if needed
        if not clone_repo_if_needed(repo_url, repo_dir):
            return None

        # Count the number of propert-based tests in all files (cumulative)
        count = 0
        for file in repo_dir.rglob("*.py"):
            try:
                code = file.read_text(encoding="utf-8", errors="ignore")
                count += count_property_tests(code)
            except Exception:
                continue

        # Only save repos that have at least 2 property-based tests
        if count >= 2:
            repo_with_count = dict(repo)
            repo_with_count["property_test_count"] = count
            return repo_with_count
    finally:
        # Clean up the cloned repo
        shutil.rmtree(repo_dir, ignore_errors=True)

    return None

def main():
    # Create cache directory if it doesn't exist
    CACHE_DIR.mkdir(exist_ok=True)

    # Get the list of all public repos that depend on Hypothesis from local file
    # This file should be generated with `github-dependents-info --repo HypothesisWorks/hypothesis --sort stars --minstars 100 --json`
    with open("dependents_hypothesis.json") as f:
        all_repos = json.load(f)["all_public_dependent_repos"]

    # Check if the script has run before
    # If so, load the existing results and skip already done repos
    already_done = set()
    existing_results = []
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            existing_results = json.load(f)
            already_done = {r["name"] for r in existing_results}

    # Filter out repos that are already done
    repos_to_check = [repo for repo in all_repos if repo["name"] not in already_done]
    results = existing_results[:]

    # Analyze each repo in parallel
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(analyze_repo, repo): repo for repo in repos_to_check}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Analyzing repos"):
            result = future.result()
            if result:
                results.append(result)
                with open(RESULTS_FILE, "w", encoding="utf-8") as out:
                    json.dump(results, out, indent=2)

    # Sort by stars descending
    results.sort(key=lambda r: r.get("stars", 0), reverse=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as out:
        json.dump({"repos": results}, out, indent=2)

    # Done
    print(f"Done. {len(results)} repositories use Hypothesis with at least 2 property tests.")

# Run the script
if __name__ == "__main__":
    main()
