# Kubernetes Issue Analysis [![CircleCI](https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis.svg?style=shield)](https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis)

### Kubernetes issue and pull request analysis powered by machine learning

This project aims to provide continuous data analysis of all GitHub issues and
Pull Requests (PRs) in the [Kubernetes][0] repository.

[0]: http://github.com/kubernetes/kubernetes

#### Data Export and Update

The [data/api.tar.xz][1] file is a compressed JSON file, which contains all the
raw data from the [GitHub issues API endpoint][2], which returns the PRs as
well. This file will be updated on a nightly [CircleCI][3] job.

The base data for the Natural Language Parsing (NLP) is stored in a separate
tarball in [data/bow.tar.xz][4]. This archive contains all [Bag of Words][5] for
the issues and PRs from the local API data set.

Every update job is using the [./export][6] script within this repository to
keep the data sets up to date.

[1]: data/api.tar.xz
[2]: https://developer.github.com/v3/issues/#list-repository-issues
[3]: https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis
[4]: data/bow.tar.xz
[5]: https://en.wikipedia.org/wiki/Bag-of-words_model
[6]: ./export

### Analysis

The [./analyze][5] script can be used for manual data analysis. This script
automatically extracts the data and operates on it. See `./analyze -h` for more
details.

[5]: ./analyze
