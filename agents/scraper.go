package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"regexp"
	"strings"
	"sync"
	"time"
)

// GoogleMapsScraper handles Google Maps scraping
type GoogleMapsScraper struct {
	config       ScraperConfig
	proxyManager *ProxyManager
	results      chan Business
	seen         map[string]bool
	mu           sync.RWMutex
}

// NewGoogleMapsScraper creates a new scraper
func NewGoogleMapsScraper(config ScraperConfig) *GoogleMapsScraper {
	return &GoogleMapsScraper{
		config:       config,
		proxyManager: NewProxyManager(config.Proxies),
		results:      make(chan Business, 1000),
		seen:         make(map[string]bool),
	}
}

// Scrape performs the scraping operation
func (s *GoogleMapsScraper) Scrape() ([]Business, error) {
	// Use HTTP client fallback method
	err := s.ScrapeWithFallback()
	if err != nil {
		return nil, err
	}

	// Collect results
	var businesses []Business
	for business := range s.results {
		businesses = append(businesses, business)
	}

	return businesses, nil
}

// buildSearchURL creates the Google Maps search URL
func (s *GoogleMapsScraper) buildSearchURL() string {
	searchTerm := fmt.Sprintf("%s %s", s.config.Query, s.config.Location)
	encoded := strings.ReplaceAll(searchTerm, " ", "+")
	return fmt.Sprintf("https://www.google.com/maps/search/%s", encoded)
}

// outputBusiness outputs a business to stdout
func (s *GoogleMapsScraper) outputBusiness(business Business) {
	// Check for duplicates
	s.mu.Lock()
	defer s.mu.Unlock()

	if !s.seen[business.CompanyName] && business.CompanyName != "" {
		s.seen[business.CompanyName] = true

		// Output business as JSON
		msg := OutputMessage{
			Type: "business",
			Data: business,
		}
		json.NewEncoder(os.Stdout).Encode(msg)
	}
}

// scrapePages scrapes multiple pages using HTTP client
func (s *GoogleMapsScraper) scrapePages(baseURL string) error {
	return s.ScrapeWithFallback()
}

// extractEmail attempts to extract email from text
func extractEmail(text string) string {
	emailRegex := regexp.MustCompile(`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`)
	matches := emailRegex.FindString(text)
	return matches
}

// ScrapeWithFallback uses HTTP client as fallback
func (s *GoogleMapsScraper) ScrapeWithFallback() error {
	searchURL := s.buildSearchURL()

	client := &http.Client{
		Timeout: time.Duration(s.config.Timeout) * time.Second,
	}

	// Try with proxy
	if s.proxyManager.HasProxies() {
		proxy := s.proxyManager.GetNextProxy()
		if pc, err := SetupProxy(proxy); err == nil {
			client = pc
		}
	}

	req, err := http.NewRequest("GET", searchURL, nil)
	if err != nil {
		return err
	}

	req.Header.Set("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
	req.Header.Set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8")
	req.Header.Set("Accept-Language", "en-US,en;q=0.9")

	resp, err := client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP status: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return err
	}

	// Parse and extract
	htmlContent := string(body)
	s.parseBusinessesFromHTML(htmlContent)

	return nil
}

// parseBusinessesFromHTML parses business data from HTML content
func (s *GoogleMapsScraper) parseBusinessesFromHTML(html string) {
	// Simple regex-based extraction as fallback
	nameRegex := regexp.MustCompile(`"name":"([^"]+)"`)
	urlRegex := regexp.MustCompile(`"website":"([^"]+)"`)
	categoryRegex := regexp.MustCompile(`"category":"([^"]+)"`)

	names := nameRegex.FindAllStringSubmatch(html, -1)
	urls := urlRegex.FindAllStringSubmatch(html, -1)
	categories := categoryRegex.FindAllStringSubmatch(html, -1)

	for i, name := range names {
		if len(name) > 1 {
			business := Business{
				CompanyName: name[1],
			}

			if i < len(urls) && len(urls[i]) > 1 {
				business.Website = urls[i][1]
			}

			if i < len(categories) && len(categories[i]) > 1 {
				business.Category = categories[i][1]
			}

			s.results <- business
		}
	}
}
