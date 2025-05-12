# Constructing the Dataset
In this file I will elaborate on how I constructed the dataset for my research. The goal is to find open-source repositories that use PBT using Hypothesis. After that, I will filter out all repos that do not have at least two property-based tests using Hypothesis. From the remaining repos I will choose those that have the most stars, while making sure that I am not just researching repositories that have been previously examined for PBTs in work by others.

## Finding the Repositories
I collect the data by using `github-dependents-info` to find all GitHub repositories that were dependent on hypothesis, selecting those that had at least 100 stars, and sorting them by number of stars:

`github-dependents-info --repo HypothesisWorks/hypothesis --sort stars --minstars 100 --markdownfile ./package-usage.md --csvdirectory ./repo_csvs/ --verbose`

Then, I ran the same command, but with `--json`, to save the data to a .json file:

`github-dependents-info --repo HypothesisWorks/hypothesis --sort stars --minstars 100 --json --verbose`

I ran these commands on Thursday, May 1, 2025, at 11:30 am. This resulted in a list of 494 repositories that list Hypothesis as a depenency.

## Filtering the Repos
I created script ([filter_repos.py](filter_repos.py)) that takes the output of the data collection command ([dependents_hypothesis.json](dependents_hypothesis.json)) and turns it into a json file that only contains the repositories that have at least two property-based tests that use Hypothesis. It does so by shallow-cloning all repositories from the json file and counting the number of occurences of `@given` or `@*.given`, which represents the number of PBTs. Of course, this number may not be entirely correct as the script also counts occurences of the `given` keyword in comments, for example. However, it does give an idea of how many PBTs each repositories has.

The output of the script ([filtered_repos.json](filtered_repos.json)) thus contains all GitHub repositories that likely use Hypothesis for at least two property-based tests. Another script ([repolist2md.py](repolist2md.py)) can be used to convert the output json file into a markdown file ([hypothesis_repos.md](hypothesis_repos.md)) that is nice to look at.

I ran these scripts on Thursday, May 1, 2025, around 3:00 pm. This resulted in a list of 273 repositories with at least two property-based tests that use Hypothesis.

## Collecting the Property-Based Tests
The [collect_pbts.py](collect_pbts.py) script collects the property-based tests from the repositories by cloning a repository, checking out a specific commit, and finding all functions that have the decorator `@given` or `@*.given` using regex. The functions are saved to a pdf file that includes the path, class and permalink of the test. 

The pdf files can be used for qualitative analysis of the tests (*open coding using pen and paper*).

I ran [collect_pbts.py](collect_pbts.py) in May 2025 for the following repositories (permalinks are to the specific commits):
- [cpython](https://github.com/python/cpython/commit/483d130e504f63aaf3afe8af3a37650edcdb07a3/)
- [pandas](https://github.com/pandas-dev/pandas/commit/f496acffccfc08f30f8392894a8e0c56d404ef87/)
- [streamlit](https://github.com/streamlit/streamlit/commit/3c99f2051644fd942844d0014540911afeea36bc/)
- [gradio](https://github.com/gradio-app/gradio/commit/d5ddd85d4d5088cce154b1cd50a4a2db179ac227)
- [jax](https://github.com/jax-ml/jax/commit/e2b70767a6c26774b4275b64d9c262dfdd2a7031/)
- [spaCy](https://github.com/explosion/spaCy/commit/87ec2b72a58f2aa21020043ecad11ac2264123e1/)
- [numpy](https://github.com/numpy/numpy/commit/0e7139d253f400fcb68854f357ea507017ffffa4/)