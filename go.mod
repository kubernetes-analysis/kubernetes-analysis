module github.com/kubernetes-analysis/kubernetes-analysis

go 1.14

require (
	github.com/pkg/errors v0.9.1
	github.com/sirupsen/logrus v1.6.0
	github.com/stretchr/testify v1.5.1
	k8s.io/release v0.3.2-0.20200515084658-44f0f159dd82
	k8s.io/test-infra v0.0.0-20200515104936-59705fc01a8d
)

replace (
	github.com/Azure/go-autorest => github.com/Azure/go-autorest v12.2.0+incompatible
	k8s.io/client-go => k8s.io/client-go v0.17.3
)
