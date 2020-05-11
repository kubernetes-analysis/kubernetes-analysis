package plugin

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
	"strings"
	"time"

	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"k8s.io/release/pkg/notes"
	"k8s.io/test-infra/prow/config"
	"k8s.io/test-infra/prow/github"
	"k8s.io/test-infra/prow/pluginhelp"
)

type PredictionResult float64

const (
	CommentMarker                            = "<!-- RELNOTE_PREDICTION -->"
	KindBugLabel                             = "kind/bug"
	TruePrediction          PredictionResult = 0.6
	PredctionResultExcluded PredictionResult = -1.0

	predictionURL = "http://kfserving-ingressgateway.istio-system" + urlPath
	urlPath       = "/v1/models/kubernetes-analysis:predict"
	urlHost       = "kubernetes-analysis.kfserving.example.com"
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
	Predict(url, input string) (PredictionResult, error)
}

type client struct {
	ghc github.Client
}

//go:generate go run github.com/maxbrunsfeld/counterfeiter/v6 -generate
//counterfeiter:generate . Client
type Client interface {
	AddLabel(number int, label string) error
	BotUser() (*github.User, error)
	CreateComment(number int, comment string) error
	DeleteComment(number int) error
	EditComment(id int, comment string) error
	GetIssueLabels(number int) ([]github.Label, error)
	ListIssueComments(number int) ([]github.IssueComment, error)
	RemoveLabel(number int, label string) error
}

func (c *client) AddLabel(number int, label string) error {
	return c.ghc.AddLabel(repoOrg, repoOrg, number, label)
}

func (c *client) BotUser() (*github.User, error) {
	return c.ghc.BotUser()
}

func (c *client) CreateComment(number int, comment string) error {
	return c.ghc.CreateComment(repoOrg, repoOrg, number, comment)
}

func (c *client) DeleteComment(number int) error {
	return c.ghc.DeleteComment(repoOrg, repoOrg, number)
}

func (c *client) EditComment(id int, comment string) error {
	return c.ghc.EditComment(repoOrg, repoOrg, id, comment)
}

func (c *client) GetIssueLabels(number int) ([]github.Label, error) {
	return c.ghc.GetIssueLabels(repoOrg, repoOrg, number)
}

func (c *client) ListIssueComments(number int) ([]github.IssueComment, error) {
	return c.ghc.ListIssueComments(repoOrg, repoOrg, number)
}

func (c *client) RemoveLabel(number int, label string) error {
	return c.ghc.RemoveLabel(repoOrg, repoOrg, number, label)
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

	return p.catchHandle(issue.User.Login, issue.Number, issue.Body)
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

	return p.catchHandle(pr.User.Login, pr.Number, pr.Body)
}

func (p *plugin) catchHandle(login string, number int, body string) error {
	if err := p.handle(login, number, body); err != nil {
		p.log.Warn("Something bad happened, trying to comment that")
		if cerr := p.comment(
			number, 0,
			fmt.Sprintf("Unable to run prediction plugin:**\n%v", err),
		); cerr != nil {
			return errors.Wrap(err, "notifying user about error")
		}
	}
	return nil
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

	additionalText, err := p.label(number, prediction)
	if err != nil {
		return errors.Wrap(err, "label handling")
	}

	message := predictionMessage(userLogin, prediction, additionalText)
	if err := p.comment(number, prediction, message); err != nil {
		return errors.Wrap(err, "comment handling")
	}

	return nil
}

func (p *plugin) label(
	prNumber int, prediction PredictionResult,
) (txt string, err error) {
	p.log.Info("Getting PR labels")
	labels, err := p.client.GetIssueLabels(prNumber)
	if err != nil {
		return "", errors.Wrap(err, "getting PR labels")
	}
	hasLabel := github.HasLabel(KindBugLabel, labels)

	if prediction >= TruePrediction && !hasLabel {
		p.log.Info("Adding the label")
		if err := p.client.AddLabel(prNumber, KindBugLabel); err != nil {
			return "", errors.Wrapf(err, "adding %q label", KindBugLabel)
		}
		txt = "I added the label for you."
	} else if prediction < TruePrediction && hasLabel {
		p.log.Info("Removing the label")
		if err := p.client.RemoveLabel(prNumber, KindBugLabel); err != nil {
			return "", errors.Wrapf(err, "removing %q label", KindBugLabel)
		}
		txt = "I removed the label for you."
	}
	return txt, nil
}

func (p *plugin) comment(
	number int,
	prediction PredictionResult,
	message string,
) error {
	// Handle the comments
	bot, err := p.client.BotUser()
	if err != nil {
		return errors.Wrap(err, "getting bot user")
	}

	comments, err := p.client.ListIssueComments(number)
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

	comment := fmt.Sprintf("%s\n%s", message, CommentMarker)

	if existingComment > 0 {
		if prediction == PredctionResultExcluded {
			p.log.Info("Removing existing comment")
			if err := p.client.DeleteComment(existingComment); err != nil {
				return errors.Wrap(err, "deleting comment")
			}
			return nil
		}

		p.log.Info("Editing existing comment")

		if err := p.client.EditComment(existingComment, comment); err != nil {
			return errors.Wrap(err, "editing comment")
		}
	} else if prediction != PredctionResultExcluded {
		p.log.Info("Creating new comment")

		if err := p.client.CreateComment(number, comment); err != nil {
			return errors.Wrap(err, "creating comment")
		}
	}

	return nil
}

func predictionMessage(
	user string, prediction PredictionResult, additionalText string,
) string {
	return fmt.Sprintf(`Hey @%s :wave:,

I predicted that this release note qualifies as **%s** to **%.2f%%**.

A release note with the kind/bug needs a prediction rate with at least %.0f%%.

%s`,
		user, KindBugLabel, prediction*100, TruePrediction*100, additionalText)
}

func (p *predictor) Predict(url, input string) (PredictionResult, error) {
	if notes.MatchesExcludeFilter(input) || !notes.MatchesIncludeFilter(input) {
		return PredctionResultExcluded, nil
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
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(requestBody))
	if err != nil {
		return 0, errors.Wrap(err, "creating POST request")
	}
	req.Host = urlHost

	client := &http.Client{Timeout: 30 * time.Second}
	resp, err := client.Do(req)
	if err != nil {
		return 0, errors.Wrap(err, "doing HTTP request")
	}

	if resp.StatusCode != http.StatusOK {
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
	return PredictionResult(result), nil
}
