package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/gocolly/colly/v2"
)

// Business represents a scraped business
type Business struct {
	Name     string `json:"name"`
	Address  string `json:"address"`
	Phone    string `json:"phone"`
	Website  string `json:"website"`
	Category string `json:"category"`
}

func main() {
	if len(os.Args) < 2 {
		log.Fatal("Usage: scraper <search-term>")
	}

	searchTerm := os.Args[1]
	url := fmt.Sprintf("https://www.google.com/maps/search/%s", strings.ReplaceAll(searchTerm, " ", "+"))

	// Create collector
	c := colly.NewCollector(
		colly.UserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"),
		colly.MaxDepth(1),
	)

	// Set timeouts
	c.SetRequestTimeout(30 * time.Second)

	var businesses []Business

	// On every div that contains business info
	c.OnHTML("[data-result-index]", func(e *colly.HTMLElement) {
		biz := Business{
			Name:     e.ChildText("h3, .fontHeadlineSmall"),
			Category: e.ChildText(".W4Efsd span:first-child"),
			Address:  e.ChildText(".W4Efsd span:nth-child(2)"),
			Phone:    e.ChildText("[data-tooltip=\"Copy phone number\"]"),
			Website:  e.ChildAttr("a[href^=\"http\"]", "href"),
		}

		if biz.Name != "" {
			businesses = append(businesses, biz)
			// Output immediately as JSON
			output := map[string]interface{}{
				"type": "business",
				"data": biz,
			}
			json.NewEncoder(os.Stdout).Encode(output)
		}
	})

	// Also try other selectors
	c.OnHTML("[role=\"article\"]", func(e *colly.HTMLElement) {
		text := e.Text
		lines := strings.Split(text, "\n")
		if len(lines) > 0 && lines[0] != "" {
			biz := Business{Name: strings.TrimSpace(lines[0])}
			businesses = append(businesses, biz)
			output := map[string]interface{}{
				"type": "business",
				"data": biz,
			}
			json.NewEncoder(os.Stdout).Encode(output)
		}
	})

	c.OnError(func(r *colly.Response, err error) {
		log.Printf("Error: %v", err)
	})

	// Visit the URL
	if err := c.Visit(url); err != nil {
		log.Fatal(err)
	}

	// Final output
	final := map[string]interface{}{
		"type":  "complete",
		"count": len(businesses),
	}
	json.NewEncoder(os.Stdout).Encode(final)
}
