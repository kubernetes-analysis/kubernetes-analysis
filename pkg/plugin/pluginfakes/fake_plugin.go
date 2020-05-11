// Code generated by counterfeiter. DO NOT EDIT.
package pluginfakes

import (
	"sync"

	"github.com/kubernetes-analysis/kubernetes-analysis/pkg/plugin"
	"k8s.io/test-infra/prow/github"
)

type FakePlugin struct {
	HandleIssueEventStub        func(*github.IssueEvent) error
	handleIssueEventMutex       sync.RWMutex
	handleIssueEventArgsForCall []struct {
		arg1 *github.IssueEvent
	}
	handleIssueEventReturns struct {
		result1 error
	}
	handleIssueEventReturnsOnCall map[int]struct {
		result1 error
	}
	HandlePullRequestEventStub        func(*github.PullRequestEvent) error
	handlePullRequestEventMutex       sync.RWMutex
	handlePullRequestEventArgsForCall []struct {
		arg1 *github.PullRequestEvent
	}
	handlePullRequestEventReturns struct {
		result1 error
	}
	handlePullRequestEventReturnsOnCall map[int]struct {
		result1 error
	}
	SetClientStub        func(plugin.Client)
	setClientMutex       sync.RWMutex
	setClientArgsForCall []struct {
		arg1 plugin.Client
	}
	SetPredictorStub        func(plugin.Predictor)
	setPredictorMutex       sync.RWMutex
	setPredictorArgsForCall []struct {
		arg1 plugin.Predictor
	}
	invocations      map[string][][]interface{}
	invocationsMutex sync.RWMutex
}

func (fake *FakePlugin) HandleIssueEvent(arg1 *github.IssueEvent) error {
	fake.handleIssueEventMutex.Lock()
	ret, specificReturn := fake.handleIssueEventReturnsOnCall[len(fake.handleIssueEventArgsForCall)]
	fake.handleIssueEventArgsForCall = append(fake.handleIssueEventArgsForCall, struct {
		arg1 *github.IssueEvent
	}{arg1})
	fake.recordInvocation("HandleIssueEvent", []interface{}{arg1})
	fake.handleIssueEventMutex.Unlock()
	if fake.HandleIssueEventStub != nil {
		return fake.HandleIssueEventStub(arg1)
	}
	if specificReturn {
		return ret.result1
	}
	fakeReturns := fake.handleIssueEventReturns
	return fakeReturns.result1
}

func (fake *FakePlugin) HandleIssueEventCallCount() int {
	fake.handleIssueEventMutex.RLock()
	defer fake.handleIssueEventMutex.RUnlock()
	return len(fake.handleIssueEventArgsForCall)
}

func (fake *FakePlugin) HandleIssueEventCalls(stub func(*github.IssueEvent) error) {
	fake.handleIssueEventMutex.Lock()
	defer fake.handleIssueEventMutex.Unlock()
	fake.HandleIssueEventStub = stub
}

func (fake *FakePlugin) HandleIssueEventArgsForCall(i int) *github.IssueEvent {
	fake.handleIssueEventMutex.RLock()
	defer fake.handleIssueEventMutex.RUnlock()
	argsForCall := fake.handleIssueEventArgsForCall[i]
	return argsForCall.arg1
}

func (fake *FakePlugin) HandleIssueEventReturns(result1 error) {
	fake.handleIssueEventMutex.Lock()
	defer fake.handleIssueEventMutex.Unlock()
	fake.HandleIssueEventStub = nil
	fake.handleIssueEventReturns = struct {
		result1 error
	}{result1}
}

func (fake *FakePlugin) HandleIssueEventReturnsOnCall(i int, result1 error) {
	fake.handleIssueEventMutex.Lock()
	defer fake.handleIssueEventMutex.Unlock()
	fake.HandleIssueEventStub = nil
	if fake.handleIssueEventReturnsOnCall == nil {
		fake.handleIssueEventReturnsOnCall = make(map[int]struct {
			result1 error
		})
	}
	fake.handleIssueEventReturnsOnCall[i] = struct {
		result1 error
	}{result1}
}

func (fake *FakePlugin) HandlePullRequestEvent(arg1 *github.PullRequestEvent) error {
	fake.handlePullRequestEventMutex.Lock()
	ret, specificReturn := fake.handlePullRequestEventReturnsOnCall[len(fake.handlePullRequestEventArgsForCall)]
	fake.handlePullRequestEventArgsForCall = append(fake.handlePullRequestEventArgsForCall, struct {
		arg1 *github.PullRequestEvent
	}{arg1})
	fake.recordInvocation("HandlePullRequestEvent", []interface{}{arg1})
	fake.handlePullRequestEventMutex.Unlock()
	if fake.HandlePullRequestEventStub != nil {
		return fake.HandlePullRequestEventStub(arg1)
	}
	if specificReturn {
		return ret.result1
	}
	fakeReturns := fake.handlePullRequestEventReturns
	return fakeReturns.result1
}

func (fake *FakePlugin) HandlePullRequestEventCallCount() int {
	fake.handlePullRequestEventMutex.RLock()
	defer fake.handlePullRequestEventMutex.RUnlock()
	return len(fake.handlePullRequestEventArgsForCall)
}

func (fake *FakePlugin) HandlePullRequestEventCalls(stub func(*github.PullRequestEvent) error) {
	fake.handlePullRequestEventMutex.Lock()
	defer fake.handlePullRequestEventMutex.Unlock()
	fake.HandlePullRequestEventStub = stub
}

func (fake *FakePlugin) HandlePullRequestEventArgsForCall(i int) *github.PullRequestEvent {
	fake.handlePullRequestEventMutex.RLock()
	defer fake.handlePullRequestEventMutex.RUnlock()
	argsForCall := fake.handlePullRequestEventArgsForCall[i]
	return argsForCall.arg1
}

func (fake *FakePlugin) HandlePullRequestEventReturns(result1 error) {
	fake.handlePullRequestEventMutex.Lock()
	defer fake.handlePullRequestEventMutex.Unlock()
	fake.HandlePullRequestEventStub = nil
	fake.handlePullRequestEventReturns = struct {
		result1 error
	}{result1}
}

func (fake *FakePlugin) HandlePullRequestEventReturnsOnCall(i int, result1 error) {
	fake.handlePullRequestEventMutex.Lock()
	defer fake.handlePullRequestEventMutex.Unlock()
	fake.HandlePullRequestEventStub = nil
	if fake.handlePullRequestEventReturnsOnCall == nil {
		fake.handlePullRequestEventReturnsOnCall = make(map[int]struct {
			result1 error
		})
	}
	fake.handlePullRequestEventReturnsOnCall[i] = struct {
		result1 error
	}{result1}
}

func (fake *FakePlugin) SetClient(arg1 plugin.Client) {
	fake.setClientMutex.Lock()
	fake.setClientArgsForCall = append(fake.setClientArgsForCall, struct {
		arg1 plugin.Client
	}{arg1})
	fake.recordInvocation("SetClient", []interface{}{arg1})
	fake.setClientMutex.Unlock()
	if fake.SetClientStub != nil {
		fake.SetClientStub(arg1)
	}
}

func (fake *FakePlugin) SetClientCallCount() int {
	fake.setClientMutex.RLock()
	defer fake.setClientMutex.RUnlock()
	return len(fake.setClientArgsForCall)
}

func (fake *FakePlugin) SetClientCalls(stub func(plugin.Client)) {
	fake.setClientMutex.Lock()
	defer fake.setClientMutex.Unlock()
	fake.SetClientStub = stub
}

func (fake *FakePlugin) SetClientArgsForCall(i int) plugin.Client {
	fake.setClientMutex.RLock()
	defer fake.setClientMutex.RUnlock()
	argsForCall := fake.setClientArgsForCall[i]
	return argsForCall.arg1
}

func (fake *FakePlugin) SetPredictor(arg1 plugin.Predictor) {
	fake.setPredictorMutex.Lock()
	fake.setPredictorArgsForCall = append(fake.setPredictorArgsForCall, struct {
		arg1 plugin.Predictor
	}{arg1})
	fake.recordInvocation("SetPredictor", []interface{}{arg1})
	fake.setPredictorMutex.Unlock()
	if fake.SetPredictorStub != nil {
		fake.SetPredictorStub(arg1)
	}
}

func (fake *FakePlugin) SetPredictorCallCount() int {
	fake.setPredictorMutex.RLock()
	defer fake.setPredictorMutex.RUnlock()
	return len(fake.setPredictorArgsForCall)
}

func (fake *FakePlugin) SetPredictorCalls(stub func(plugin.Predictor)) {
	fake.setPredictorMutex.Lock()
	defer fake.setPredictorMutex.Unlock()
	fake.SetPredictorStub = stub
}

func (fake *FakePlugin) SetPredictorArgsForCall(i int) plugin.Predictor {
	fake.setPredictorMutex.RLock()
	defer fake.setPredictorMutex.RUnlock()
	argsForCall := fake.setPredictorArgsForCall[i]
	return argsForCall.arg1
}

func (fake *FakePlugin) Invocations() map[string][][]interface{} {
	fake.invocationsMutex.RLock()
	defer fake.invocationsMutex.RUnlock()
	fake.handleIssueEventMutex.RLock()
	defer fake.handleIssueEventMutex.RUnlock()
	fake.handlePullRequestEventMutex.RLock()
	defer fake.handlePullRequestEventMutex.RUnlock()
	fake.setClientMutex.RLock()
	defer fake.setClientMutex.RUnlock()
	fake.setPredictorMutex.RLock()
	defer fake.setPredictorMutex.RUnlock()
	copiedInvocations := map[string][][]interface{}{}
	for key, value := range fake.invocations {
		copiedInvocations[key] = value
	}
	return copiedInvocations
}

func (fake *FakePlugin) recordInvocation(key string, args []interface{}) {
	fake.invocationsMutex.Lock()
	defer fake.invocationsMutex.Unlock()
	if fake.invocations == nil {
		fake.invocations = map[string][][]interface{}{}
	}
	if fake.invocations[key] == nil {
		fake.invocations[key] = [][]interface{}{}
	}
	fake.invocations[key] = append(fake.invocations[key], args)
}

var _ plugin.Plugin = new(FakePlugin)