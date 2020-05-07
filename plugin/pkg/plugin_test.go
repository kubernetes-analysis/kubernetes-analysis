package plugin_test

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/sirupsen/logrus"
	"github.com/stretchr/testify/require"

	plugin "github.com/kubernetes-analysis/kubernetes-analysis/plugin/pkg"
)

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

func TestPredictSuccess(t *testing.T) {
	server := testServer(t, `{"result": 0.5}`)
	defer server.Close()

	res, err := plugin.Predict(log(), server.URL, validNote())

	require.Nil(t, err)
	require.NotZero(t, res)
}

func TestPredictFailureResultNoFloat(t *testing.T) {
	server := testServer(t, `{"result": "wrong"}`)
	defer server.Close()

	res, err := plugin.Predict(log(), server.URL, validNote())

	require.NotNil(t, err)
	require.Zero(t, res)
}

func TestPredictFailureResultNoJSON(t *testing.T) {
	server := testServer(t, "wrong")
	defer server.Close()

	res, err := plugin.Predict(log(), server.URL, validNote())

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

	res, err := plugin.Predict(log(), server.URL, validNote())

	require.NotNil(t, err)
	require.Zero(t, res)
}

func TestPredictFailureNotNote(t *testing.T) {
	res, err := plugin.Predict(log(), "", "wrong")
	require.NotNil(t, err)
	require.Zero(t, res)
}

func TestPredictFailureExcluded(t *testing.T) {
	releaseNote := "```release-note\nNone\n```"

	res, err := plugin.Predict(log(), "", releaseNote)

	require.NotNil(t, err)
	require.Zero(t, res)
}
