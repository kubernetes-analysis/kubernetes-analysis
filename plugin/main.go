package main

import (
	"flag"
	"fmt"
	"net/http"
	"os"
	"strconv"
	"time"

	"github.com/pkg/errors"
	"github.com/sirupsen/logrus"
	"k8s.io/test-infra/pkg/flagutil"
	"k8s.io/test-infra/prow/config/secret"
	prowflagutil "k8s.io/test-infra/prow/flagutil"
	"k8s.io/test-infra/prow/interrupts"
	"k8s.io/test-infra/prow/pluginhelp/externalplugins"
	"k8s.io/test-infra/prow/plugins"

	plugin "github.com/kubernetes-analysis/kubernetes-analysis/plugin/pkg"
)

const (
	port       = 8888
	pluginName = "kubernetes-analysis"
)

type options struct {
	pluginConfig      string
	webhookSecretFile string
	dryRun            bool
	github            prowflagutil.GitHubOptions
}

func (o *options) validate() error {
	for idx, group := range []flagutil.OptionGroup{&o.github} {
		if err := group.Validate(o.dryRun); err != nil {
			return fmt.Errorf("%d: %w", idx, err)
		}
	}

	return nil
}

func gatherOptions() (*options, error) {
	o := options{}
	fs := flag.NewFlagSet(os.Args[0], flag.ExitOnError)

	fs.StringVar(
		&o.pluginConfig,
		"plugin-config",
		"/etc/plugins/plugins.yaml",
		"Path to plugin config file.",
	)

	fs.BoolVar(
		&o.dryRun,
		"dry-run",
		true,
		"Dry run for testing. Uses API tokens but does not mutate.",
	)

	fs.StringVar(
		&o.webhookSecretFile,
		"hmac-secret-file",
		"/etc/webhook/hmac",
		"Path to the file containing the GitHub HMAC secret.",
	)

	for _, group := range []flagutil.OptionGroup{&o.github} {
		group.AddFlags(fs)
	}

	if err := fs.Parse(os.Args[1:]); err != nil {
		return nil, errors.Wrap(err, "parsing CLI args")
	}

	return &o, nil
}

func main() {
	if err := run(); err != nil {
		logrus.Fatal(err)
	}
}

func run() error {
	logrus.SetFormatter(&logrus.JSONFormatter{DisableTimestamp: true})
	logrus.SetLevel(logrus.InfoLevel)

	o, err := gatherOptions()
	if err != nil {
		return errors.Wrap(err, "gathering options")
	}

	if err := o.validate(); err != nil {
		return errors.Wrap(err, "validating options")
	}

	secretAgent := &secret.Agent{}
	if err := secretAgent.Start([]string{
		o.github.TokenPath, o.webhookSecretFile,
	}); err != nil {
		return errors.Wrap(err, "starting secrets agent")
	}

	pa := &plugins.ConfigAgent{}
	if err := pa.Start(o.pluginConfig, false); err != nil {
		return errors.Wrap(err, "starting config agent")
	}

	githubClient, err := o.github.GitHubClient(secretAgent, o.dryRun)
	if err != nil {
		return errors.Wrap(err, "getting GitHub client")
	}
	githubClient.Throttle(360, 360)

	log := logrus.StandardLogger().WithField("plugin", pluginName)
	server := plugin.NewServer(
		secretAgent.GetTokenGenerator(o.webhookSecretFile),
		githubClient,
		log,
	)
	defer interrupts.WaitForGracefulShutdown()

	mux := http.NewServeMux()
	mux.Handle("/", server)
	externalplugins.ServeExternalPluginHelp(mux, log, plugin.HelpProvider)
	httpServer := &http.Server{Addr: ":" + strconv.Itoa(port), Handler: mux}
	interrupts.ListenAndServe(httpServer, 5*time.Second)

	return nil
}
