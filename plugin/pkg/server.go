package plugin

import (
	"encoding/json"
	"fmt"
	"net/http"

	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"k8s.io/test-infra/prow/github"
)

// Server implements http.Handler. It validates incoming GitHub webhooks and
// then dispatches them to the appropriate plugins.
type Server struct {
	tokenGenerator func() []byte
	ghc            github.Client
	log            *logrus.Entry
}

// NewServer creates a new server instance.
func NewServer(
	tokenGenerator func() []byte,
	ghc github.Client,
	log *logrus.Entry,
) *Server {
	return &Server{tokenGenerator, ghc, log}
}

// ServeHTTP validates an incoming webhook and puts it into the event channel.
func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	eventType, eventGUID, payload, ok, _ := github.ValidateWebhook(
		w, r, s.tokenGenerator,
	)
	if !ok {
		return
	}

	fmt.Fprint(w, "event received")

	if err := s.handleEvent(eventType, eventGUID, payload); err != nil {
		logrus.WithError(err).Error("parsing event failed")
	}
}

func (s *Server) handleEvent(eventType, eventGUID string, payload []byte) error {
	l := s.log.WithFields(
		logrus.Fields{
			"event-type":     eventType,
			github.EventGUID: eventGUID,
		},
	)

	switch eventType {
	case "pull_request":
		var pre github.PullRequestEvent
		if err := json.Unmarshal(payload, &pre); err != nil {
			return errors.Wrap(err, "unmarshalling pull request event")
		}

		go func() {
			if err := handlePullRequestEvent(l, s.ghc, &pre); err != nil {
				l.WithField("event-type", eventType).
					WithError(err).
					Error("Unable to handle event")
			}
		}()
	default:
		s.log.Infof(
			"received an event of type %q but didn't ask for it", eventType,
		)
	}

	return nil
}
