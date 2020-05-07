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
	CommentMarker  = "<!-- RELNOTE_PREDICTION -->"
	KindBugLabel   = "kind/bug"
	TruePrediction = 0.6

	predictionURL = "https://kfserving.k8s.saschagrunert.de/v1/models/kubernetes-analysis:predict"
	repoOrg       = "kubernetes-analysis"
)

type plugin struct {
	log       *logrus.Entry
	client    Client
	predictor Predictor
}

// New creates a new plugin instance.
func New(log *logrus.Entry, ghc github.Client) Plugin {
	return &plugin{
		log:       log,
		client:    &client{ghc},
		predictor: &predictor{log},
	}
}

//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6 -generate
//counterfeiter:generate . Plugin
type Plugin interface {
	HandleIssueEvent(*github.IssueEvent) error
	HandlePullRequestEvent(*github.PullRequestEvent) error
	SetPredictor(Predictor)
	SetClient(Client)
}

type predictor struct {
	log *logrus.Entry
}

// NewPredictor creates a new predictor instance.
func NewPredictor(log *logrus.Entry) Predictor {
	return &predictor{log}
}

//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6 -generate
//counterfeiter:generate . Predictor
type Predictor interface {
	Predict(url, input string) (float64, error)
}

type client struct {
	ghc github.Client
}

//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6 -generate
//counterfeiter:generate . Client
type Client interface {
	AddLabel(org, repo string, number int, label string) error
	BotUser() (*github.User, error)
	CreateComment(org, repo string, number int, comment string) error
	EditComment(org, repo string, id int, comment string) error
	GetIssueLabels(org, repo string, number int) ([]github.Label, error)
	ListIssueComments(org, repo string, nr int) ([]github.IssueComment, error)
	RemoveLabel(org, repo string, number int, label string) error
}

func (c *client) AddLabel(org, repo string, number int, label string) error {
	return c.ghc.AddLabel(org, repo, number, label)
}

func (c *client) BotUser() (*github.User, error) {
	return c.ghc.BotUser()
}

func (c *client) CreateComment(
	org, repo string, number int, comment string,
) error {
	return c.ghc.CreateComment(org, repo, number, comment)
}

func (c *client) EditComment(
	org, repo string, id int, comment string,
) error {
	return c.ghc.EditComment(org, repo, id, comment)
}

func (c *client) GetIssueLabels(
	org, repo string, number int,
) ([]github.Label, error) {
	return c.ghc.GetIssueLabels(org, repo, number)
}

func (c *client) ListIssueComments(
	org, repo string, number int,
) ([]github.IssueComment, error) {
	return c.ghc.ListIssueComments(org, repo, number)
}

func (c *client) RemoveLabel(
	org, repo string, number int, label string,
) error {
	return c.ghc.RemoveLabel(org, repo, number, label)
}

// HelpProvider constructs the PluginHelp for this plugin that takes into
// account enabled repositories. helpProvider defines the type for function
// that construct the PluginHelp for plugins.
func HelpProvider([]config.OrgRepo) (*pluginhelp.PluginHelp, error) {
	return &pluginhelp.PluginHelp{
		Description: "Some useful description",
	}, nil
}

// SetPredictor sets the internal predictor.
func (p *plugin) SetPredictor(predictor Predictor) {
	p.predictor = predictor
}

// SetClient sets the internal client.
func (p *plugin) SetClient(client Client) {
	p.client = client
}

func (p *plugin) HandleIssueEvent(ie *github.IssueEvent) error {
	// Filter out some events
	if ie.Action != github.IssueActionOpened &&
		ie.Action != github.IssueActionEdited {
		return nil
	}

	issue := ie.Issue
	p.log.Debugf("Got issue: %+v", issue)
	return p.handle(issue.User.Login, issue.Number, issue.Body)
}

func (p *plugin) HandlePullRequestEvent(pre *github.PullRequestEvent) error {
	// Filter out some events
	if pre.Action != github.PullRequestActionOpened &&
		pre.Action != github.PullRequestActionEdited &&
		pre.Action != github.PullRequestActionSynchronize &&
		pre.Action != github.PullRequestActionReopened {
		return nil
	}

	pr := pre.PullRequest
	p.log.Debugf("Got PR: %+v", pr)
	if pr.Merged {
		p.log.Infof("PR #%d is already merged", pr.Number)
		return nil
	}

	return p.handle(pr.User.Login, pr.Number, pr.Body)
}

func (p *plugin) handle(
	userLogin string,
	number int,
	body string,
) error {
	p.log.Infof("Parsing release notes from PR #%d", number)

	prediction, err := p.predictor.Predict(predictionURL, body)
	if err != nil {
		return errors.Wrap(err, "predicting release note")
	}

	txt, err := p.handleLabel(number, prediction)
	if err != nil {
		return errors.Wrap(err, "label handling")
	}

	if err := p.handleComment(userLogin, number, prediction, txt); err != nil {
		return errors.Wrap(err, "comment handling")
	}

	return nil
}

func (p *plugin) handleLabel(
	prNumber int, prediction float64,
) (txt string, err error) {
	p.log.Info("Getting PR labels")
	labels, err := p.client.GetIssueLabels(repoOrg, repoOrg, prNumber)
	if err != nil {
		return "", errors.Wrap(err, "getting PR labels")
	}
	hasLabel := github.HasLabel(KindBugLabel, labels)

	if prediction >= TruePrediction && !hasLabel {
		p.log.Info("Adding the label")
		if err := p.client.AddLabel(
			repoOrg, repoOrg, prNumber, KindBugLabel,
		); err != nil {
			return "", errors.Wrapf(err, "adding %q label", KindBugLabel)
		}
		txt = "I added the label for you."
	} else if prediction < TruePrediction && hasLabel {
		p.log.Info("Removing the label")
		if err := p.client.RemoveLabel(
			repoOrg, repoOrg, prNumber, KindBugLabel,
		); err != nil {
			return "", errors.Wrapf(err, "removing %q label", KindBugLabel)
		}
		txt = "I removed the label for you."
	}
	return txt, nil
}

func (p *plugin) handleComment(
	userLogin string,
	number int,
	prediction float64,
	txt string,
) error {
	// Handle the comments
	bot, err := p.client.BotUser()
	if err != nil {
		return errors.Wrap(err, "getting bot user")
	}

	comments, err := p.client.ListIssueComments(repoOrg, repoOrg, number)
	if err != nil {
		return errors.Wrap(err, "listing comments for PR or issue")
	}

	existingComment := -1
	for i := range comments {
		comment := comments[i]
		if comment.User.Login == bot.Login &&
			strings.Contains(comment.Body, CommentMarker) {
			existingComment = comment.ID
			break
		}
	}

	comment := fmt.Sprintf(`Hey @%s :wave:,

I predicted that this release note qualifies as **kind/bug** to **%.2f%%**.

A release note with the kind/bug needs a prediction rate with at least %.0f%%.

%s
%s`, userLogin, prediction*100, TruePrediction*100, txt, CommentMarker)

	if existingComment > 0 {
		p.log.Info("Editing existing comment")

		if err := p.client.EditComment(
			repoOrg, repoOrg, existingComment, comment,
		); err != nil {
			return errors.Wrap(err, "editing PR comment")
		}
	} else {
		p.log.Info("Creating new comment")

		if err := p.client.CreateComment(
			repoOrg, repoOrg, number, comment,
		); err != nil {
			return errors.Wrap(err, "creating PR comment")
		}
	}

	return nil
}

func (p *predictor) Predict(url, input string) (float64, error) {
	if regexp.MustCompile(
		"(?i)```(release-note[s]?\\s*)?('|\")?(none|n/a|na)?('|\")?\\s*```",
	).MatchString(input) {
		return 0, errors.New("excluded release note")
	}

	note, err := notes.NoteTextFromString(input)
	if err != nil {
		return 0, errors.Wrap(err, "parsing release note")
	}
	p.log.Infof("Got release note: %s", note)

	p.log.Infof("Creating JSON request body")
	requestBody, err := json.Marshal(map[string]string{"text": note})
	if err != nil {
		return 0, errors.Wrap(err, "encoding request JSON")
	}

	p.log.Infof("Doing prediction request")
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
			p.log.Errorf("Unable to close response body: %v", err)
		}
	}()

	p.log.Infof("Reading response")
	responseBody, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return 0, errors.Wrap(err, "reading response body")
	}

	p.log.Infof("Unmarshaling response JSON")
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
	p.log.Infof("Got prediction result: %f", result)
	return result, nil
}
