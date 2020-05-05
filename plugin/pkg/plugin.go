package plugin

import (
	"github.com/sirupsen/logrus"

	"k8s.io/test-infra/prow/config"
	"k8s.io/test-infra/prow/github"
	"k8s.io/test-infra/prow/pluginhelp"
)

// HelpProvider constructs the PluginHelp for this plugin that takes into
// account enabled repositories. helpProvider defines the type for function
// that construct the PluginHelp for plugins.
func HelpProvider(_ []config.OrgRepo) (*pluginhelp.PluginHelp, error) {
	return &pluginhelp.PluginHelp{
		Description: "Some useful description",
	}, nil
}

func handlePullRequestEvent(
	log *logrus.Entry, ghc github.Client, pre *github.PullRequestEvent,
) error {
	// Filter out some events
	if pre.Action != github.PullRequestActionOpened &&
		pre.Action != github.PullRequestActionEdited &&
		pre.Action != github.PullRequestActionSynchronize &&
		pre.Action != github.PullRequestActionReopened {
		return nil
	}

	return handle(log, ghc, &pre.PullRequest)
}

func handle(log *logrus.Entry, _ github.Client, pr *github.PullRequest) error {
	if pr.Merged {
		return nil
	}

	log.Infof("Got pr, body:\n%s", pr.Body)

	return nil
}
