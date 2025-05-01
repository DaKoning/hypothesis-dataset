import json

INPUT_FILE = "filtered_repos.json"
OUTPUT_FILE = "hypothesis_repos.md"
TITLE = "# Hypothesis-Powered Repositories"

with open(INPUT_FILE, "r") as f:
    repos = json.load(f)["repos"]

# Start Markdown table
lines = [
    "# Hypothesis-Powered Repositories\n",
    "| Repository | ⭐ Stars | 🧪 Property-Based Tests |",
    "|------------|----------|--------------------------|"
]

for repo in repos:
    avatar = f"<img src=\"{repo['img']}\" width=\"20\" height=\"20\"> &nbsp;"
    name = f"[{repo['name']}](https://github.com/{repo['name']})"
    stars = repo.get("stars", 0)
    tests = repo.get("property_test_count", "N/A")
    lines.append(f"| {avatar} {name} | {stars} | {tests} |")

# Write to file
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(TITLE + "\n")
    f.write("\n".join(lines))

print(f"✅ Markdown file saved to {OUTPUT_FILE}")
