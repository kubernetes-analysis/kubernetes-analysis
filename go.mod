module github.com/kubernetes-analysis/kubernetes-analysis

go 1.14

require (
	github.com/pkg/errors v0.9.1
	github.com/sirupsen/logrus v1.6.0
	github.com/stretchr/testify v1.5.1
	k8s.io/release v0.3.1-0.20200508084750-b82e255bb1dd
	k8s.io/test-infra v0.0.0-20200504223708-6c76e02fb720
)

replace (
	github.com/Azure/go-autorest => github.com/Azure/go-autorest v12.2.0+incompatible
	k8s.io/client-go => k8s.io/client-go v0.17.3
)
