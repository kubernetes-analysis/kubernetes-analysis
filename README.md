# Kubernetes Issue Analysis [![CircleCI](https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis.svg?style=shield)](https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis)

### Kubernetes issue and pull request analysis powered by machine learning

This project aims to provide continuous data analysis of all GitHub issues and
pull requests in the [Kubernetes](http://github.com/kubernetes/kubernetes)
repository.

The [data.tar.xz](data.tar.xz) file is basically a compressed JSON file, which
will be updated on a nightly
[CircleCI](https://circleci.com/gh/saschagrunert/kubernetes-issue-analysis) job.
This jobs is using the [export](export) script within this repository to keep
the database up to date.

The [analyze](analyze) script can be used for manual data analysis. This script
automatically extracts the data and operates on it. See `./analyze -h` for more
details.
