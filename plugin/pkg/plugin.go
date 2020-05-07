package plugin

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"regexp"
	"strings"

	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"k8s.io/release/pkg/notes"
	"k8s.io/test-infra/prow/config"
	"k8s.io/test-infra/prow/github"
	"k8s.io/test-infra/prow/pluginhelp"
)

const (
	predictionURL = "https://kfserving.k8s.saschagrunert.de/v1/models/kubernetes-analysis:predict"
	repoOrg       = "kubernetes-analysis"
	commentMarker = "<!-- RELNOTE_PREDICTION -->"
	kindBugLabel  = "kind/bug"
)

// HelpProvider constructs the PluginHelp for this plugin that takes into
// account enabled repositories. helpProvider defines the type for function
// that construct the PluginHelp for plugins.
func HelpProvider([]config.OrgRepo) (*pluginhelp.PluginHelp, error) {
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

	pr := pre.PullRequest
	log.Debugf("Got PR: %+v", pr)
	if pr.Merged {
		log.Infof("PR #%d is already merged", pr.Number)
		return nil
	}

	return handle(log, ghc, pr.User.Login, pr.Number, pr.Body)
}

func handleIssueComment(
	log *logrus.Entry,
	ghc github.Client,
	ice *github.IssueCommentEvent,
) error {
	// Filter out some events
	if ice.Action != github.IssueCommentActionEdited &&
		ice.Action != github.IssueCommentActionCreated {
		return nil
	}

	issue := ice.Issue
	log.Debugf("Got issue: %+v", issue)
	return handle(log, ghc, issue.User.Login, issue.Number, issue.Body)
}

func handle(
	log *logrus.Entry,
	ghc github.Client,
	userLogin string,
	number int,
	body string,
) error {
	log.Infof("Parsing release notes from PR #%d", number)

	prediction, err := Predict(log, predictionURL, body)
	if err != nil {
		return errors.Wrap(err, "predicting release note")
	}

	txt, err := handleLabel(log, ghc, number, prediction)
	if err != nil {
		return errors.Wrap(err, "label handling")
	}

	if err := handleComment(
		log, ghc, userLogin, number, prediction, txt,
	); err != nil {
		return errors.Wrap(err, "comment handling")
	}

	return nil
}

func handleLabel(
	log *logrus.Entry,
	ghc github.Client,
	prNumber int,
	prediction float64,
) (txt string, err error) {
	log.Info("Getting PR labels")
	labels, err := ghc.GetIssueLabels(repoOrg, repoOrg, prNumber)
	if err != nil {
		return "", errors.Wrap(err, "getting PR labels")
	}
	hasLabel := github.HasLabel(kindBugLabel, labels)

	truePrediction := 0.6
	if prediction >= truePrediction && !hasLabel {
		log.Info("Adding the label")
		if err := ghc.AddLabel(
			repoOrg, repoOrg, prNumber, kindBugLabel,
		); err != nil {
			return "", errors.Wrapf(err, "adding %q label", kindBugLabel)
		}
		txt = "I added the label for you."
	} else if prediction < truePrediction && hasLabel {
		log.Info("Removing the label")
		if err := ghc.RemoveLabel(
			repoOrg, repoOrg, prNumber, kindBugLabel,
		); err != nil {
			return "", errors.Wrapf(err, "removing %q label", kindBugLabel)
		}
		txt = "I removed the label for you."
	}
	return txt, nil
}

func handleComment(
	log *logrus.Entry,
	ghc github.Client,
	userLogin string,
	number int,
	prediction float64,
	txt string,
) error {
	// Handle the comments
	bot, err := ghc.BotUser()
	if err != nil {
		return errors.Wrap(err, "getting bot user")
	}

	comments, err := ghc.ListIssueComments(repoOrg, repoOrg, number)
	if err != nil {
		return errors.Wrap(err, "listing comments for PR or issue")
	}

	existingComment := -1
	for i := range comments {
		comment := comments[i]
		if comment.User.Login == bot.Login &&
			strings.Contains(comment.Body, commentMarker) {
			existingComment = comment.ID
			break
		}
	}

	comment := fmt.Sprintf(`Hey @%s :wave:,

I predicted that this release note qualifies as **kind/bug** to **%.2f%%**. %s

%s`, userLogin, prediction*100, txt, commentMarker)

	if existingComment > 0 {
		log.Info("Editing existing comment")

		if err := ghc.EditComment(
			repoOrg, repoOrg, existingComment, comment,
		); err != nil {
			return errors.Wrap(err, "editing PR comment")
		}
	} else {
		log.Info("Creating new comment")

		if err := ghc.CreateComment(
			repoOrg, repoOrg, number, comment,
		); err != nil {
			return errors.Wrap(err, "creating PR comment")
		}
	}

	return nil
}

func Predict(log *logrus.Entry, url, input string) (float64, error) {
	if regexp.MustCompile(
		"(?i)```(release-note[s]?\\s*)?('|\")?(none|n/a|na)?('|\")?\\s*```",
	).MatchString(input) {
		return 0, errors.New("excluded release note")
	}

	note, err := notes.NoteTextFromString(input)
	if err != nil {
		return 0, errors.Wrap(err, "parsing release note")
	}
	log.Infof("Got release note: %s", note)

	log.Infof("Creating JSON request body")
	requestBody, err := json.Marshal(map[string]string{"text": note})
	if err != nil {
		return 0, errors.Wrap(err, "encoding request JSON")
	}

	log.Infof("Doing prediction request")
	resp, err := http.Post(
		url, "application/json", bytes.NewBuffer(requestBody),
	)
	if resp.StatusCode != 200 {
		return 0, errors.Errorf("HTTP status: %s", resp.Status)
	}

	if err != nil {
		return 0, errors.Wrap(err, "HTTP POST request")
	}
	defer func() {
		if err := resp.Body.Close(); err != nil {
			log.Errorf("Unable to close response body: %v", err)
		}
	}()

	log.Infof("Reading response")
	responseBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return 0, errors.Wrap(err, "reading response body")
	}

	log.Infof("Unmarshaling response JSON")
	var response map[string]interface{}
	if err := json.Unmarshal(responseBody, &response); err != nil {
		return 0, errors.Wrap(err, "unmarshaling response JSON")
	}

	result, ok := response["result"].(float64)
	if !ok {
		return 0, errors.Errorf(
			"result type assertion failed of response: %v", response,
		)
	}
	log.Infof("Got prediction result: %f", result)
	return result, nil
}
