package main

import (
	"math/rand"
	"net/http"
	"net/url"
	"sync"
	"time"
)

// ProxyManager handles proxy rotation
type ProxyManager struct {
	proxies []string
	index   int
	mu      sync.Mutex
}

// NewProxyManager creates a new proxy manager
func NewProxyManager(proxies []string) *ProxyManager {
	return &ProxyManager{
		proxies: proxies,
		index:   0,
	}
}

// HasProxies returns true if proxies are available
func (pm *ProxyManager) HasProxies() bool {
	return len(pm.proxies) > 0
}

// GetNextProxy returns the next proxy in rotation
func (pm *ProxyManager) GetNextProxy() string {
	if !pm.HasProxies() {
		return ""
	}

	pm.mu.Lock()
	defer pm.mu.Unlock()

	proxy := pm.proxies[pm.index]
	pm.index = (pm.index + 1) % len(pm.proxies)
	return proxy
}

// GetRandomProxy returns a random proxy
func (pm *ProxyManager) GetRandomProxy() string {
	if !pm.HasProxies() {
		return ""
	}

	pm.mu.Lock()
	defer pm.mu.Unlock()

	return pm.proxies[rand.Intn(len(pm.proxies))]
}

// SetupProxy configures HTTP client with proxy
func SetupProxy(proxyURL string) (*http.Client, error) {
	if proxyURL == "" {
		return &http.Client{
			Timeout: 30 * time.Second,
		}, nil
	}

	parsedURL, err := url.Parse(proxyURL)
	if err != nil {
		return nil, err
	}

	transport := &http.Transport{
		Proxy: http.ProxyURL(parsedURL),
	}

	return &http.Client{
		Transport: transport,
		Timeout:   30 * time.Second,
	}, nil
}
