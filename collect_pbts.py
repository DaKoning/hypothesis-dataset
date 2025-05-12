import re
import subprocess
import tempfile
from pathlib import Path
from subprocess import run, DEVNULL, PIPE
from tqdm import tqdm
from collections import defaultdict
from multiprocessing import Pool, TimeoutError
from pygments import highlight
from pygments.lexers import PythonLexer
from pygments.formatters import LatexFormatter

CLASS_REGEX = re.compile(r"^\s*class\s+(\w+)\s*\(.*?\):", re.MULTILINE)
DECORATOR_REGEX = re.compile(
    r"((?:^\s*@.*\n)*"                # Match any decorators before @given (including none)
    r"^\s*@(?:\w+\.)?given"           # Match the @given decorator (optionally prefixed)
    r"(?:\s*\(.*?(\n\s*.*?)*?\))?"    # Match optional arguments to @given, possibly multiline
    r"\s*\n(?:^\s*@.*\n)*"            # Match any decorators after @given (including none)
    r"^\s*def\s+\w+\s*\(.*?(\n\s*.*?)*?\)(\s*->\s*\w+\s*)?:)",  # Match the function definition header, including multiline
    re.MULTILINE
)

TIMEOUT_SECONDS = 30
OUTPUT_DIR = Path("collected_pbts")

def run_git_command(args, cwd=None):
    process = run(args, stdout=PIPE, stderr=PIPE, cwd=cwd, text=True)
    if process.returncode != 0:
        raise RuntimeError(f"Git command failed: {' '.join(args)}\n{process.stderr.strip()}")
    return process.stdout

def process_file(file_path):
    results = defaultdict(list)
    try:
        # Read the file 
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        lines = content.splitlines(keepends=True)
        classes = [(m.start(), m.group(1)) for m in CLASS_REGEX.finditer(content)]

        # Find @*.given decorators and extract the function bodies
        for match in DECORATOR_REGEX.finditer(content):
            header = match.group(1)
            header_lines = header.splitlines(keepends=True)
            start_line_idx = content[:match.start()].count("\n")

            # Find test function indentation
            indent_match = re.search(r"^(\s*)def", header, re.MULTILINE)
            indent = indent_match.group(1) if indent_match else "    "

            # Grab function body lines
            body_lines = []
            for i in range(start_line_idx + len(header_lines), len(lines)):
                line = lines[i]
                # Check if the line has one more indentation level than 'def'
                if line.strip() == "" or line.startswith(indent + " ") or line.startswith(indent + "\t"):
                    body_lines.append(line)
                else:
                    break

            # Save full test
            full_test = "".join(header_lines) + "\n" + "".join(body_lines)

            # Remove unnecessary indentation from all lines
            full_test = re.sub(r"^" + re.escape(indent), "", full_test, flags=re.MULTILINE)

            # Determine the enclosing class
            enclosing_class = "(global)"
            for pos, cls in reversed(classes):
                if pos < match.start():
                    enclosing_class = cls
                    break
            
            # Store the test with its enclosing class and line number
            rel_path = str(file_path)
            results[(rel_path, enclosing_class)].append((full_test.strip(), start_line_idx + 2))

    except Exception as e:
        return {"error": f"{file_path}: {e}"}
    return results

def generate_latex_pdf(repo_name, grouped, repo_base, commit_sha):
    OUTPUT_DIR.mkdir(exist_ok=True)
    aux_dir = OUTPUT_DIR / repo_name
    aux_dir.mkdir(exist_ok=True)
    tex_path = aux_dir / f"{repo_name}.tex"
    pdf_path = OUTPUT_DIR / f"{repo_name}.pdf"

    # Remove old files if they exist
    if tex_path.exists():
        tex_path.unlink()
    if pdf_path.exists():
        pdf_path.unlink()

    # Create LaTeX document
    formatter = LatexFormatter(linenos=True, full=False, title=f"Property-based tests from {repo_name}")
    with open(tex_path, "w", encoding="utf-8") as tex:
        tex.write("% Auto-generated LaTeX file with PBTs\n")
        tex.write("\\documentclass{article}\n")
        tex.write("\\usepackage[utf8]{inputenc}\n")
        tex.write("\\usepackage{geometry}\n")
        tex.write("\\usepackage{fancyvrb}\n")
        tex.write("\\usepackage{color}\n")
        tex.write("\\usepackage{listings}\n")
        tex.write("\\usepackage{hyperref}\n")  # Add hyperref for clickable links
        tex.write("\\geometry{margin=1in}\n")
        # Add Pygments macros for LaTeX
        tex.write(formatter.get_style_defs())
        tex.write("\n")
        tex.write("\\begin{document}\n")
        # Use \detokenize to avoid math mode errors with underscores
        tex.write(f"\\section*{{\\texttt{{\\detokenize{{Property-based tests from {repo_name}}}}}}}\n")

        for module, classes in tqdm(sorted(grouped.items()), desc="Writing LaTeX", dynamic_ncols=True):
            tex.write(f"\\subsection*{{\\texttt{{\\detokenize{{{module}}}}}}}\n")
            for cls, tests in sorted(classes.items()):
                tex.write(f"\\subsubsection*{{\\texttt{{\\detokenize{{{cls}}}}}}}\n")
                for test, line_number in tests:
                    permalink = f"{repo_base}/blob/{commit_sha}/{module}#L{line_number}"
                    test_name = re.search(r"def\s+(\w+)\s*\(", test).group(1)  # Extract the test name
                    tex.write(f"\\noindent\\href{{{permalink}}}{{\\textbf{{{test_name.replace("_", "\\_")}}}}}\n")
                    highlighted = highlight(test, PythonLexer(), formatter)
                    tex.write(highlighted) 
                    tex.write("\\vspace{1em}\n")

        tex.write("\\end{document}\n")
        tex.flush()  # Ensure all content is written to the file

    # Compile LaTeX to PDF
    print(f"Compiling LaTeX to PDF...")
    try:
        subprocess.run(["pdflatex", "-output-directory", str(OUTPUT_DIR), str(tex_path)], check=True, stdout=DEVNULL, stderr=DEVNULL)

        # Remove auxiliary files
        for ext in [".aux", ".log", ".out"]:
            aux_file = pdf_path.with_suffix(ext)
            if aux_file.exists():
                aux_file.unlink()

        print(f"PDF saved to {pdf_path}")
    except Exception as e:
        print(f"Failed to generate PDF: {e}")
        print(f"You can compile manually with: pdflatex -output-directory={OUTPUT_DIR} {tex_path}")

def extract_tests_from_repo(repo_url: str):
    repo_cache_dir = Path("./repo_cache")
    repo_cache_dir.mkdir(exist_ok=True)

    if "/commit/" not in repo_url:
        raise ValueError("URL must be a link to a specific commit.")

    # Extract the base URL and commit SHA from the provided URL
    repo_base = repo_url.split("/commit/")[0] + ".git"
    repo_name = repo_base.split("github.com/")[1].replace(".git", "").replace("/", "_")
    commit_sha = repo_url.split("/commit/")[1]

    repo_path = repo_cache_dir / repo_name

    # Clone or update the repository
    print(f"Processing repository: {repo_name}")    
    if not repo_path.exists():
        print("Cloning repository...")
        run_git_command(["git", "clone", repo_base, str(repo_path)])
    else:
        print("Repository already exists. Fetching updates...")
        run_git_command(["git", "fetch"], cwd=repo_path)

    # Checkout the specific commit
    print("Checking out the specified commit...")
    run_git_command(["git", "checkout", commit_sha], cwd=repo_path)

    grouped = defaultdict(lambda: defaultdict(list))
    py_files = [f for f in repo_path.rglob("*.py") if "test" in str(f).lower()]

    # Process files in parallel
    with Pool() as pool:
        for file in tqdm(py_files, desc="Scanning files", dynamic_ncols=True):
            try:
                result = pool.apply_async(process_file, (file,))
                data = result.get(timeout=TIMEOUT_SECONDS)
                if isinstance(data, dict) and "error" in data:
                    print(f"Error: {data['error']}")
                    continue
                for (rel_path, cls), tests in data.items():
                    rel_path = str(Path(rel_path).relative_to(repo_path))
                    grouped[rel_path][cls].extend(tests)
            except TimeoutError:
                print(f"Timeout: Skipped {file}")
            except Exception as e:
                print(f"Error processing {file}: {e}")

    # Write the results to the output file
    aux_dir = OUTPUT_DIR / repo_name
    aux_dir.mkdir(exist_ok=True)
    output_file = aux_dir / f"{repo_name}.py"
    with open(output_file, "w", encoding="utf-8") as out:
        for module, classes in tqdm(sorted(grouped.items()), desc="Writing output", dynamic_ncols=True):
            out.write(f"# File: {module}\n")
            for cls, tests in sorted(classes.items()):
                out.write(f"\n## Class: {cls}\n\n")
                for test, line_number in tests:
                    out.write(test + "\n\n")

    # Generate LaTeX PDF
    generate_latex_pdf(repo_name, grouped, repo_base.replace(".git", ""), commit_sha)
    print(f"Extracted {sum(len(tests) for classes in grouped.values() for tests in classes.values())} property-based tests to {output_file}")


if __name__ == "__main__":
    url = input("Enter GitHub repo commit URL (e.g., https://github.com/user/repo/commit/sha): ").strip()
    extract_tests_from_repo(url)
