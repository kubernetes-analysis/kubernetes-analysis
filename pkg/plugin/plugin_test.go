package plugin_test

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/require"
	"k8s.io/test-infra/prow/github"

	"github.com/kubernetes-analysis/kubernetes-analysis/pkg/plugin"
	"github.com/kubernetes-analysis/kubernetes-analysis/pkg/plugin/pluginfakes"
)

var err = errors.New("error")

func newSUT() (
	plugin.Plugin, *pluginfakes.FakePredictor, *pluginfakes.FakeClient,
) {
	sut := plugin.New(log(), nil)

	fakePredictor := &pluginfakes.FakePredictor{}
	sut.SetPredictor(fakePredictor)

	fakeClient := &pluginfakes.FakeClient{}
	sut.SetClient(fakeClient)

	return sut, fakePredictor, fakeClient
}

func log() *logrus.Entry {
	return logrus.StandardLogger().WithContext(context.Background())
}

func testServer(t *testing.T, json string) *httptest.Server {
	return httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) {
			_, err := io.WriteString(w, json)
			require.Nil(t, err)
		},
	))
}

func validNote() string {
	return fmt.Sprintf(
		"```release-note\n%s\n```",
		"This is my release note",
	)
}

func TestSuccessHandlePullRequestEvent(t *testing.T) {
	sut, _, _ := newSUT()

	err := sut.HandlePullRequestEvent(&github.PullRequestEvent{
		Action: github.PullRequestActionOpened,
	})

	require.Nil(t, err)
}

func TestSuccessHandlePullRequestEventMerged(t *testing.T) {
	sut, _, _ := newSUT()

	err := sut.HandlePullRequestEvent(&github.PullRequestEvent{
		Action:      github.PullRequestActionOpened,
		PullRequest: github.PullRequest{Merged: true},
	})

	require.Nil(t, err)
}

func TestSuccessHandlePullRequestEventWrongAction(t *testing.T) {
	sut, _, _ := newSUT()

	err := sut.HandlePullRequestEvent(&github.PullRequestEvent{})

	require.Nil(t, err)
}

func TestSuccessHandleIssueEvent(t *testing.T) {
	sut, _, _ := newSUT()

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.Nil(t, err)
}

func TestSuccessHandleIssueEventWrongAction(t *testing.T) {
	sut, _, _ := newSUT()

	err := sut.HandleIssueEvent(&github.IssueEvent{})

	require.Nil(t, err)
}

func TestFailureHandleIssueEventPredict(t *testing.T) {
	sut, predictor, _ := newSUT()
	predictor.PredictReturns(0, err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.NotNil(t, err)
}

func TestFailreHandleIssueEventBotUser(t *testing.T) {
	sut, _, client := newSUT()
	client.BotUserReturns(nil, err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.NotNil(t, err)
}

func TestFailreHandleIssueEventListIssueComments(t *testing.T) {
	sut, _, client := newSUT()
	client.ListIssueCommentsReturns(nil, err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.NotNil(t, err)
}

func TestFailreHandleIssueEventCreateComment(t *testing.T) {
	sut, _, client := newSUT()
	client.CreateCommentReturns(err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.NotNil(t, err)
}

func TestSuccessHandleIssueEventListIssueComments(t *testing.T) {
	sut, _, client := newSUT()
	bot := github.User{Login: "bot"}
	client.BotUserReturns(&bot, nil)
	client.ListIssueCommentsReturns([]github.IssueComment{
		{ID: 50, Body: plugin.CommentMarker, User: bot},
	}, nil)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
		Issue:  github.Issue{User: bot},
	})

	require.Nil(t, err)
}

func TestFailureHandleIssueEventListIssueCommentsEditComment(t *testing.T) {
	sut, _, client := newSUT()
	bot := github.User{Login: "bot"}
	client.BotUserReturns(&bot, nil)
	client.ListIssueCommentsReturns([]github.IssueComment{
		{ID: 50, Body: plugin.CommentMarker, User: bot},
	}, nil)
	client.EditCommentReturns(err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
		Issue:  github.Issue{User: bot},
	})

	require.NotNil(t, err)
}

func TestSuccessHandleIssueEventAddLabel(t *testing.T) {
	sut, predictor, _ := newSUT()
	predictor.PredictReturns(plugin.TruePrediction+0.1, nil)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.Nil(t, err)
}

func TestSuccessHandleIssueEventRemoveLabel(t *testing.T) {
	sut, predictor, client := newSUT()
	predictor.PredictReturns(plugin.TruePrediction-0.1, nil)
	client.GetIssueLabelsReturns([]github.Label{
		{Name: plugin.KindBugLabel},
	}, nil)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.Nil(t, err)
}

func TestFailureHandleIssueEventRemoveLabel(t *testing.T) {
	sut, predictor, client := newSUT()
	predictor.PredictReturns(plugin.TruePrediction-0.1, nil)
	client.GetIssueLabelsReturns([]github.Label{
		{Name: plugin.KindBugLabel},
	}, nil)
	client.RemoveLabelReturns(err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.NotNil(t, err)
}

func TestFailureHandleIssueEventAddLabel(t *testing.T) {
	sut, predictor, client := newSUT()
	predictor.PredictReturns(plugin.TruePrediction+0.1, nil)
	client.AddLabelReturns(err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.NotNil(t, err)
}

func TestFailureHandleIssueEventGetIssueLabels(t *testing.T) {
	sut, predictor, client := newSUT()
	predictor.PredictReturns(plugin.TruePrediction+0.1, nil)
	client.GetIssueLabelsReturns(nil, err)

	err := sut.HandleIssueEvent(&github.IssueEvent{
		Action: github.IssueActionOpened,
	})

	require.NotNil(t, err)
}

func TestPredictSuccess(t *testing.T) {
	server := testServer(t, `{"result": 0.5}`)
	defer server.Close()

	res, err := plugin.NewPredictor(log()).Predict(server.URL, validNote())

	require.Nil(t, err)
	require.NotZero(t, res)
}

func TestPredictFailureResultNoFloat(t *testing.T) {
	server := testServer(t, `{"result": "wrong"}`)
	defer server.Close()

	res, err := plugin.NewPredictor(log()).Predict(server.URL, validNote())

	require.NotNil(t, err)
	require.Zero(t, res)
}

func TestPredictFailureResultNoJSON(t *testing.T) {
	server := testServer(t, "wrong")
	defer server.Close()

	res, err := plugin.NewPredictor(log()).Predict(server.URL, validNote())

	require.NotNil(t, err)
	require.Zero(t, res)
}

func TestPredictFailureResultNoBody(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(
		func(w http.ResponseWriter, r *http.Request) {
			w.WriteHeader(404)
		},
	))
	defer server.Close()

	res, err := plugin.NewPredictor(log()).Predict(server.URL, validNote())

	require.NotNil(t, err)
	require.Zero(t, res)
}

func TestPredictFailureNotNote(t *testing.T) {
	res, err := plugin.NewPredictor(log()).Predict("", "wrong")
	require.NotNil(t, err)
	require.Zero(t, res)
}

func TestPredictFailureExcluded(t *testing.T) {
	releaseNote := "```release-note\nNone\n```"

	res, err := plugin.NewPredictor(log()).Predict("", releaseNote)

	require.NotNil(t, err)
	require.Zero(t, res)
}
