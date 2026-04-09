package main

import (
	"encoding/json"
	"io"
	"os"
	"time"
)

func main() {
	// Read config from stdin
	configData, err := io.ReadAll(os.Stdin)
	if err != nil {
		outputError("Failed to read config: " + err.Error())
		os.Exit(1)
	}

	var config ScraperConfig
	if err := json.Unmarshal(configData, &config); err != nil {
		outputError("Failed to parse config: " + err.Error())
		os.Exit(1)
	}

	// Set defaults
	if config.Workers == 0 {
		config.Workers = 50
	}
	if config.Timeout == 0 {
		config.Timeout = 30
	}
	if config.RetryAttempts == 0 {
		config.RetryAttempts = 3
	}

	// Create and run scraper
	scraper := NewGoogleMapsScraper(config)

	// Run scraping
	err = scraper.ScrapeWithFallback()
	if err != nil {
		outputError("Scraping failed: " + err.Error())
		os.Exit(1)
	}

	// Wait a bit for remaining results
	time.Sleep(2 * time.Second)

	// Output completion
	msg := OutputMessage{
		Type:    "complete",
		Message: "Scraping completed successfully",
	}
	json.NewEncoder(os.Stdout).Encode(msg)
}

func outputError(message string) {
	msg := OutputMessage{
		Type:    "error",
		Message: message,
	}
	json.NewEncoder(os.Stdout).Encode(msg)
}
