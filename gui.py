#!/usr/bin/env python3
"""
Google Maps Unlimited Scraper - Professional GUI Application
Modern desktop interface with real-time progress tracking.
"""
import asyncio
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Optional

import customtkinter as ctk
from PIL import Image

# Add orchestrator to path
sys.path.insert(0, str(Path(__file__).parent / "orchestrator"))

from config import PROXY_FILE, DEFAULT_WORKERS, OUTPUT_DIR
from csv_writer import CSVWriter
from email_finder import EmailFinder
from models import Business, SearchQuery, ScrapingConfig
from proxy_scraper import ProxyScraper
from gmaps_robust_scraper import GMapsRobustScraper

# Theme configuration
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ModernButton(ctk.CTkButton):
    """Custom styled button."""
    def __init__(self, master, text, command=None, width=140, height=40, **kwargs):
        super().__init__(
            master,
            text=text,
            command=command,
            width=width,
            height=height,
            font=("Inter", 14, "bold"),
            corner_radius=10,
            **kwargs
        )


class ModernEntry(ctk.CTkEntry):
    """Custom styled entry field."""
    def __init__(self, master, placeholder_text="", width=300, **kwargs):
        super().__init__(
            master,
            placeholder_text=placeholder_text,
            width=width,
            height=40,
            font=("Inter", 13),
            corner_radius=8,
            **kwargs
        )


class ModernLabel(ctk.CTkLabel):
    """Custom styled label."""
    def __init__(self, master, text, is_header=False, **kwargs):
        font_size = 16 if is_header else 13
        font_weight = "bold" if is_header else "normal"
        super().__init__(
            master,
            text=text,
            font=("Inter", font_size, font_weight),
            **kwargs
        )


class GoogleMapsScraperGUI(ctk.CTk):
    """Main GUI application."""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Google Maps Unlimited Scraper v1.0 - Professional Edition")
        self.geometry("1000x750")
        self.minsize(900, 650)
        
        # State
        self.scraping = False
        self.results_count = 0
        self.start_time = None
        
        # Create output directory
        OUTPUT_DIR.mkdir(exist_ok=True)
        
        # Build UI
        self._create_header()
        self._create_main_content()
        self._create_footer()
        
    def _create_header(self):
        """Create header section."""
        header = ctk.CTkFrame(self, height=70, corner_radius=0)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)
        
        # Title
        title = ctk.CTkLabel(
            header,
            text="Google Maps Unlimited Scraper",
            font=("Inter", 24, "bold")
        )
        title.pack(side="left", padx=30, pady=15)
        
        # Version badge
        version = ctk.CTkLabel(
            header,
            text="v1.0 Pro",
            font=("Inter", 12, "bold"),
            fg_color="green",
            text_color="white",
            corner_radius=15,
            width=80
        )
        version.pack(side="right", padx=30, pady=20)
        
    def _create_main_content(self):
        """Create main content area."""
        # Main container
        main = ctk.CTkFrame(self)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Left panel - Controls
        left_panel = ctk.CTkFrame(main, width=450)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        left_panel.pack_propagate(False)
        
        self._create_search_section(left_panel)
        self._create_settings_section(left_panel)
        self._create_proxy_section(left_panel)
        self._create_action_buttons(left_panel)
        
        # Right panel - Progress & Results
        right_panel = ctk.CTkFrame(main)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        self._create_progress_section(right_panel)
        self._create_stats_section(right_panel)
        self._create_log_section(right_panel)
        
    def _create_search_section(self, parent):
        """Create search input section."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=15, pady=(15, 10))
        
        ModernLabel(frame, "Search Parameters", is_header=True).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Search query
        ModernLabel(frame, "What to search for:").pack(anchor="w", padx=15, pady=(10, 5))
        self.query_entry = ModernEntry(frame, placeholder_text="e.g., restaurants, hotels, dentists")
        self.query_entry.pack(fill="x", padx=15, pady=(0, 10))
        
        # Location
        ModernLabel(frame, "Location:").pack(anchor="w", padx=15, pady=(10, 5))
        self.location_entry = ModernEntry(frame, placeholder_text="e.g., New York, London, Tokyo")
        self.location_entry.pack(fill="x", padx=15, pady=(0, 15))
        
    def _create_settings_section(self, parent):
        """Create settings section."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=15, pady=10)
        
        ModernLabel(frame, "Settings", is_header=True).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Workers
        row1 = ctk.CTkFrame(frame, fg_color="transparent")
        row1.pack(fill="x", padx=15, pady=5)
        
        ModernLabel(row1, "Workers:").pack(side="left")
        self.workers_var = ctk.IntVar(value=50)
        self.workers_slider = ctk.CTkSlider(
            row1,
            from_=10,
            to=100,
            number_of_steps=90,
            command=lambda v: self.workers_label.configure(text=f"{int(v)}")
        )
        self.workers_slider.set(50)
        self.workers_slider.pack(side="left", fill="x", expand=True, padx=10)
        self.workers_label = ctk.CTkLabel(row1, text="50", width=30)
        self.workers_label.pack(side="right")
        
        # Max results
        row2 = ctk.CTkFrame(frame, fg_color="transparent")
        row2.pack(fill="x", padx=15, pady=5)
        
        ModernLabel(row2, "Max Results:").pack(side="left")
        self.max_results_var = ctk.StringVar(value="Unlimited")
        self.max_results_entry = ctk.CTkEntry(
            row2,
            textvariable=self.max_results_var,
            width=120,
            placeholder_text="Unlimited"
        )
        self.max_results_entry.pack(side="right")
        
        # Output file
        row3 = ctk.CTkFrame(frame, fg_color="transparent")
        row3.pack(fill="x", padx=15, pady=10)
        
        ModernLabel(row3, "Output File:").pack(side="left")
        self.output_var = ctk.StringVar(value="results.csv")
        self.output_entry = ctk.CTkEntry(row3, textvariable=self.output_var, width=180)
        self.output_entry.pack(side="left", fill="x", expand=True, padx=10)
        
        ctk.CTkButton(
            row3,
            text="Browse",
            width=80,
            height=30,
            command=self._browse_output
        ).pack(side="right")
        
    def _create_proxy_section(self, parent):
        """Create proxy settings section."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=15, pady=10)
        
        ModernLabel(frame, "Proxy Configuration", is_header=True).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Proxy options
        self.use_proxies_var = ctk.BooleanVar(value=False)
        self.fetch_proxies_var = ctk.BooleanVar(value=True)
        
        ctk.CTkCheckBox(
            frame,
            text="Use Proxies",
            variable=self.use_proxies_var,
            font=("Inter", 12)
        ).pack(anchor="w", padx=15, pady=5)
        
        ctk.CTkCheckBox(
            frame,
            text="Auto-fetch Fresh Proxies (recommended)",
            variable=self.fetch_proxies_var,
            font=("Inter", 12)
        ).pack(anchor="w", padx=15, pady=5)
        
        # Proxy file button
        ctk.CTkButton(
            frame,
            text="Open proxies.txt",
            width=150,
            height=30,
            command=self._open_proxies_file
        ).pack(anchor="w", padx=15, pady=(10, 15))
        
    def _create_action_buttons(self, parent):
        """Create action buttons."""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=(20, 15))
        
        self.start_btn = ModernButton(
            frame,
            text="Start Scraping",
            command=self._start_scraping,
            width=200,
            height=50,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_btn.pack(pady=10)
        
        self.stop_btn = ModernButton(
            frame,
            text="Stop",
            command=self._stop_scraping,
            width=200,
            height=50,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_btn.pack(pady=10)
        
    def _create_progress_section(self, parent):
        """Create progress section."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=15, pady=(15, 10))
        
        ModernLabel(frame, "Progress", is_header=True).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Progress bar
        self.progress_var = ctk.DoubleVar(value=0)
        self.progress_bar = ctk.CTkProgressBar(
            frame,
            variable=self.progress_var,
            width=400,
            height=20,
            corner_radius=10
        )
        self.progress_bar.pack(fill="x", padx=15, pady=10)
        self.progress_bar.set(0)
        
        # Status label
        self.status_label = ModernLabel(frame, "Ready to start", text_color="gray")
        self.status_label.pack(anchor="w", padx=15, pady=(0, 15))
        
    def _create_stats_section(self, parent):
        """Create statistics section."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="x", padx=15, pady=10)
        
        ModernLabel(frame, "Statistics", is_header=True).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Stats grid
        stats_frame = ctk.CTkFrame(frame, fg_color="transparent")
        stats_frame.pack(fill="x", padx=15, pady=5)
        
        # Results count
        self.results_stat = self._create_stat_box(stats_frame, "Results", "0", 0)
        # Speed
        self.speed_stat = self._create_stat_box(stats_frame, "Speed", "0/min", 1)
        # Time
        self.time_stat = self._create_stat_box(stats_frame, "Elapsed", "00:00", 2)
        
    def _create_stat_box(self, parent, title, value, column):
        """Create a statistic box."""
        box = ctk.CTkFrame(parent, width=130, height=80, corner_radius=10)
        box.grid(row=0, column=column, padx=10, pady=5)
        box.grid_propagate(False)
        
        ctk.CTkLabel(box, text=title, font=("Inter", 11), text_color="gray").pack(pady=(10, 0))
        label = ctk.CTkLabel(box, text=value, font=("Inter", 20, "bold"))
        label.pack(pady=(5, 0))
        
        return label
        
    def _create_log_section(self, parent):
        """Create log/output section."""
        frame = ctk.CTkFrame(parent)
        frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        ModernLabel(frame, "Activity Log", is_header=True).pack(anchor="w", padx=15, pady=(15, 10))
        
        # Log text area
        self.log_text = ctk.CTkTextbox(
            frame,
            font=("Consolas", 11),
            wrap="word",
            corner_radius=8
        )
        self.log_text.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        self.log_text.configure(state="disabled")
        
    def _create_footer(self):
        """Create footer section."""
        footer = ctk.CTkFrame(self, height=40, corner_radius=0)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        
        ctk.CTkLabel(
            footer,
            text="Professional Desktop Edition | Hybrid Python/Go Architecture",
            font=("Inter", 11),
            text_color="gray"
        ).pack(side="left", padx=30, pady=10)
        
    def _browse_output(self):
        """Browse for output file."""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialdir=str(OUTPUT_DIR),
            initialfile=self.output_var.get()
        )
        if filename:
            self.output_var.set(Path(filename).name)
            
    def _open_proxies_file(self):
        """Open proxies.txt file."""
        if PROXY_FILE.exists():
            os.startfile(str(PROXY_FILE))
        else:
            PROXY_FILE.touch()
            os.startfile(str(PROXY_FILE))
            
    def _log(self, message: str, level: str = "info"):
        """Add message to log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        
        color = {
            "info": "white",
            "success": "green",
            "warning": "orange",
            "error": "red"
        }.get(level, "white")
        
        self.log_text.insert("end", f"[{timestamp}] ", "timestamp")
        self.log_text.insert("end", f"{message}\n", level)
        self.log_text.tag_config("timestamp", foreground="gray")
        self.log_text.tag_config(level, foreground=color)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")
        
    def _start_scraping(self):
        """Start scraping process."""
        # Validate inputs
        query = self.query_entry.get().strip()
        location = self.location_entry.get().strip()
        
        if not query or not location:
            messagebox.showerror("Validation Error", "Please enter both search query and location.")
            return
            
        # Update UI state
        self.scraping = True
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.results_count = 0
        self.start_time = time.time()
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_bar.set(0)
        self.status_label.configure(text="Initializing...", text_color="yellow")
        
        # Clear log
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")
        
        self._log(f"Starting scrape: {query} in {location}", "info")
        
        # Start in thread
        thread = threading.Thread(target=self._scrape_thread, args=(query, location))
        thread.daemon = True
        thread.start()
        
        # Start UI update
        self._update_ui()
        
    def _scrape_thread(self, query: str, location: str):
        """Scraping thread."""
        try:
            asyncio.run(self._run_scraper(query, location))
        except Exception as e:
            self.after(0, lambda: self._log(f"Error: {str(e)}", "error"))
        finally:
            self.after(0, self._scraping_finished)
            
    async def _run_scraper(self, query: str, location: str):
        """Run the scraper using Playwright."""
        # Fetch proxies if requested
        if self.fetch_proxies_var.get():
            self.after(0, lambda: self._log("Fetching fresh proxies...", "info"))
            proxy_scraper = ProxyScraper()
            proxies = await proxy_scraper.fetch_all_proxies()
            if proxies:
                count = proxy_scraper.save_to_file(str(PROXY_FILE))
                self.after(0, lambda: self._log(f"Saved {count} fresh proxies", "success"))
                self.use_proxies_var.set(True)
            else:
                self.after(0, lambda: self._log("Failed to fetch proxies, continuing without", "warning"))
        
        # Prepare config
        max_results_str = self.max_results_var.get()
        max_results = None if max_results_str in ["", "Unlimited"] else int(max_results_str)
        
        output_file = self.output_var.get()
        csv_writer = CSVWriter(output_file)
        email_finder = EmailFinder()
        
        # Load proxies
        proxy_list = []
        if self.use_proxies_var.get() and PROXY_FILE.exists():
            with open(PROXY_FILE, 'r') as f:
                proxy_list = [line.strip() for line in f if line.strip()]
            self.after(0, lambda: self._log(f"Loaded {len(proxy_list)} proxies", "info"))
        
        self.after(0, lambda: self._log("Starting Google Maps scraper...", "info"))
        self.after(0, lambda: self.status_label.configure(text="Scraping Google Maps...", text_color="green"))
        
        # Create robust Google Maps scraper
        scraper = GMapsRobustScraper(proxy_list=proxy_list if self.use_proxies_var.get() else None)
        
        # Progress callback
        def progress_callback(type_, data):
            if type_ == "status":
                self.after(0, lambda d=data: self._log(d, "info"))
            elif type_ == "business":
                business = data
                self.after(0, lambda b=business: self._log(f"Found: {b.company_name}", "success"))
            elif type_ == "count":
                self.results_count = data
        
        try:
            # Run scraper
            businesses = await scraper.scrape(
                query=query,
                location=location,
                max_results=max_results,
                progress_callback=progress_callback
            )
            
            # Process results - extract emails and save to CSV
            for business in businesses:
                if business.website and not business.email:
                    business.email = await email_finder.extract_from_website(business.website)
                csv_writer.write_business(business)
                self.results_count += 1
            
            # Show stats
            stats = csv_writer.get_stats()
            self.after(0, lambda: self._log(f"Scraping complete! Total: {stats['rows']} businesses", "success"))
            self.after(0, lambda: self._log(f"Output saved to: {csv_writer.filepath}", "info"))
            
        except Exception as e:
            self.after(0, lambda: self._log(f"Error during scraping: {str(e)}", "error"))
            raise
        
    def _update_ui(self):
        """Update UI during scraping."""
        if not self.scraping:
            return
            
        # Update stats
        self.results_stat.configure(text=str(self.results_count))
        
        if self.start_time:
            elapsed = int(time.time() - self.start_time)
            mins, secs = divmod(elapsed, 60)
            self.time_stat.configure(text=f"{mins:02d}:{secs:02d}")
            
            if elapsed > 0:
                speed = self.results_count / elapsed * 60
                self.speed_stat.configure(text=f"{int(speed)}/min")
        
        # Pulse progress bar
        current = self.progress_var.get()
        if current >= 1:
            self.progress_var.set(0)
        else:
            self.progress_var.set(current + 0.01)
            
        self.after(100, self._update_ui)
        
    def _scraping_finished(self):
        """Called when scraping finishes."""
        self.scraping = False
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.status_label.configure(text="Ready", text_color="gray")
        self.progress_bar.set(1)
        self.progress_var.set(1)
        
        # Show completion dialog
        messagebox.showinfo(
            "Scraping Complete",
            f"Successfully scraped {self.results_count} businesses!\n\nOutput saved to: {OUTPUT_DIR / self.output_var.get()}"
        )
        
    def _stop_scraping(self):
        """Stop scraping process."""
        self.scraping = False
        self._log("Scraping stopped by user", "warning")
        self._scraping_finished()


def main():
    """Main entry point."""
    app = GoogleMapsScraperGUI()
    app.mainloop()


if __name__ == "__main__":
    main()
