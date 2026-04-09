package main

// Business represents a scraped business
type Business struct {
	CompanyName string `json:"company_name"`
	Website     string `json:"website"`
	Email       string `json:"email"`
	Category    string `json:"category"`
}

// ScraperConfig holds scraper configuration
type ScraperConfig struct {
	Query         string   `json:"query"`
	Location      string   `json:"location"`
	Workers       int      `json:"workers"`
	Timeout       int      `json:"timeout"`
	RetryAttempts int      `json:"retry_attempts"`
	Proxies       []string `json:"proxies"`
	MaxResults    *int     `json:"max_results"`
}

// OutputMessage represents a message to output
type OutputMessage struct {
	Type    string      `json:"type"`
	Data    interface{} `json:"data,omitempty"`
	Page    int         `json:"page,omitempty"`
	Message string      `json:"message,omitempty"`
}
