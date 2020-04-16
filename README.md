# Kubernetes Issue Analysis [![CircleCI](https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis.svg?style=shield)](https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis)

### Kubernetes issue and pull request analysis powered by machine learning

This project aims to provide continuous data analysis of all GitHub issues and
pull requests in the [Kubernetes][0] repository.

[0]: http://github.com/kubernetes/kubernetes

#### Data

The [data/api.tar.xz][1] file is a compressed JSON file, which contains all the
raw data from the [GitHub issues API endpoint][2]. This file will be updated on
a nightly [CircleCI][3] job.

Every update job is using the [./export][4] script within this repository to
keep the datasets up to date.

[1]: data/api.tar.xz
[2]: https://developer.github.com/v3/issues/#list-repository-issues
[3]: https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis
[4]: ./export

### Analysis

The [./analyze][5] script can be used for manual data analysis. This script
automatically extracts the data and operates on it. See `./analyze -h` for more
details.

[5]: ./analyze
