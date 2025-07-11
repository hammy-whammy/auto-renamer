#!/usr/bin/env python3
"""
PDF Invoice Renamer Script
Automatically renames PDF invoices based on their content using the format:
Site-Collecte-InvoiceMonthYear-InvoiceNumber
"""

import os
import re
import json
import logging
import time
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import PyPDF2
import google.generativeai as genai
import argparse
from dotenv import load_dotenv
import pandas as pd
from difflib import SequenceMatcher
import unicodedata

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProcessingLogger:
    """Enhanced logger for PDF processing with structured output and detailed reporting."""
    
    def __init__(self, log_dir: str = "logs", enable_file_logging: bool = True):
        self.log_dir = Path(log_dir)
        self.enable_file_logging = enable_file_logging
        self.processing_results = []
        self.session_stats = {
            'start_time': datetime.now(),
            'total_files': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'api_requests_used': 0
        }
        
        if self.enable_file_logging:
            self.log_dir.mkdir(exist_ok=True)
            self.setup_file_logging()
    
    def setup_file_logging(self):
        """Setup structured file logging."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"pdf_renaming_{timestamp}.log"
        self.json_log_file = self.log_dir / f"pdf_renaming_{timestamp}.json"
        
        # Create file handler with custom formatter
        self.file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        self.file_handler.setLevel(logging.INFO)
        
        # Custom formatter for readable logs
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.file_handler.setFormatter(formatter)
        
        # Add to existing logger
        logger.addHandler(self.file_handler)
        
        self.log_session_start()
    
    def log_session_start(self):
        """Log session start information."""
        logger.info("=" * 80)
        logger.info("PDF INVOICE RENAMING SESSION STARTED")
        logger.info("=" * 80)
        logger.info(f"Session ID: {datetime.now().strftime('%Y%m%d_%H%M%S')}")
        if self.enable_file_logging:
            logger.info(f"Log file: {self.log_file}")
            logger.info(f"JSON report: {self.json_log_file}")
    
    def log_processing_start(self, pdf_count: int, directory: str, dry_run: bool, rate_limit_status: Dict):
        """Log processing start details."""
        mode = "DRY RUN" if dry_run else "LIVE"
        self.session_stats['total_files'] = pdf_count
        
        logger.info("-" * 80)
        logger.info(f"PROCESSING START - {mode} MODE")
        logger.info("-" * 80)
        logger.info(f"Directory: {directory}")
        logger.info(f"PDF files found: {pdf_count}")
        logger.info(f"Mode: {mode}")
        logger.info(f"API quota: {rate_limit_status['requests_today']}/{rate_limit_status['max_per_day']} used today")
        logger.info(f"Remaining requests: {rate_limit_status['remaining_today']}")
        
        if pdf_count > rate_limit_status['remaining_today']:
            logger.warning(f"⚠️  WARNING: Found {pdf_count} PDFs but only {rate_limit_status['remaining_today']} API requests remaining!")
    
    def log_file_processing_start(self, filename: str, file_index: int, total_files: int):
        """Log individual file processing start."""
        logger.info("-" * 50)
        logger.info(f"Processing file {file_index}/{total_files}: {filename}")
    
    def log_file_success(self, original_name: str, new_name: str, extracted_data: Dict, dry_run: bool):
        """Log successful file processing."""
        action = "Would rename" if dry_run else "Renamed"
        logger.info(f"✅ SUCCESS: {action} '{original_name}' → '{new_name}'")
        
        # Log extracted information
        if extracted_data:
            logger.info(f"   📊 Extracted data:")
            if 'restaurant_name' in extracted_data:
                logger.info(f"     Restaurant: {extracted_data['restaurant_name']}")
            if 'site_number' in extracted_data:
                logger.info(f"     Site: {extracted_data['site_number']}")
            if 'collecte' in extracted_data:
                logger.info(f"     Collecte: {extracted_data['collecte']}")
            if 'invoice_number' in extracted_data:
                logger.info(f"     Invoice #: {extracted_data['invoice_number']}")
            if 'invoice_date' in extracted_data:
                logger.info(f"     Date: {extracted_data['invoice_date']}")
        
        self.session_stats['successful'] += 1
        self.processing_results.append({
            'status': 'success',
            'original_name': original_name,
            'new_name': new_name,
            'extracted_data': extracted_data,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_file_failure(self, filename: str, reason: str, details: Dict = None):
        """Log file processing failure with detailed reason."""
        logger.error(f"❌ FAILED: {filename}")
        logger.error(f"   Reason: {reason}")
        
        if details:
            logger.error(f"   Details:")
            for key, value in details.items():
                logger.error(f"     {key}: {value}")
        
        self.session_stats['failed'] += 1
        self.processing_results.append({
            'status': 'failed',
            'filename': filename,
            'reason': reason,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        })
    
    def log_file_skipped(self, filename: str, reason: str):
        """Log skipped file with reason."""
        logger.warning(f"⏭️  SKIPPED: {filename}")
        logger.warning(f"   Reason: {reason}")
        
        self.session_stats['skipped'] += 1
        self.processing_results.append({
            'status': 'skipped',
            'filename': filename,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_api_request(self, filename: str, success: bool, response_data: Dict = None):
        """Log API request details."""
        if success:
            logger.info(f"   🔄 API request successful for {filename}")
            self.session_stats['api_requests_used'] += 1
        else:
            logger.error(f"   🔄 API request failed for {filename}")
            if response_data:
                logger.error(f"   Error details: {response_data}")
    
    def log_rate_limit_wait(self, wait_time: float, reason: str):
        """Log rate limiting wait."""
        logger.warning(f"⏳ Rate limit reached: {reason}")
        logger.warning(f"   Waiting {wait_time:.1f} seconds...")
    
    def log_session_end(self, final_rate_status: Dict):
        """Log session end with comprehensive summary."""
        end_time = datetime.now()
        duration = end_time - self.session_stats['start_time']
        
        logger.info("=" * 80)
        logger.info("PROCESSING SESSION COMPLETED")
        logger.info("=" * 80)
        logger.info(f"Duration: {duration}")
        logger.info(f"Total files processed: {self.session_stats['total_files']}")
        logger.info(f"✅ Successful: {self.session_stats['successful']}")
        logger.info(f"❌ Failed: {self.session_stats['failed']}")
        logger.info(f"⏭️  Skipped: {self.session_stats['skipped']}")
        logger.info(f"🔄 API requests used: {self.session_stats['api_requests_used']}")
        logger.info(f"📊 Final API quota: {final_rate_status['requests_today']}/{final_rate_status['max_per_day']}")
        logger.info(f"🔋 Remaining requests: {final_rate_status['remaining_today']}")
        
        if self.session_stats['failed'] > 0:
            logger.info("\n📋 FAILURE SUMMARY:")
            for result in self.processing_results:
                if result['status'] == 'failed':
                    logger.info(f"   • {result['filename']}: {result['reason']}")
        
        if self.session_stats['skipped'] > 0:
            logger.info("\n📋 SKIPPED FILES SUMMARY:")
            for result in self.processing_results:
                if result['status'] == 'skipped':
                    logger.info(f"   • {result['filename']}: {result['reason']}")
        
        # Save detailed JSON report
        if self.enable_file_logging:
            self.save_json_report(end_time, duration)
        
        logger.info("=" * 80)
    
    def save_json_report(self, end_time: datetime, duration: timedelta):
        """Save detailed JSON report."""
        # Prepare summary stats with serializable data
        summary_stats = self.session_stats.copy()
        summary_stats['start_time'] = self.session_stats['start_time'].isoformat()
        
        report = {
            'session_info': {
                'start_time': self.session_stats['start_time'].isoformat(),
                'end_time': end_time.isoformat(),
                'duration_seconds': duration.total_seconds(),
                'session_id': datetime.now().strftime('%Y%m%d_%H%M%S')
            },
            'summary': summary_stats,
            'detailed_results': self.processing_results
        }
        
        try:
            with open(self.json_log_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            logger.info(f"📄 Detailed JSON report saved: {self.json_log_file}")
        except Exception as e:
            logger.error(f"Failed to save JSON report: {e}")
    
    def cleanup(self):
        """Cleanup logging handlers."""
        if hasattr(self, 'file_handler'):
            logger.removeHandler(self.file_handler)
            self.file_handler.close()

class PersistentRateLimiter:
    """
    Persistent rate limiter that stores usage data across program runs.
    Respects Google Gemini API limits with local file persistence.
    """
    
    def __init__(self, max_per_minute: int = 1000, max_per_day: int = 10000, storage_file: str = ".api_usage.json"):
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self.storage_file = Path(storage_file)
        self.verbose = os.getenv('RATE_LIMIT_VERBOSE', 'false').lower() == 'true'
        
        # Load persistent data
        self.usage_data = self._load_usage_data()
        self._cleanup_old_data()
        
    def _load_usage_data(self) -> Dict:
        """Load usage data from persistent storage."""
        default_data = {
            'daily_requests': {},
            'minute_requests': [],
            'last_updated': datetime.now().isoformat()
        }
        
        if not self.storage_file.exists():
            self._save_usage_data(default_data)
            return default_data
            
        try:
            with open(self.storage_file, 'r') as f:
                data = json.load(f)
                # Ensure all required keys exist
                for key in default_data:
                    if key not in data:
                        data[key] = default_data[key]
                return data
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Could not load usage data: {e}. Starting fresh.")
            self._save_usage_data(default_data)
            return default_data
    
    def _save_usage_data(self, data: Dict = None):
        """Save usage data to persistent storage."""
        try:
            save_data = data or self.usage_data
            save_data['last_updated'] = datetime.now().isoformat()
            with open(self.storage_file, 'w') as f:
                json.dump(save_data, f, indent=2)
        except IOError as e:
            logger.error(f"Could not save usage data: {e}")
    
    def _cleanup_old_data(self):
        """Remove old usage data to keep file size manageable."""
        now = datetime.now()
        today_str = now.date().isoformat()
        
        # Keep only last 7 days of daily data
        cutoff_date = (now - timedelta(days=7)).date().isoformat()
        
        # Clean daily requests
        old_keys = [date_str for date_str in self.usage_data['daily_requests'].keys() 
                   if date_str < cutoff_date]
        for old_key in old_keys:
            del self.usage_data['daily_requests'][old_key]
        
        # Clean minute requests (keep only last hour)
        hour_ago = now - timedelta(hours=1)
        hour_ago_iso = hour_ago.isoformat()
        
        self.usage_data['minute_requests'] = [
            req_time for req_time in self.usage_data['minute_requests']
            if req_time > hour_ago_iso
        ]
        
        # Save cleaned data
        self._save_usage_data()
    
    def _get_today_requests(self) -> int:
        """Get number of requests made today."""
        today_str = datetime.now().date().isoformat()
        return self.usage_data['daily_requests'].get(today_str, 0)
    
    def _get_minute_requests(self) -> List[datetime]:
        """Get list of requests made in the last minute."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Convert stored ISO strings back to datetime objects for recent requests
        recent_requests = []
        for req_time_str in self.usage_data['minute_requests']:
            try:
                req_time = datetime.fromisoformat(req_time_str)
                if req_time > minute_ago:
                    recent_requests.append(req_time)
            except ValueError:
                continue  # Skip invalid dates
        
        return recent_requests
        
    def wait_if_needed(self, processing_logger=None):
        """Wait if necessary to respect rate limits."""
        now = datetime.now()
        today_str = now.date().isoformat()
        
        # Check daily limit
        today_requests = self._get_today_requests()
        if today_requests >= self.max_per_day:
            logger.warning(f"Daily limit of {self.max_per_day} requests reached. Please try again tomorrow.")
            raise Exception(f"Daily API limit reached ({self.max_per_day} requests)")
        
        # Check per-minute limit
        minute_requests = self._get_minute_requests()
        if len(minute_requests) >= self.max_per_minute:
            sleep_time = 60 - (now - minute_requests[0]).total_seconds()
            if sleep_time > 0:
                if processing_logger:
                    processing_logger.log_rate_limit_wait(sleep_time, f"Used {len(minute_requests)}/{self.max_per_minute} requests this minute")
                else:
                    logger.info(f"Rate limit: waiting {sleep_time:.1f} seconds (used {len(minute_requests)}/{self.max_per_minute} requests this minute)")
                time.sleep(sleep_time)
                # Refresh minute requests after waiting
                minute_requests = self._get_minute_requests()
        
        # Record this request
        self.usage_data['minute_requests'].append(now.isoformat())
        self.usage_data['daily_requests'][today_str] = today_requests + 1
        
        # Save updated data
        self._save_usage_data()
        
        if self.verbose:
            logger.info(f"API request #{today_requests + 1} today, {len(minute_requests) + 1} this minute")
    
    def get_status(self) -> Dict:
        """Get current rate limiting status."""
        today_requests = self._get_today_requests()
        minute_requests = self._get_minute_requests()
        
        # Get historical data for context
        historical_data = []
        for date_str, count in sorted(self.usage_data['daily_requests'].items())[-7:]:  # Last 7 days
            historical_data.append({
                'date': date_str,
                'requests': count
            })
        
        return {
            'requests_today': today_requests,
            'max_per_day': self.max_per_day,
            'requests_this_minute': len(minute_requests),
            'max_per_minute': self.max_per_minute,
            'remaining_today': self.max_per_day - today_requests,
            'remaining_this_minute': self.max_per_minute - len(minute_requests),
            'historical_usage': historical_data,
            'total_lifetime_requests': sum(self.usage_data['daily_requests'].values())
        }
    
    def reset_today_count(self):
        """Reset today's count (useful for testing or if you know the count is wrong)."""
        today_str = datetime.now().date().isoformat()
        self.usage_data['daily_requests'][today_str] = 0
        self._save_usage_data()
        logger.info("Today's request count has been reset to 0")
    
    def get_weekly_summary(self) -> Dict:
        """Get a summary of API usage for the past week."""
        now = datetime.now()
        
        weekly_total = 0
        daily_breakdown = []
        
        # Get last 7 days including today
        for i in range(7):
            date = (now - timedelta(days=6-i)).date()  # Start from 6 days ago to today
            date_str = date.isoformat()
            count = self.usage_data['daily_requests'].get(date_str, 0)
            weekly_total += count
            daily_breakdown.append({
                'date': date_str,
                'day_name': date.strftime('%A'),
                'requests': count
            })
        
        return {
            'weekly_total': weekly_total,
            'daily_breakdown': daily_breakdown,
            'average_per_day': weekly_total / 7
        }

# Backward compatibility alias
RateLimiter = PersistentRateLimiter

class PDFRenamer:
    def __init__(self, api_key: str = None, csv_dir: str = ".", enable_detailed_logging: bool = True):
        """Initialize the PDF renamer with API key and CSV directory."""
        # Get API key from parameter or environment
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key or api_key == 'your_api_key_here':
            raise ValueError("Please set your Gemini API key in the .env file or pass it as a parameter")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')
        self.csv_dir = Path(csv_dir)
        
        # Initialize enhanced logging
        self.processing_logger = ProcessingLogger(enable_file_logging=enable_detailed_logging)
        
        # Initialize persistent rate limiter for Gemini 2.5 Flash
        max_per_minute = 1000
        max_per_day = 10000
        self.rate_limiter = PersistentRateLimiter(max_per_minute, max_per_day)
        
        logger.info(f"Rate limiter initialized: {max_per_minute}/minute, {max_per_day}/day (Gemini 2.5 Flash tier)")
        
        # Show current usage on startup
        status = self.rate_limiter.get_status()
        logger.info(f"Current usage: {status['requests_today']}/{status['max_per_day']} requests today")
        
        # Load data from CSV files
        self.restaurants_data = self._load_restaurants_data()
        self.prestataires_data = self._load_prestataires_data()
        self.valid_collectors = self._load_valid_collectors()

        # Define provider aliases to map subsidiaries to their parent company
        self.provider_aliases = {
            'COVED': 'PAPREC',
            'IDDEE 13 SAS': 'ELISE',
            'ELISE MEDITERRANEE': 'ELISE'
            # Add other aliases here in the future, e.g., 'SUBSIDIARY': 'PARENT'
        }
        if self.provider_aliases:
            logger.info(f"Loaded {len(self.provider_aliases)} provider aliases: {self.provider_aliases}")
        
        # Create lookup dictionaries for faster matching
        self.restaurant_lookup = self._create_restaurant_lookup()
        
    def _normalize_text(self, text: str) -> str:
        """Normalize text by lowercasing, removing accents, and stripping extra whitespace."""
        if not text:
            return ""
        
        # NFD form separates characters from their accents
        # Then we remove combining marks (the accents)
        text = ''.join(c for c in unicodedata.normalize('NFD', text) 
                       if unicodedata.category(c) != 'Mn')
        
        return text.lower().strip()

    def _load_restaurants_data(self) -> List[Dict]:
        """Load restaurant data from Excel file only."""
        restaurants = []
        excel_path = self.csv_dir / "Liste des clients.xlsx"
        
        try:
            # Load Excel file
            df = pd.read_excel(excel_path)
            
            # Handle column spacing issues and normalize column names
            df.columns = df.columns.str.strip()
            
            # Expected columns: Code client, Nom, Adresse, CP
            # Map to our expected format
            for _, row in df.iterrows():
                # Handle "Code client " with trailing space
                site_number = row.get('Code client') or row.get('Code client ')
                restaurant_name = row.get('Nom', '').strip()
                address = row.get('Adresse', '').strip()
                postal_code = row.get('CP', '')
                
                if pd.notna(site_number) and pd.notna(restaurant_name):
                    restaurants.append({
                        'Site': str(int(site_number)),  # Convert to string, remove decimal
                        'Nom': restaurant_name,
                        'Adresse': address,
                        'CP': str(postal_code).strip() if pd.notna(postal_code) else ''
                    })
            
            logger.info(f"Loaded {len(restaurants)} restaurant entries from Excel")
            return restaurants
            
        except Exception as e:
            logger.error(f"Critical error loading Excel file {excel_path}: {e}")
            logger.error("Excel file is required - CSV fallback has been deprecated")
            raise RuntimeError(f"Could not load required Excel file: {excel_path}. Please ensure the file exists and is accessible.")
    

    
    def _load_prestataires_data(self) -> Dict[str, List[str]]:
        """Load prestataires data from CSV file."""
        prestataires = {}
        csv_path = self.csv_dir / "Prestataires.csv"
        
        with open(csv_path, 'r', encoding='utf-8-sig') as file:  # Handle BOM
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                collecte = row['Collecte'].strip()
                combinations = [combo.strip() for combo in row['Combinations'].split(',')]
                prestataires[collecte] = combinations
        
        logger.info(f"Loaded prestataires data for {len(prestataires)} collecte types")
        return prestataires
    
    def _load_valid_collectors(self) -> set:
        """Load valid collector names from Prestataires.csv for validation."""
        valid_collectors = set()
        csv_path = self.csv_dir / "Prestataires.csv"
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as file:
                reader = csv.DictReader(file, delimiter=';')
                for row in reader:
                    collecte = row['Collecte'].strip()
                    if collecte:  # Skip empty rows
                        valid_collectors.add(collecte)
            
            logger.info(f"Loaded {len(valid_collectors)} valid collectors for validation")
            return valid_collectors
            
        except Exception as e:
            logger.error(f"Error loading valid collectors: {e}")
            return set()
    
    def _validate_collector(self, extracted_collector: str, base_collector: str) -> bool:
        """Validate that the base collector is in our valid collectors list."""
        if base_collector not in self.valid_collectors:
            logger.warning(f"❌ Invalid collector '{base_collector}' extracted from '{extracted_collector}'")
            logger.info(f"📋 Valid collectors: {sorted(list(self.valid_collectors))}")
            return False
        
        logger.info(f"✅ Collector '{base_collector}' is valid")
        return True
    
    def _extract_valid_collectors(self) -> List[str]:
        """Extract unique collectors from Prestataires.csv for validation."""
        return list(self.prestataires_data.keys())
    
    def _normalize_address(self, address: str) -> str:
        """Normalize address for matching by handling common abbreviations."""
        if not address:
            return ""
        
        address = address.lower().strip()
        
        # Common French address normalizations
        address_mappings = {
            'avenue': 'av',
            'av.': 'av',
            'boulevard': 'bd',
            'bd.': 'bd',
            'rue': 'r',
            'place': 'pl',
            'pl.': 'pl',
            'saint': 'st',
            'sainte': 'ste',
            'st.': 'st',
            'ste.': 'ste'
        }
        
        # Apply normalizations
        for full_form, abbrev in address_mappings.items():
            address = re.sub(r'\b' + full_form + r'\b', abbrev, address)
        
        # Remove extra spaces and punctuation
        address = re.sub(r'[^\w\s]', '', address)
        address = re.sub(r'\s+', ' ', address).strip()
        
        return address
    
    def _calculate_address_similarity(self, addr1: str, addr2: str) -> float:
        """Calculate similarity between two addresses."""
        norm_addr1 = self._normalize_address(addr1)
        norm_addr2 = self._normalize_address(addr2)
        
        if not norm_addr1 or not norm_addr2:
            return 0.0
        
        # Use sequence matcher for similarity
        return SequenceMatcher(None, norm_addr1, norm_addr2).ratio()
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two restaurant names."""
        if not name1 or not name2:
            return 0.0
        
        # Normalize names for comparison
        norm_name1 = name1.lower().strip()
        norm_name2 = name2.lower().strip()
        
        # Direct similarity using sequence matcher
        return SequenceMatcher(None, norm_name1, norm_name2).ratio()
    
    def _find_address_matches(self, restaurant_name: str, address: str, threshold: float = 0.7) -> List[Dict]:
        """Find restaurants matching both name and address with fallback to address-only matching."""
        matches = []
        
        # First try exact name matches with address validation
        for restaurant in self.restaurants_data:
            if self._is_similar_restaurant_name(restaurant_name.lower(), restaurant['Nom'].lower()):
                addr_similarity = self._calculate_address_similarity(address, restaurant.get('Adresse', ''))
                if addr_similarity >= threshold:
                    matches.append({
                        'restaurant': restaurant,
                        'address_similarity': addr_similarity,
                        'match_type': 'name_and_address'
                    })
        
        # If no good matches, try address-only matching for same name restaurants
        if not matches:
            name_matches = []
            for restaurant in self.restaurants_data:
                if self._is_similar_restaurant_name(restaurant_name.lower(), restaurant['Nom'].lower()):
                    name_matches.append(restaurant)
            
            # If multiple restaurants with same name, try to match by address
            if len(name_matches) > 1:
                for restaurant in name_matches:
                    addr_similarity = self._calculate_address_similarity(address, restaurant.get('Adresse', ''))
                    if addr_similarity >= 0.5:  # Lower threshold for fallback
                        matches.append({
                            'restaurant': restaurant,
                            'address_similarity': addr_similarity,
                            'match_type': 'address_fallback'
                        })
        
        # Sort by address similarity (best matches first)
        matches.sort(key=lambda x: x['address_similarity'], reverse=True)
        return matches
    
    def _create_restaurant_lookup(self) -> Dict[str, List[Dict]]:
        """Create a lookup dictionary for faster restaurant matching."""
        lookup = {}
        
        for restaurant in self.restaurants_data:
            # Excel structure (Excel file has 'Nom' field)
            restaurant_name = restaurant['Nom'].lower()
            
            # Create various normalized versions for McDonald's variations
            normalized_names = self._normalize_restaurant_name(restaurant_name)
            
            for name in normalized_names:
                if name not in lookup:
                    lookup[name] = []
                lookup[name].append(restaurant)
        
        return lookup
    
    def _normalize_restaurant_name(self, name: str) -> List[str]:
        """Generate normalized versions of restaurant names for matching."""
        name = name.lower().strip()
        variations = [name]
        
        # Handle McDonald's variations
        if any(variant in name for variant in ['mcdonald', 'mac do', 'macdonald']):
            # Extract location part
            location_patterns = [
                r"mcdonald'?s?\s+(.+)",
                r"mac\s*do\s+(.+)",
                r"macdonald'?s?\s+(.+)"
            ]
            
            location = ""
            for pattern in location_patterns:
                match = re.search(pattern, name, re.IGNORECASE)
                if match:
                    location = match.group(1).strip()
                    break
            
            if location:
                # Generate various McDonald's format variations
                variations.extend([
                    f"mcdonald's {location}",
                    f"mcdonalds {location}",
                    f"mac do {location}",
                    f"macdonald's {location}",
                    f"macdonalds {location}",
                    location  # Just the location name
                ])
        
        # Clean up common variations
        cleaned_variations = []
        for var in variations:
            # Remove extra spaces and normalize
            cleaned = re.sub(r'\s+', ' ', var).strip()
            cleaned_variations.append(cleaned)
            
            # Also add version without apostrophes
            if "'" in cleaned:
                cleaned_variations.append(cleaned.replace("'", ""))
        
        return list(set(cleaned_variations))
    
    def _extract_pdf_text(self, pdf_path: Path) -> str:
        """Extract text from the first page of a PDF."""
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                if len(reader.pages) > 0:
                    return reader.pages[0].extract_text()
                return ""
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            return ""
    
    def _analyze_invoice_with_gemini(self, pdf_path: Path, filename: str = "unknown") -> Dict:
        """Use Gemini to analyze invoice content and extract key information."""
        prompt = """
        Analyze this French invoice PDF and extract the following information in JSON format:
        
        1. entreprise: The company name. Be very specific and extract the full name. For example, if the name is "McDonald's Chalon Sur Saone Bowling", extract the entire name, not just "McDonald's Chalon". Look for variations of McDonald's like "MAC DO", "McDONALD'S", etc.
        2. restaurant_address: The restaurant address if mentioned (street address, city, postal code)
        3. invoice_provider: The invoice provider/collector company (like SUEZ, VEOLIA, PAPREC, etc.)
        4. invoice_date: The relevant date for filename in DD/MM/YYYY format (see critical note below)
        5. invoice_number: The invoice number (usually alphanumeric)
        6. site_number: The site number (e.g., 620). ONLY extract this if the invoice_provider is "ABCDE", "REFOOD", or "VEOLIA". For all other providers, this should be null.
        
        Important notes:
        - For "ABCDE" invoices, the site number is in a format like "Mcdonald's n°620". Extract 620.
        - For "REFOOD" invoices, the site number is found after the text "N° commande - vos références :". It might be preceded by a hyphen (e.g., "-1419"). You must extract only the number itself (e.g., "1419"). For example, from "N° commande - vos références : -353", extract 353.
        - For "VEOLIA" invoices, the site number is in a format like "MC DONALD'S - CODE RESTAURANT 865". Extract 865.
        - For McDonald's variations, normalize to include the location (e.g., "MAC DO CHALON" should be "McDonald's Chalon")
        - Extract the restaurant address if visible - this helps identify the specific location
        - CRITICAL: The address "34 BOULEVARD DES ITALIENS" belongs to "SOCIETE RUBO", which is our own company, NOT the restaurant. You MUST NOT extract this address as the `restaurant_address`. If this is the only address you can find, you MUST return `null` for the `restaurant_address` field.
        - When "SOCIETE RUBO" is present, ignore the "34 BOULEVARD DES ITALIENS" address completely and find the restaurant's actual address listed elsewhere in the document. If no other address is found, return `null`.
        - CRITICAL: "SOCIETE RUBO" is NEVER the invoice_provider. If you see "SOCIETE RUBO", you MUST find another company name in the document to use as the invoice_provider. The actual provider will be another company mentioned in the invoice (e.g., a logo, another address).
        - The invoice provider is usually the company issuing the invoice
        - Be very careful with the invoice number - it's usually prominently displayed
        - CRITICAL: Look for company logos in the image! Sometimes the invoice provider will not be listed explicitly via text, in this case you MUST use the logos to identify the provider (e.g., SUEZ logo, VEOLIA logo, PAPREC logo) and use that as the invoice_provider
        - Give priority to logos over text when determining the invoice provider - if you see a PAPREC logo but text mentions "RUBO", the correct provider is PAPREC
        - CRITICAL FOR DATE: Look for "Période" field first, which shows a date range (e.g., "01/05/2025 - 31/05/2025"). If this exists, use the START date of the range as the invoice_date. Only if no "Période" field exists, then use the regular invoice date. The "Période" represents the service period and is more important for our filing system than the actual invoice creation date.
        
        Return only valid JSON:
        """
        
        try:
            # Wait if necessary to respect rate limits
            self.rate_limiter.wait_if_needed(self.processing_logger)
            
            # Convert PDF to image for Gemini analysis
            pdf_image = self._convert_pdf_to_image(pdf_path)
            if pdf_image is None:
                # Fallback to text extraction if image conversion fails
                pdf_text = self._extract_pdf_text(pdf_path)
                if not pdf_text:
                    logger.error(f"Could not extract text or convert to image from {pdf_path}")
                    return {}
                
                # Use text-based analysis as fallback
                text_prompt = f"""
                Analyze this French invoice text and extract the following information in JSON format:
                
                1. entreprise: The company name. Be very specific and extract the full name. For example, if the name is "McDonald's Chalon Sur Saone Bowling", extract the entire name, not just "McDonald's Chalon". Look for variations of McDonald's like "MAC DO", "McDONALD'S", etc.
                2. restaurant_address: The restaurant address if mentioned (street address, city, postal code)
                3. invoice_provider: The invoice provider/collector company (like SUEZ, VEOLIA, PAPREC, etc.)
                4. invoice_date: The relevant date for filename in DD/MM/YYYY format (see critical note below)
                5. invoice_number: The invoice number (usually alphanumeric)
                6. site_number: The site number (e.g., 620). ONLY extract this if the invoice_provider is "ABCDE", "REFOOD", or "VEOLIA". For all other providers, this should be null.
                
                Important notes:
                - For "ABCDE" invoices, the site number is in a format like "Mcdonald's n°620". Extract 620.
                - For "REFOOD" invoices, the site number is found after the text "N° commande - vos références :". It might be preceded by a hyphen (e.g., "-1419"). You must extract only the number itself (e.g., "1419"). For example, from "N° commande - vos références : -353", extract 353.
                - For "VEOLIA" invoices, the site number is in a format like "MC DONALD'S - CODE RESTAURANT 865". Extract 865.
                - For McDonald's variations, normalize to include the location (e.g., "MAC DO CHALON" should be "McDonald's Chalon")
                - Extract the restaurant address if visible - this helps identify the specific location
                - CRITICAL: The address "34 BOULEVARD DES ITALIENS" belongs to "SOCIETE RUBO", which is our own company, NOT the restaurant. You MUST NOT extract this address as the `restaurant_address`. If this is the only address you can find, you MUST return `null` for the `restaurant_address` field.
                - When "SOCIETE RUBO" is present, ignore the "34 BOULEVARD DES ITALIENS" address completely and find the restaurant's actual address listed elsewhere in the document. If no other address is found, return `null`.
                - CRITICAL: "SOCIETE RUBO" is NEVER the invoice_provider. If you see "SOCIETE RUBO", you MUST find another company name in the document to use as the invoice_provider. The actual provider will be another company mentioned in the invoice.
                - The invoice provider is usually the company issuing the invoice
                - Be very careful with the invoice number - it's usually prominently displayed
                - CRITICAL FOR DATE: Look for "Période" field first, which shows a date range (e.g., "01/05/2025 - 31/05/2025"). If this exists, use the START date of the range as the invoice_date. Only if no "Période" field exists, then use the regular invoice date. The "Période" represents the service period and is more important for our filing system than the actual invoice creation date.
                
                Invoice text:
                {pdf_text}
                
                Return only valid JSON:
                """
                response = self.model.generate_content(text_prompt)
            else:
                # Use image-based analysis
                response = self.model.generate_content([prompt, pdf_image])
            
            # Clean the response to extract JSON
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            result = json.loads(response_text)
            self.processing_logger.log_api_request(filename, True, result)
            
            return result
        except Exception as e:
            logger.error(f"Error analyzing invoice with Gemini: {e}")
            self.processing_logger.log_api_request(filename, False, {"error": str(e)})
            return {}
    
    def _convert_pdf_to_image(self, pdf_path: Path):
        """Convert the first page of a PDF to an image for Gemini analysis."""
        try:
            import pdf2image
            from PIL import Image
            
            # Convert first page of PDF to image
            images = pdf2image.convert_from_path(pdf_path, first_page=1, last_page=1)
            if images:
                return images[0]  # Return PIL Image object
            return None
        except ImportError:
            logger.warning("pdf2image not available, falling back to text extraction")
            return None
        except Exception as e:
            logger.warning(f"Could not convert PDF to image: {e}, falling back to text extraction")
            return None
    
    def _extract_postal_code(self, address: str) -> Optional[str]:
        """Extract postal code from an address string."""
        if not address:
            return None
        
        # French postal codes are 5 digits
        postal_code_match = re.search(r'\b(\d{5})\b', address)
        if postal_code_match:
            return postal_code_match.group(1)
        
        return None
    
    def _find_postal_code_matches(self, invoice_postal_code: str, restaurant_name: str = "") -> List[Dict]:
        """Find restaurants matching postal code with optional name similarity."""
        matches = []
        
        if not invoice_postal_code:
            return matches
        
        for restaurant in self.restaurants_data:
            # Check if restaurant has CP (Code Postal) field
            restaurant_postal_code = restaurant.get('CP', '')
            if str(restaurant_postal_code) == invoice_postal_code:
                # If restaurant name provided, check for name similarity as well
                name_similarity = 0.0
                if restaurant_name:
                    restaurant_name_clean = restaurant.get('Nom', '').lower()
                    # Check for partial name matches (like "Marzy" in "Nevers Marzy")
                    name_parts = restaurant_name.lower().split()
                    for part in name_parts:
                        if part in restaurant_name_clean:
                            name_similarity = 1.0
                            break
                    
                    # Also check reverse (restaurant name parts in invoice name)
                    if name_similarity == 0.0:
                        restaurant_parts = restaurant_name_clean.split()
                        for part in restaurant_parts:
                            if part in restaurant_name.lower():
                                name_similarity = 0.8
                                break
                
                matches.append({
                    'restaurant': restaurant,
                    'name_similarity': name_similarity,
                    'match_type': 'postal_code'
                })
        
        # Sort by name similarity (if restaurant name provided), otherwise just return all matches
        if restaurant_name:
            matches.sort(key=lambda x: x['name_similarity'], reverse=True)
        
        return matches

    def _find_restaurant_site(self, entreprise_name: str, collecte: str, restaurant_address: str = "") -> Tuple[Optional[str], Optional[str]]:
        """Find the site number and restaurant name using Excel-based matching with address fallback.
        
        Returns:
            Tuple[Optional[str], Optional[str]]: (site_number, restaurant_name) or (None, None) if not found
        """
        normalized_name = entreprise_name.lower().strip() if entreprise_name else ""
        
        # First try: Name-based matching, now enhanced to check address
        name_matches = []
        if normalized_name:
            # Extract keywords from AI-provided name (e.g., "traversiere" from "mcdonald's traversiere")
            normalized_keywords_str = self._normalize_text(re.sub(r'(mcdonald[s]?|mac\s*do)', '', normalized_name).strip())
            name_keywords = set(normalized_keywords_str.split())

            for restaurant in self.restaurants_data:
                restaurant_name = restaurant.get('Nom', '').lower()
                db_address = restaurant.get('Adresse', '').lower()

                # Condition 1: Check for similarity in name
                is_similar_name = self._is_similar_restaurant_name(normalized_name, restaurant_name)

                # Condition 2: Check if keywords from AI name are in the DB address (accent-insensitive)
                normalized_db_address = self._normalize_text(db_address)
                address_contains_keyword = False
                if name_keywords:
                    for keyword in name_keywords:
                        if len(keyword) > 3 and keyword in normalized_db_address:
                            address_contains_keyword = True
                            break
                
                if is_similar_name or address_contains_keyword:
                    name_matches.append(restaurant)
        
        # If no name provided or no Excel matches found, try address-based matching if address provided
        if not name_matches and restaurant_address:
            if not normalized_name:
                logger.info(f"No restaurant name provided, trying address matching with '{restaurant_address}'...")
            else:
                logger.info(f"No name matches found for '{entreprise_name}', trying address matching...")
            address_matches = self._find_address_matches(entreprise_name or "Unknown", restaurant_address)
            if address_matches:
                # Use the best address match
                best_match = address_matches[0]['restaurant']
                site_number = best_match.get('Site', best_match.get('Code client'))
                matched_name = best_match.get('Nom', '')
                if site_number:
                    logger.info(f"Found via address matching: {entreprise_name} -> {matched_name} (Site {site_number})")
                    return str(site_number), matched_name
        
        # If still no matches, try postal code matching as final fallback
        if not name_matches and restaurant_address:
            invoice_postal_code = self._extract_postal_code(restaurant_address)
            if invoice_postal_code:
                search_desc = f"'{entreprise_name}'" if entreprise_name else "restaurant address"
                logger.info(f"No name/address matches found for {search_desc}, trying postal code matching with {invoice_postal_code}...")
                postal_matches = self._find_postal_code_matches(invoice_postal_code, entreprise_name or "")
                if postal_matches:
                    # Use the best postal code match (highest name similarity)
                    best_match = postal_matches[0]['restaurant']
                    site_number = best_match.get('Site', best_match.get('Code client'))
                    matched_name = best_match.get('Nom', '')
                    if site_number:
                        logger.info(f"Found via postal code matching: {search_desc} -> {matched_name} (Site {site_number}, CP: {invoice_postal_code})")
                        return str(site_number), matched_name
        
        # If still no matches, skip
        if not name_matches:
            search_info = f"'{entreprise_name}'" if entreprise_name else f"address '{restaurant_address}'"
            logger.warning(f"No restaurant matches found for {search_info} - skipping file")
            return None, None
        
        # Filter name matches by collecte if available (for Excel data, collecte is not part of the row)
        # Since Excel doesn't have collecte column, we validate against Prestataires.csv separately
        valid_collectors = self._extract_valid_collectors()
        if collecte.upper() not in [c.upper() for c in valid_collectors]:
            logger.warning(f"Invalid collecte '{collecte}' not found in Prestataires.csv")
            return None, None
        
        # Multiple name matches - use address to disambiguate if provided
        if len(name_matches) > 1 and restaurant_address:
            logger.info(f"Multiple name matches found for '{entreprise_name}', using address to disambiguate...")
            
            best_match = None
            best_similarity = 0.0
            
            for restaurant in name_matches:
                addr_similarity = self._calculate_address_similarity(
                    restaurant_address, 
                    restaurant.get('Adresse', '')
                )
                if addr_similarity > best_similarity:
                    best_similarity = addr_similarity
                    best_match = restaurant
            
            if best_match and best_similarity > 0.6:  # Lowered threshold for higher confidence
                # Additional validation: check postal code if available
                invoice_postal_code = self._extract_postal_code(restaurant_address)
                restaurant_postal_code = best_match.get('CP', '')
                
                if invoice_postal_code and restaurant_postal_code:
                    if str(restaurant_postal_code) != invoice_postal_code:
                        logger.warning(f"Address match found but postal codes don't match: invoice {invoice_postal_code} vs restaurant {restaurant_postal_code}")
                        
                        # Allow very strong address matches (>0.8) to override postal code mismatches
                        if best_similarity > 0.8:
                            logger.info(f"⚠️  OVERRIDE: Accepting high-confidence address match despite postal code mismatch: {best_match.get('Nom', '')} (Site {best_match.get('Site', '')}, similarity: {best_similarity:.2f})")
                            site_number = best_match.get('Site', best_match.get('Code client'))
                            matched_name = best_match.get('Nom', '')
                            if site_number:
                                logger.info(f"Address disambiguation successful with postal code override: {entreprise_name} -> {matched_name} (Site {site_number}, similarity: {best_similarity:.2f}, invoice CP: {invoice_postal_code}, restaurant CP: {restaurant_postal_code})")
                                return str(site_number), matched_name
                        else:
                            logger.info(f"Rejecting address match due to postal code mismatch: {best_match.get('Nom', '')} (Site {best_match.get('Site', '')}, similarity: {best_similarity:.2f})")
                    else:
                        site_number = best_match.get('Site', best_match.get('Code client'))
                        matched_name = best_match.get('Nom', '')
                        if site_number:
                            logger.info(f"Address disambiguation successful with postal code validation: {entreprise_name} -> {matched_name} (Site {site_number}, similarity: {best_similarity:.2f}, CP: {invoice_postal_code})")
                            return str(site_number), matched_name
                else:
                    # No postal code available for validation - proceed with address match
                    site_number = best_match.get('Site', best_match.get('Code client'))
                    matched_name = best_match.get('Nom', '')
                    if site_number:
                        logger.info(f"Address disambiguation successful (no postal code validation): {entreprise_name} -> {matched_name} (Site {site_number}, similarity: {best_similarity:.2f})")
                        return str(site_number), matched_name
            elif best_match:
                logger.info(f"Best address match has low similarity ({best_similarity:.2f}) - threshold is 0.6")
            
            # If address disambiguation failed, try global postal code matching immediately
            invoice_postal_code = self._extract_postal_code(restaurant_address)
            if invoice_postal_code:
                logger.info(f"Address disambiguation failed, trying global postal code matching with {invoice_postal_code}...")
                postal_matches = self._find_postal_code_matches(invoice_postal_code, entreprise_name or "")
                if postal_matches:
                    if len(postal_matches) == 1:
                        # Single global match
                        best_match = postal_matches[0]['restaurant']
                        site_number = best_match.get('Site', best_match.get('Code client'))
                        matched_name = best_match.get('Nom', '')
                        if site_number:
                            logger.info(f"Found via global postal code matching: {entreprise_name} -> {matched_name} (Site {site_number}, CP: {invoice_postal_code})")
                            return str(site_number), matched_name
                    else:
                        # Multiple global matches - use a combined score of name and address to pick the best one
                        logger.info(f"Found {len(postal_matches)} global postal code matches, using combined name and address score to select best match...")
                        best_match = None
                        best_combined_score = 0.0
                        
                        for match_info in postal_matches:
                            restaurant = match_info['restaurant']
                            restaurant_name = restaurant.get('Nom', '')
                            
                            addr_similarity = self._calculate_address_similarity(restaurant_address, restaurant.get('Adresse', ''))
                            name_similarity = self._calculate_name_similarity(entreprise_name or "", restaurant_name)

                            # Give preference to shorter, more exact matches ("less is more")
                            # Penalize if the DB name is much longer than the invoice name but contains it
                            if len(restaurant_name) > len(entreprise_name or "") and (entreprise_name or "").lower() in restaurant_name.lower():
                                name_similarity *= 0.9

                            # Boost exact matches significantly
                            if restaurant_name.lower() == (entreprise_name or "").lower():
                                name_similarity = 1.5
                            
                            # Weights for combining scores
                            name_weight = 0.7
                            addr_weight = 0.3
                            combined_score = (name_similarity * name_weight) + (addr_similarity * addr_weight)

                            logger.info(f"  - Candidate: {restaurant_name} (Site {restaurant.get('Site', '')})")
                            logger.info(f"    Scores -> Name Sim: {name_similarity:.2f}, Addr Sim: {addr_similarity:.2f}, Combined: {combined_score:.2f}")

                            if combined_score > best_combined_score:
                                best_combined_score = combined_score
                                best_match = restaurant
                        
                        if best_match and best_combined_score >= 0.5:  # Use a threshold for the combined score
                            site_number = best_match.get('Site', best_match.get('Code client'))
                            matched_name = best_match.get('Nom', '')
                            if site_number:
                                logger.info(f"Best global postal code + combined score match: {entreprise_name} -> {matched_name} (Site {site_number}, score: {best_combined_score:.2f}, CP: {invoice_postal_code})")
                                return str(site_number), matched_name
                        else:
                            logger.warning(f"No good combined score match among global postal code matches (best score: {best_combined_score:.2f})")
                else:
                    logger.warning(f"No restaurants found with postal code {invoice_postal_code} in global search")
        
        # If single match or no address disambiguation possible, validate postal code before returning match
        if name_matches:
            logger.info(f"Checking {len(name_matches)} name match candidates for postal code validation:")
            for i, restaurant in enumerate(name_matches[:3]):  # Show first 3
                logger.info(f"  {i+1}. {restaurant.get('Nom', '')} (Site {restaurant.get('Site', '')}, CP {restaurant.get('CP', '')})")
            
            # If we have a postal code from the invoice, validate against it
            invoice_postal_code = self._extract_postal_code(restaurant_address) if restaurant_address else None
            if invoice_postal_code:
                logger.info(f"Validating name matches against invoice postal code {invoice_postal_code}...")
                
                # First, try to find exact matches within the name matches
                postal_code_name_matches = []
                for restaurant in name_matches:
                    restaurant_postal_code = restaurant.get('CP', '')
                    if str(restaurant_postal_code) == invoice_postal_code:
                        postal_code_name_matches.append(restaurant)
                
                if postal_code_name_matches:
                    # Found matches within name matches - use name similarity to pick the best one
                    if len(postal_code_name_matches) == 1:
                        best_match = postal_code_name_matches[0]
                    else:
                        # Multiple matches - use name similarity to pick the best one
                        logger.info(f"Found {len(postal_code_name_matches)} postal code matches within name matches, using name similarity...")
                        best_match = None
                        best_similarity = 0.0
                        
                        for restaurant in postal_code_name_matches:
                            restaurant_name = restaurant.get('Nom', '').lower()
                            similarity = self._calculate_name_similarity(normalized_name, restaurant_name)
                            logger.info(f"  Name similarity: {similarity:.2f} for {restaurant.get('Nom', '')} (Site {restaurant.get('Site', '')})")
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_match = restaurant
                        
                        logger.info(f"Best name match within postal code matches: {best_match.get('Nom', '')} (similarity: {best_similarity:.2f})")
                    
                    site_number = best_match.get('Site', best_match.get('Code client'))
                    matched_name = best_match.get('Nom', '')
                    if site_number:
                        logger.info(f"Found validated match: {entreprise_name} -> {matched_name} (Site {site_number}, CP: {invoice_postal_code})")
                        return str(site_number), matched_name
                else:
                    # No matches within name matches - search ALL restaurants with this postal code
                    logger.info(f"No postal code matches within name matches, searching all restaurants with postal code {invoice_postal_code}...")
                    all_postal_matches = []
                    for restaurant in self.restaurants_data:
                        restaurant_postal_code = restaurant.get('CP', '')
                        if str(restaurant_postal_code) == invoice_postal_code:
                            all_postal_matches.append(restaurant)
                    
                    if all_postal_matches:
                        logger.info(f"Found {len(all_postal_matches)} restaurants with postal code {invoice_postal_code}")
                        for i, restaurant in enumerate(all_postal_matches[:5]):  # Show first 5
                            logger.info(f"  {i+1}. {restaurant.get('Nom', '')} (Site {restaurant.get('Site', '')}, CP {restaurant.get('CP', '')})")
                        
                        # Now match by name similarity within these postal code matches
                        best_match = None
                        best_similarity = 0.0
                        
                        for restaurant in all_postal_matches:
                            restaurant_name = restaurant.get('Nom', '').lower()
                            similarity = self._calculate_name_similarity(normalized_name, restaurant_name)
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_match = restaurant
                        
                        if best_match and best_similarity > 0.3:  # Lower threshold for postal code validated matches
                            site_number = best_match.get('Site', best_match.get('Code client'))
                            matched_name = best_match.get('Nom', '')
                            if site_number:
                                logger.info(f"Found postal code + name match: {entreprise_name} -> {matched_name} (Site {site_number}, similarity: {best_similarity:.2f}, CP: {invoice_postal_code})")
                                return str(site_number), matched_name
                        
                        logger.warning(f"Found restaurants with postal code {invoice_postal_code} but no good name matches (best similarity: {best_similarity:.2f})")
                    else:
                        logger.warning(f"No restaurants found with postal code {invoice_postal_code}")
                
                logger.warning(f"No validated matches found for postal code {invoice_postal_code} - cannot safely assign site number")
                return None, None
            else:
                # No postal code available - use first match as fallback (risky but legacy behavior)
                logger.warning(f"No postal code available for validation - using first name match as fallback")
                # Sort by name length (prefer shorter, more generic names)
                name_matches.sort(key=lambda x: len(x.get('Nom', '')))
                first_match = name_matches[0]
                site_number = first_match.get('Site', first_match.get('Code client'))
                matched_name = first_match.get('Nom', '')
                if site_number:
                    logger.warning(f"Using unvalidated fallback match: {entreprise_name} -> {matched_name} (Site {site_number})")
                    return str(site_number), matched_name
        
        return None, None
    
    def _is_similar_restaurant_name(self, name1: str, name2: str) -> bool:
        """Check if two restaurant names are similar (for fuzzy matching)."""
        # Extract key components
        name1_clean = re.sub(r'[^\w\s]', '', name1.lower())
        name2_clean = re.sub(r'[^\w\s]', '', name2.lower())
        
        # For McDonald's, check if location matches
        if any(variant in name1_clean for variant in ['mcdonald', 'mac do']):
            if any(variant in name2_clean for variant in ['mcdonald', 'mac do']):
                # Extract location parts
                location1 = re.sub(r'(mcdonald[s]?|mac\s*do)', '', name1_clean).strip()
                location2 = re.sub(r'(mcdonald[s]?|mac\s*do)', '', name2_clean).strip()
                
                # Check if locations match or are similar
                return location1 in location2 or location2 in location1 or \
                       any(word in location2.split() for word in location1.split() if len(word) > 2)
        
        # For non-McDonald's restaurants, check for direct name similarity
        return name1_clean == name2_clean or name1_clean in name2_clean or name2_clean in name1_clean
    
    def _determine_collecte_suffix(self, collecte: str) -> str:
        """Return the collecte name without waste type suffixes and spaces removed."""
        return collecte.upper().replace(' ', '')
    
    def _sanitize_invoice_number(self, invoice_number: str) -> str:
        """Sanitize invoice number by removing accents and all non-alphanumeric characters."""
        if not invoice_number:
            return invoice_number
        
        # Normalize to remove accents, preserving case
        deaccented = ''.join(c for c in unicodedata.normalize('NFKD', invoice_number) if not unicodedata.combining(c))
        
        # Remove all non-alphanumeric characters
        sanitized = re.sub(r'[^a-zA-Z0-9]', '', deaccented)
        
        return sanitized.replace('\\', '')
    
    def _format_date(self, date_str: str) -> str:
        """Format date from DD/MM/YYYY to MMYYYY."""
        try:
            # Parse the date
            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
            return date_obj.strftime('%m%Y')
        except ValueError:
            logger.error(f"Could not parse date: {date_str}")
            return "UNKNOWN"
    
    def generate_new_filename(self, pdf_path: Path) -> Optional[str]:
        """Generate new filename for a PDF based on its content."""
        logger.info(f"Processing: {pdf_path}")
        
        # Analyze with Gemini
        analysis = self._analyze_invoice_with_gemini(pdf_path, pdf_path.name)
        if not analysis:
            logger.error(f"Could not analyze invoice content for {pdf_path}")
            return None
        
        logger.info(f"Analysis result: {analysis}")
        
        # Extract required information
        entreprise = analysis.get('entreprise', '')
        invoice_provider = analysis.get('invoice_provider', '')
        invoice_date = analysis.get('invoice_date', '')
        invoice_number = analysis.get('invoice_number', '')
        restaurant_address = analysis.get('restaurant_address', '')
        
        if not all([entreprise, invoice_provider, invoice_date, invoice_number]):
            logger.error(f"Missing required information for {pdf_path}")
            logger.error(f"entreprise: {entreprise}, provider: {invoice_provider}, date: {invoice_date}, number: {invoice_number}")
            return None
        
        # Find base collecte name from the full provider name
        base_collecte = self._find_base_collecte_name(invoice_provider)
        if not base_collecte:
            logger.error(f"Could not find base collecte name for provider '{invoice_provider}'")
            return None
        
        # Validate that the collector is in our valid collectors list
        if not self._validate_collector(invoice_provider, base_collecte):
            logger.error(f"Skipping file: Invalid collector '{base_collecte}' not in approved collectors list")
            return None
        
        logger.info(f"Base collecte name: {base_collecte}")
        
        # Find site number using the base collecte name
        site_number, matched_restaurant_name = self._find_restaurant_site(entreprise, base_collecte, restaurant_address)
        if not site_number:
            logger.error(f"Could not find site number for {entreprise} with collecte {base_collecte}")
            return None
        
        # Use base collecte name as the collecte suffix
        collecte_suffix = self._determine_collecte_suffix(base_collecte)
        
        # Format date
        formatted_date = self._format_date(invoice_date)
        
        # Generate filename
        new_filename = f"{site_number}-{collecte_suffix}-{formatted_date}-{self._sanitize_invoice_number(invoice_number)}.pdf"
        
        logger.info(f"Generated filename: {new_filename}")
        return new_filename
    
    def generate_new_filename_with_details(self, pdf_path: Path) -> Tuple[Optional[str], Dict]:
        """Generate new filename for a PDF and return detailed extraction data."""
        # Analyze with Gemini (includes both image and text extraction fallbacks)
        analysis = self._analyze_invoice_with_gemini(pdf_path, pdf_path.name)
        if not analysis:
            error_details = {
                'error': 'Gemini analysis failed or returned no data',
                'pdf_size': f"{pdf_path.stat().st_size} bytes",
                'file_extension': pdf_path.suffix
            }
            return None, error_details
            error_details = {
                'error': 'Could not analyze invoice content',
                'pdf_text_length': len(pdf_text),
                'analysis_result': analysis
            }
            return None, error_details
        
        # Post-process to filter out the known incorrect RUBO address
        # This is a safeguard against the AI model incorrectly extracting our company's address.
        raw_address = analysis.get('restaurant_address')
        if isinstance(raw_address, str) and "34" in raw_address and "boulevard des italiens" in raw_address.lower():
            logger.warning(f"AI returned the RUBO address '{raw_address}'. Ignoring it as per rules.")
            analysis['restaurant_address'] = None

        # Extract required information
        entreprise = analysis.get('entreprise', '')
        invoice_provider = analysis.get('invoice_provider', '')
        invoice_date = analysis.get('invoice_date', '')
        invoice_number = analysis.get('invoice_number', '')
        restaurant_address = analysis.get('restaurant_address', '')
        
        # Prepare detailed extraction data
        extracted_data = {
            'restaurant_name': entreprise,
            'invoice_provider': invoice_provider,
            'invoice_date': invoice_date,
            'invoice_number': invoice_number,
            'restaurant_address': restaurant_address,
            'raw_analysis': analysis
        }

        # Handle ABCDE, REFOOD, and VEOLIA special cases
        if invoice_provider and invoice_provider.upper() in ['ABCDE', 'REFOOD', 'VEOLIA']:
            return self._handle_invoice_with_site_number(analysis, extracted_data, invoice_provider.upper())
        
        # Validate required fields
        missing_fields = []
        # Allow entreprise to be missing if we have restaurant_address for postal code matching
        if not entreprise and not restaurant_address:
            missing_fields.append('entreprise (no address available for fallback matching)')
        if not invoice_provider:
            missing_fields.append('invoice_provider')
        if not invoice_date:
            missing_fields.append('invoice_date')
        if not invoice_number:
            missing_fields.append('invoice_number')
        
        if missing_fields:
            extracted_data['error'] = f"Missing required fields: {', '.join(missing_fields)}"
            extracted_data['available_fields'] = {k: v for k, v in analysis.items() if v}
            return None, extracted_data
        
        # Find base collecte name from the full provider name
        base_collecte = self._find_base_collecte_name(invoice_provider)
        if not base_collecte:
            extracted_data['error'] = f"Could not find base collecte name for provider '{invoice_provider}'"
            extracted_data['available_providers'] = list(self.prestataires_data.keys())
            return None, extracted_data
        
        # Validate that the collector is in our valid collectors list
        if not self._validate_collector(invoice_provider, base_collecte):
            extracted_data['error'] = f"Invalid collector '{base_collecte}' not in approved collectors list"
            extracted_data['valid_collectors'] = sorted(list(self.valid_collectors))
            return None, extracted_data
        
        extracted_data['base_collecte'] = base_collecte
        
        # Find site number and restaurant name using the base collecte name
        site_number, matched_restaurant_name = self._find_restaurant_site(entreprise or "", base_collecte, restaurant_address)
        if not site_number:
            # Determine what to show in error message
            search_term = entreprise if entreprise else f"address: {restaurant_address}"
            extracted_data['error'] = f"Could not find site number for '{search_term}' with collecte '{base_collecte}'"
            # Find similar restaurant names for debugging
            similar_restaurants = []
            for restaurant in self.restaurants_data:
                restaurant_name = restaurant.get('Nom', '')
                if entreprise and any(word in restaurant_name.lower() for word in entreprise.lower().split() if len(word) > 2):
                    similar_restaurants.append({
                        'name': restaurant_name,
                        'site': restaurant.get('Site', restaurant.get('Code client')),
                        'collecte': base_collecte
                    })
            extracted_data['similar_restaurants'] = similar_restaurants[:5]  # Top 5 matches
            return None, extracted_data
        
        extracted_data['site_number'] = site_number
        
        # Update restaurant name if we found a match via fallback methods
        if matched_restaurant_name and not entreprise:
            extracted_data['restaurant_name'] = matched_restaurant_name
            logger.info(f"Updated restaurant name from fallback matching: {matched_restaurant_name}")
        
        # Use base collecte name as the collecte suffix
        collecte_suffix = self._determine_collecte_suffix(base_collecte)
        extracted_data['collecte'] = collecte_suffix
        
        # Format date
        formatted_date = self._format_date(invoice_date)
        extracted_data['formatted_date'] = formatted_date
        
        # Generate filename
        new_filename = f"{site_number}-{collecte_suffix}-{formatted_date}-{self._sanitize_invoice_number(invoice_number)}.pdf"
        extracted_data['generated_filename'] = new_filename
        
        return new_filename, extracted_data

    def rename_pdfs_in_directory(self, directory: Path, dry_run: bool = True) -> Dict:
        """Rename all PDFs in a directory."""
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        # Pick up all PDFs, case-insensitive (.pdf or .PDF)
        pdf_files = [f for f in directory.iterdir() if f.is_file() and f.suffix.lower() == '.pdf']
        
        # Log processing start
        rate_status = self.get_rate_limit_status()
        self.processing_logger.log_processing_start(len(pdf_files), str(directory), dry_run, rate_status)
        
        for i, pdf_file in enumerate(pdf_files, 1):
            self.processing_logger.log_file_processing_start(pdf_file.name, i, len(pdf_files))
            
            try:
                new_filename, extracted_data = self.generate_new_filename_with_details(pdf_file)
                
                if new_filename:
                    new_path = pdf_file.parent / new_filename
                    
                    if new_path.exists():
                        reason = f"Target file already exists: {new_filename}"
                        self.processing_logger.log_file_skipped(pdf_file.name, reason)
                        results['skipped'].append({
                            'original': str(pdf_file),
                            'target': str(new_path),
                            'reason': 'Target file already exists'
                        })
                        continue
                    
                    if not dry_run:
                        pdf_file.rename(new_path)
                    
                    self.processing_logger.log_file_success(pdf_file.name, new_filename, extracted_data, dry_run)
                    results['success'].append({
                        'original': str(pdf_file),
                        'new': str(new_path)
                    })
                else:
                    reason = "Could not generate filename - missing or invalid data from AI analysis"
                    details = {
                        'extracted_data': extracted_data,
                        'pdf_size': f"{pdf_file.stat().st_size} bytes"
                    }
                    self.processing_logger.log_file_failure(pdf_file.name, reason, details)
                    results['failed'].append({
                        'file': str(pdf_file),
                        'reason': reason
                    })
                    
            except Exception as e:
                reason = f"Processing error: {str(e)}"
                details = {
                    'error_type': type(e).__name__,
                    'pdf_size': f"{pdf_file.stat().st_size} bytes" if pdf_file.exists() else "unknown"
                }
                self.processing_logger.log_file_failure(pdf_file.name, reason, details)
                results['failed'].append({
                    'file': str(pdf_file),
                    'reason': reason
                })
        
        # Log session end
        final_rate_status = self.get_rate_limit_status()
        self.processing_logger.log_session_end(final_rate_status)
        
        return results

    def get_rate_limit_status(self) -> Dict:
        """Get current rate limiting status."""
        return self.rate_limiter.get_status()
    
    def get_weekly_summary(self) -> Dict:
        """Get weekly API usage summary."""
        return self.rate_limiter.get_weekly_summary()
    
    def reset_daily_counter(self):
        """Reset today's API request counter (use with caution)."""
        self.rate_limiter.reset_today_count()
    
    def _find_base_collecte_name(self, provider_name):
        """Find the base collecte name from a full provider name using a multi-step matching process."""
        if not provider_name:
            return None
            
        provider_upper = provider_name.upper()
        
        # 1. Check for an exact match in the alias dictionary first
        for alias, parent in self.provider_aliases.items():
            if alias.upper() in provider_upper:
                logger.info(f"Found provider '{alias}' and mapped to parent '{parent}' via alias dictionary.")
                return parent

        # Split by common delimiters like space, hyphen, or period.
        provider_words = set(re.split(r'[\s.-]', provider_upper))

        # 1. Word-based match (e.g., "SUEZ" in "SUEZ EAU FRANCE")
        # More robust than substring; we sort by word count to prioritize more specific matches.
        sorted_collectors_by_word_count = sorted(self.prestataires_data.keys(), key=lambda x: len(x.split()), reverse=True)
        for collecte in sorted_collectors_by_word_count:
            collecte_upper = collecte.upper()
            collecte_words = set(collecte_upper.split())
            if collecte_words.issubset(provider_words):
                logger.info(f"Found base collecte '{collecte}' via word match in provider '{provider_name}'")
                return collecte

        # 2. Substring match as a fallback (e.g., "PAPREC" in "PAPREC IDF")
        # Sort collectors by length (longest first) to avoid partial matches like "PAP" instead of "PAPREC".
        sorted_collectors_by_len = sorted(self.prestataires_data.keys(), key=len, reverse=True)
        for collecte in sorted_collectors_by_len:
            collecte_upper = collecte.upper()
            if collecte_upper in provider_upper:
                logger.info(f"Found base collecte '{collecte}' via substring match in provider '{provider_name}'")
                return collecte
        
        # 3. Fuzzy matching for spelling variations (e.g., ALCHIMISTES vs ALCHEMISTES)
        best_match = None
        best_ratio = 0.0
        # Compare each known collector against each word from the invoice's provider name
        for collecte in self.prestataires_data.keys():
            collecte_upper = collecte.upper()
            for provider_word in provider_words:
                ratio = SequenceMatcher(None, collecte_upper, provider_word).ratio()
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_match = collecte

        # Use a threshold to avoid false positives from fuzzy matching
        FUZZY_MATCH_THRESHOLD = 0.8
        if best_ratio >= FUZZY_MATCH_THRESHOLD:
            logger.info(f"Found base collecte '{best_match}' via fuzzy match in provider '{provider_name}' (ratio: {best_ratio:.2f})")
            return best_match
    
        logger.warning(f"Could not find base collecte name for provider '{provider_name}'")
        return None

    def _handle_invoice_with_site_number(self, analysis: Dict, extracted_data: Dict, provider_name: str) -> Tuple[Optional[str], Dict]:
        """Handle specific cases for invoices where site number is directly available."""
        logger.info(f"Handling special case for {provider_name} invoice")

        site_number = analysis.get('site_number')

        if not site_number:
            extracted_data['error'] = f"Invoice provider is {provider_name} but no site_number was found in the analysis"
            return None, extracted_data

        # Sanitize site number to remove non-digits and leading zeros
        if isinstance(site_number, str):
            # Remove all non-digit characters
            site_number_digits = re.sub(r'\D', '', site_number)
            if site_number_digits:
                # Convert to int and back to string to remove leading zeros
                site_number = str(int(site_number_digits))
            else:
                site_number = "" # Set to empty if no digits found
        elif isinstance(site_number, int):
            site_number = str(site_number)

        if not site_number:
            extracted_data['error'] = f"Site number is empty after sanitization for provider {provider_name}"
            return None, extracted_data

        invoice_date = analysis.get('invoice_date')
        invoice_number = analysis.get('invoice_number')

        # Basic validation for other required fields
        if not invoice_date or not invoice_number:
            missing_fields = []
            if not invoice_date: missing_fields.append('invoice_date')
            if not invoice_number: missing_fields.append('invoice_number')
            extracted_data['error'] = f"Missing required fields for {provider_name} invoice: {', '.join(missing_fields)}"
            return None, extracted_data

        collecte_suffix = provider_name
        formatted_date = self._format_date(invoice_date)

        # Update extracted_data for logging
        extracted_data['site_number'] = site_number
        extracted_data['collecte'] = collecte_suffix
        extracted_data['formatted_date'] = formatted_date

        # Generate filename
        new_filename = f"{site_number}-{collecte_suffix}-{formatted_date}-{self._sanitize_invoice_number(invoice_number)}.pdf"
        extracted_data['generated_filename'] = new_filename

        logger.info(f"Successfully generated filename for {provider_name} invoice: {new_filename}")

        return new_filename, extracted_data


def main():
    parser = argparse.ArgumentParser(description='Rename PDF invoices based on content')
    parser.add_argument('directory', nargs='?', help='Directory containing PDF files to rename')
    parser.add_argument('--api-key', help='Google Gemini API key (or set GEMINI_API_KEY in .env file)')
    parser.add_argument('--csv-dir', default='.', help='Directory containing CSV files (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without actually renaming files')
    parser.add_argument('--status', action='store_true', help='Show current rate limit status and exit')
    parser.add_argument('--weekly-summary', action='store_true', help='Show weekly API usage summary and exit')
    parser.add_argument('--reset-counter', action='store_true', help='Reset today\'s API request counter (use with caution)')
    parser.add_argument('--disable-detailed-logging', action='store_true', help='Disable detailed log files (console only)')
    
    args = parser.parse_args()
    
    # Handle status and summary commands first (don't need directory)
    if args.status or args.weekly_summary or args.reset_counter:
        try:
            enable_detailed_logging = not args.disable_detailed_logging
            renamer = PDFRenamer(args.api_key, args.csv_dir, enable_detailed_logging)
            
            if args.status:
                status = renamer.get_rate_limit_status()
                print(f"📊 Rate Limit Status:")
                print(f"  Today: {status['requests_today']}/{status['max_per_day']} ({status['remaining_today']} remaining)")
                print(f"  This minute: {status['requests_this_minute']}/{status['max_per_minute']} ({status['remaining_this_minute']} remaining)")
                print(f"  Total lifetime requests: {status['total_lifetime_requests']}")
                
                if status['historical_usage']:
                    print(f"\n📈 Recent Usage (last 7 days):")
                    for day in status['historical_usage']:
                        print(f"    {day['date']}: {day['requests']} requests")
                
            if args.weekly_summary:
                summary = renamer.get_weekly_summary()
                print(f"\n📅 Weekly Summary:")
                print(f"  Total requests this week: {summary['weekly_total']}")
                print(f"  Average per day: {summary['average_per_day']:.1f}")
                print(f"\n  Daily breakdown:")
                for day in summary['daily_breakdown']:
                    print(f"    {day['day_name']} ({day['date']}): {day['requests']} requests")
                
            if args.reset_counter:
                print("⚠️  Are you sure you want to reset today's API request counter?")
                response = input("This should only be done if you know the count is incorrect. Type 'yes' to confirm: ")
                if response.lower() == 'yes':
                    renamer.reset_daily_counter()
                    print("✅ Today's request counter has been reset to 0")
                else:
                    print("❌ Reset cancelled")
                    
            return
        except Exception as e:
            logger.error(f"Error: {e}")
            return
    
    # For processing, directory is required
    if not args.directory:
        parser.error("Directory argument is required for processing PDFs")
        
    # If just checking status
    if args.status:
        try:
            renamer = PDFRenamer(args.api_key, args.csv_dir)
            status = renamer.get_rate_limit_status()
            print(f"Rate Limit Status:")
            print(f"  Today: {status['requests_today']}/{status['max_per_day']} ({status['remaining_today']} remaining)")
            print(f"  This minute: {status['requests_this_minute']}/{status['max_per_minute']} ({status['remaining_this_minute']} remaining)")
            return
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return
    
    # Validate directories
    pdf_dir = Path(args.directory)
    csv_dir = Path(args.csv_dir)
    
    if not pdf_dir.exists():
        logger.error(f"PDF directory does not exist: {pdf_dir}")
        return
    
    if not csv_dir.exists():
        logger.error(f"CSV directory does not exist: {csv_dir}")
        return
    
    # Check for required CSV files
    required_files = ['Liste des clients.xlsx', 'Prestataires.csv']
    for file in required_files:
        if not (csv_dir / file).exists():
            logger.error(f"Required CSV file not found: {csv_dir / file}")
            return
    
    # Initialize renamer
    try:
        enable_detailed_logging = not args.disable_detailed_logging
        renamer = PDFRenamer(args.api_key, csv_dir, enable_detailed_logging)
        
        # Show initial rate limit status
        status = renamer.get_rate_limit_status()
        logger.info(f"Starting with {status['remaining_today']} API requests remaining today")
        
    except Exception as e:
        logger.error(f"Failed to initialize PDF renamer: {e}")
        return
    
    # Count PDFs to process
    pdf_files = list(pdf_dir.glob('*.pdf'))
    total_pdfs = len(pdf_files)
    
    if total_pdfs > status['remaining_today']:
        logger.warning(f"Found {total_pdfs} PDFs but only {status['remaining_today']} API requests remaining today")
        response = input(f"Continue with processing the first {status['remaining_today']} files? (y/n): ")
        if response.lower() != 'y':
            logger.info("Processing cancelled by user")
            return
    
    # Process files
    results = renamer.rename_pdfs_in_directory(pdf_dir, args.dry_run)
    
    # Get reference to processing logger for cleanup
    processing_logger = renamer.processing_logger
    
    # Show final rate limit status
    final_status = renamer.get_rate_limit_status()
    
    # Print summary
    print("\n" + "="*50)
    print("PROCESSING SUMMARY")
    print("="*50)
    print(f"Successfully processed: {len(results['success'])}")
    print(f"Failed: {len(results['failed'])}")
    print(f"Skipped: {len(results['skipped'])}")
    print(f"API requests used: {final_status['requests_today']}")
    print(f"Remaining today: {final_status['remaining_today']}")
    
    if results['failed']:
        print("\nFAILED FILES:")
        for failed in results['failed']:
            print(f"  - {failed['file']}: {failed['reason']}")
    
    if results['skipped']:
        print("\nSKIPPED FILES:")
        for skipped in results['skipped']:
            print(f"  - {skipped['original']}: {skipped['reason']}")
    
    if args.dry_run:
        print("\nNote: This was a dry run. No files were actually renamed.")
    
    if final_status['remaining_today'] <= 10:
        print(f"\n⚠️  Warning: Only {final_status['remaining_today']} API requests remaining today!")
    
    # Log session end - Note: session end is already logged in rename_pdfs_in_directory()
    # processing_logger.log_session_end(final_status)
    processing_logger.cleanup()


if __name__ == "__main__":
    main()
