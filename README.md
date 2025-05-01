# Constructing the Dataset
In this file I will elaborate on how I constructed the dataset for my research. The goal is to find open-source repositories that use PBT using Hypothesis. After that, I will filter out all repos that do not have at least two property-based tests using Hypothesis. From the remaining repos I will choose those that have the most stars, while making sure that I am not just researching repositories that have been previously examined for PBTs in work by others.

## Collecting the Data
I collect the data by using `github-dependents-info` to find all GitHub repositories that were depenendent on hypothesis, selecting those that had at least 100 stars, and sorting them by number of stars:

`github-dependents-info --repo HypothesisWorks/hypothesis --sort stars --minstars 100 --markdownfile ./package-usage.md --csvdirectory ./repo_csvs/ --verbose`

Then, I ran the same command, but with `--json`, to save the data to a .json file:

`github-dependents-info --repo HypothesisWorks/hypothesis --sort stars --minstars 100 --json --verbose`

I ran these commands on Thursday, March 1, 2025, at 11:30 am. This resulted in a list of 494 repositories that list Hypothesis as a depenency.

## Filtering the Repos
I created script ([filter_repos.py](filter_repos.py)) that takes the [output of the data collection command](dependents_hypothesis.json) and turns it into a json file that only contains the repositories that have at least two property-based tests that use Hypothesis. It does so by shallow-cloning all repositories from the json file and counting the number of occurences of `@given` or `@*.given`, which represents the number of PBTs. Ofcourse, this number may not be entirely correct as the script also counts occurences of the `given` keyword in comments, for example. However, it does give an idea of how many PBTs each repositories has.

The [output of the script](filtered_repos.json) thus contains all GitHub repositories that likely use Hypothesis for at least two property-based tests. [Another script](repolist2md.py) can be used to convert the output json file into a [markdown file](hypothesis_repos.md) that is nice to look at.

I ran these scripts on Thursday, March 1, 2025, around 3:00 pm. This resulted in a list of 273 repositories with at least two property-based tests that use Hypothesis.