all: build

.PHONY: build
build:
	go build \
		-tags "netgo" \
		-ldflags '-s -w -linkmode external -extldflags "-static -lm"'

.PHONY: test
test:
	go test -v -count=1 -cover -coverprofile coverage.out ./... $(ARGS)
	go tool cover -html coverage.out -o coverage.html
