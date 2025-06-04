#!/usr/bin/env python3
"""
PDF Invoice Renamer Script
Automatically renames PDF invoices based on their content using the format:
Site-Collecte(+CS/BIO/DIB)-InvoiceMonthYear-InvoiceNumber
"""

import os
import re
import csv
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import PyPDF2
import google.generativeai as genai
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RateLimiter:
    """Rate limiter to respect Google Gemini API free tier limits."""
    
    def __init__(self, max_per_minute: int = 15, max_per_day: int = 1500):
        self.max_per_minute = max_per_minute
        self.max_per_day = max_per_day
        self.requests_this_minute = []
        self.requests_today = 0
        self.current_day = datetime.now().date()
        self.verbose = os.getenv('RATE_LIMIT_VERBOSE', 'false').lower() == 'true'
        
    def wait_if_needed(self):
        """Wait if necessary to respect rate limits."""
        now = datetime.now()
        
        # Reset daily counter if it's a new day
        if now.date() != self.current_day:
            self.requests_today = 0
            self.current_day = now.date()
            if self.verbose:
                logger.info("New day - resetting daily request counter")
        
        # Check daily limit
        if self.requests_today >= self.max_per_day:
            logger.warning(f"Daily limit of {self.max_per_day} requests reached. Please try again tomorrow.")
            raise Exception(f"Daily API limit reached ({self.max_per_day} requests)")
        
        # Remove requests older than 1 minute
        minute_ago = now - timedelta(minutes=1)
        self.requests_this_minute = [req_time for req_time in self.requests_this_minute if req_time > minute_ago]
        
        # Check per-minute limit
        if len(self.requests_this_minute) >= self.max_per_minute:
            sleep_time = 60 - (now - self.requests_this_minute[0]).total_seconds()
            if sleep_time > 0:
                logger.info(f"Rate limit: waiting {sleep_time:.1f} seconds (used {len(self.requests_this_minute)}/{self.max_per_minute} requests this minute)")
                time.sleep(sleep_time)
                # Clean up the list after waiting
                minute_ago = datetime.now() - timedelta(minutes=1)
                self.requests_this_minute = [req_time for req_time in self.requests_this_minute if req_time > minute_ago]
        
        # Record this request
        self.requests_this_minute.append(now)
        self.requests_today += 1
        
        if self.verbose:
            logger.info(f"API request #{self.requests_today} today, {len(self.requests_this_minute)} this minute")
    
    def get_status(self) -> Dict:
        """Get current rate limiting status."""
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        self.requests_this_minute = [req_time for req_time in self.requests_this_minute if req_time > minute_ago]
        
        return {
            'requests_today': self.requests_today,
            'max_per_day': self.max_per_day,
            'requests_this_minute': len(self.requests_this_minute),
            'max_per_minute': self.max_per_minute,
            'remaining_today': self.max_per_day - self.requests_today,
            'remaining_this_minute': self.max_per_minute - len(self.requests_this_minute)
        }

class PDFRenamer:
    def __init__(self, api_key: str = None, csv_dir: str = "."):
        """Initialize the PDF renamer with API key and CSV directory."""
        # Get API key from parameter or environment
        if not api_key:
            api_key = os.getenv('GEMINI_API_KEY')
        
        if not api_key or api_key == 'your_api_key_here':
            raise ValueError("Please set your Gemini API key in the .env file or pass it as a parameter")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.csv_dir = Path(csv_dir)
        
        # Initialize rate limiter
        max_per_minute = int(os.getenv('MAX_REQUESTS_PER_MINUTE', 15))
        max_per_day = int(os.getenv('MAX_REQUESTS_PER_DAY', 1500))
        self.rate_limiter = RateLimiter(max_per_minute, max_per_day)
        
        logger.info(f"Rate limiter initialized: {max_per_minute}/minute, {max_per_day}/day")
        
        # Load data from CSV files
        self.restaurants_data = self._load_restaurants_data()
        self.prestataires_data = self._load_prestataires_data()
        
        # Create lookup dictionaries for faster matching
        self.restaurant_lookup = self._create_restaurant_lookup()
        
    def _load_restaurants_data(self) -> List[Dict]:
        """Load restaurant data from CSV file."""
        restaurants = []
        csv_path = self.csv_dir / "Restaurants.csv"
        
        with open(csv_path, 'r', encoding='utf-8-sig') as file:  # Handle BOM
            reader = csv.DictReader(file, delimiter=';')
            for row in reader:
                # Clean up column names (remove spaces)
                cleaned_row = {k.strip(): v.strip() for k, v in row.items()}
                restaurants.append(cleaned_row)
        
        logger.info(f"Loaded {len(restaurants)} restaurant entries")
        return restaurants
    
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
    
    def _create_restaurant_lookup(self) -> Dict[str, List[Dict]]:
        """Create a lookup dictionary for faster restaurant matching."""
        lookup = {}
        
        for restaurant in self.restaurants_data:
            entreprise = restaurant['Entreprise'].lower()
            
            # Create various normalized versions for McDonald's variations
            normalized_names = self._normalize_restaurant_name(entreprise)
            
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
    
    def _analyze_invoice_with_gemini(self, pdf_text: str) -> Dict:
        """Use Gemini to analyze invoice content and extract key information."""
        prompt = f"""
        Analyze this French invoice text and extract the following information in JSON format:
        
        1. entreprise: The company name (look for variations of McDonald's like "MAC DO", "McDONALD'S", etc.)
        2. invoice_provider: The invoice provider/collector company (like SUEZ, VEOLIA, PAPREC, etc.)
        3. invoice_date: The invoice date in DD/MM/YYYY format
        4. invoice_number: The invoice number (usually alphanumeric)
        5. waste_types: Array of waste types found (look for DIB, BIO, CS, DECHET RECYCLABLE, etc.)
        
        Important notes:
        - For McDonald's variations, normalize to include the location (e.g., "MAC DO CHALON" should be "McDonald's Chalon")
        - Look for waste type indicators like "DIB", "BIO", "CS", "DECHET RECYCLABLE" (CS), "Déchets recyclables" (CS)
        - The invoice provider is usually the company issuing the invoice
        - Be very careful with the invoice number - it's usually prominently displayed
        
        Invoice text:
        {pdf_text}
        
        Return only valid JSON:
        """
        
        try:
            # Wait if necessary to respect rate limits
            self.rate_limiter.wait_if_needed()
            
            # Make the API call
            response = self.model.generate_content(prompt)
            
            # Clean the response to extract JSON
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Error analyzing invoice with Gemini: {e}")
            return {}
    
    def _find_restaurant_site(self, entreprise_name: str, collecte: str) -> Optional[str]:
        """Find the site number for a restaurant and collecte combination."""
        normalized_name = entreprise_name.lower().strip()
        
        # Try direct lookup first
        if normalized_name in self.restaurant_lookup:
            candidates = self.restaurant_lookup[normalized_name]
        else:
            # Try fuzzy matching for McDonald's variations
            candidates = []
            for lookup_name, restaurants in self.restaurant_lookup.items():
                if self._is_similar_restaurant_name(normalized_name, lookup_name):
                    candidates.extend(restaurants)
        
        # Filter by collecte and sort candidates to prefer simpler/generic names
        matching_candidates = []
        for restaurant in candidates:
            if restaurant['Collecte'].upper() == collecte.upper():
                matching_candidates.append(restaurant)
        
        if not matching_candidates:
            return None
            
        # Sort candidates by name length (prefer shorter, more generic names)
        # This helps "MAC DO CHALON" match to "Mcdonald's CHALON SUR SAONE" (site 1173)
        # instead of "Mcdonald's CHALON SUR SAONE OBELISQUE" (site 161)
        matching_candidates.sort(key=lambda x: len(x['Entreprise']))
        
        return matching_candidates[0]['Site']
    
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
        
        return False
    
    def _determine_collecte_suffix(self, collecte: str, waste_types: List[str]) -> str:
        """Determine the collecte suffix based on waste types found."""
        if not waste_types:
            return collecte.upper()
        
        # Normalize waste types
        detected_types = set()
        for waste_type in waste_types:
            waste_upper = waste_type.upper()
            if 'BIO' in waste_upper:
                detected_types.add('BIO')
            if 'DIB' in waste_upper:
                detected_types.add('DIB')
            if any(cs_indicator in waste_upper for cs_indicator in ['CS', 'RECYCLABLE', 'RECYCLABLES']):
                detected_types.add('CS')
        
        # If no waste types detected, return base collecte
        if not detected_types:
            return collecte.upper()
        
        # Check against valid combinations from prestataires data
        if collecte.upper() in self.prestataires_data:
            valid_combinations = [combo.upper() for combo in self.prestataires_data[collecte.upper()]]
            
            # Find the best matching combination
            best_match = None
            best_score = 0
            
            for combo in valid_combinations:
                # Extract waste types from this combination
                combo_types = set()
                if 'BIO' in combo:
                    combo_types.add('BIO')
                if 'DIB' in combo:
                    combo_types.add('DIB')
                if 'CS' in combo:
                    combo_types.add('CS')
                
                # Calculate match score (how many detected types are in this combination)
                match_score = len(detected_types.intersection(combo_types))
                
                # Prefer exact matches, then partial matches
                if combo_types == detected_types:
                    return combo
                elif match_score > best_score:
                    best_match = combo
                    best_score = match_score
            
            # Return best match if found
            if best_match:
                return best_match
        
        # Fallback: create suffix manually (this shouldn't happen with valid data)
        sorted_types = sorted(list(detected_types))
        return collecte.upper() + ''.join(sorted_types)
    
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
        
        # Extract text from PDF
        pdf_text = self._extract_pdf_text(pdf_path)
        if not pdf_text:
            logger.error(f"Could not extract text from {pdf_path}")
            return None
        
        # Analyze with Gemini
        analysis = self._analyze_invoice_with_gemini(pdf_text)
        if not analysis:
            logger.error(f"Could not analyze invoice content for {pdf_path}")
            return None
        
        logger.info(f"Analysis result: {analysis}")
        
        # Extract required information
        entreprise = analysis.get('entreprise', '')
        invoice_provider = analysis.get('invoice_provider', '')
        invoice_date = analysis.get('invoice_date', '')
        invoice_number = analysis.get('invoice_number', '')
        waste_types = analysis.get('waste_types', [])
        
        if not all([entreprise, invoice_provider, invoice_date, invoice_number]):
            logger.error(f"Missing required information for {pdf_path}")
            logger.error(f"entreprise: {entreprise}, provider: {invoice_provider}, date: {invoice_date}, number: {invoice_number}")
            return None
        
        # Find base collecte name from the full provider name
        base_collecte = self._find_base_collecte_name(invoice_provider)
        if not base_collecte:
            logger.error(f"Could not find base collecte name for provider '{invoice_provider}'")
            return None
        
        logger.info(f"Base collecte name: {base_collecte}")
        
        # Find site number using the base collecte name
        site_number = self._find_restaurant_site(entreprise, base_collecte)
        if not site_number:
            logger.error(f"Could not find site number for {entreprise} with collecte {base_collecte}")
            return None
        
        # Determine collecte suffix using the base collecte name
        collecte_suffix = self._determine_collecte_suffix(base_collecte, waste_types)
        
        # Format date
        formatted_date = self._format_date(invoice_date)
        
        # Generate filename
        new_filename = f"{site_number}-{collecte_suffix}-{formatted_date}-{invoice_number}.pdf"
        
        logger.info(f"Generated filename: {new_filename}")
        return new_filename
    
    def rename_pdfs_in_directory(self, directory: Path, dry_run: bool = True) -> Dict:
        """Rename all PDFs in a directory."""
        results = {
            'success': [],
            'failed': [],
            'skipped': []
        }
        
        pdf_files = list(directory.glob('*.pdf'))
        logger.info(f"Found {len(pdf_files)} PDF files to process")
        
        for pdf_file in pdf_files:
            try:
                new_filename = self.generate_new_filename(pdf_file)
                
                if new_filename:
                    new_path = pdf_file.parent / new_filename
                    
                    if new_path.exists():
                        logger.warning(f"Target file already exists: {new_path}")
                        results['skipped'].append({
                            'original': str(pdf_file),
                            'target': str(new_path),
                            'reason': 'Target file already exists'
                        })
                        continue
                    
                    if not dry_run:
                        pdf_file.rename(new_path)
                        logger.info(f"Renamed: {pdf_file.name} -> {new_filename}")
                    else:
                        logger.info(f"DRY RUN: Would rename {pdf_file.name} -> {new_filename}")
                    
                    results['success'].append({
                        'original': str(pdf_file),
                        'new': str(new_path)
                    })
                else:
                    results['failed'].append({
                        'file': str(pdf_file),
                        'reason': 'Could not generate filename'
                    })
                    
            except Exception as e:
                logger.error(f"Error processing {pdf_file}: {e}")
                results['failed'].append({
                    'file': str(pdf_file),
                    'reason': str(e)
                })
        
        return results

    def get_rate_limit_status(self) -> Dict:
        """Get current rate limiting status."""
        return self.rate_limiter.get_status()
    
    def _find_base_collecte_name(self, provider_name):
        """Find the base collecte name from a full provider name using fuzzy matching."""
        if not provider_name:
            return None
            
        provider_upper = provider_name.upper()
        
        # Check if any collecte name is contained in the provider name
        for collecte in self.prestataires_data.keys():
            collecte_upper = collecte.upper()
            if collecte_upper in provider_upper:
                logger.info(f"Found base collecte '{collecte}' in provider '{provider_name}'")
                return collecte
        
        # If no direct match, try partial matching for common variations
        common_mappings = {
            'SUEZ': ['SUEZ'],
            'VEOLIA': ['VEOLIA'],
            'REFOOD': ['REFOOD'],
            'PAPREC': ['PAPREC'],
            'ELISE': ['ELISE'],
            'DERICHEBOURG': ['DERICHEBOURG'],
            'ORTEC': ['ORTEC'],
            'ATESIS': ['ATESIS'],
            'BRANGEON': ['BRANGEON'],
            'COLLECTEA': ['COLLECTEA'],
        }
        
        for base_name, variations in common_mappings.items():
            for variation in variations:
                if variation in provider_upper:
                    logger.info(f"Found base collecte '{base_name}' via mapping from provider '{provider_name}'")
                    return base_name
        
        logger.warning(f"Could not find base collecte name for provider '{provider_name}'")
        return None


def main():
    parser = argparse.ArgumentParser(description='Rename PDF invoices based on content')
    parser.add_argument('directory', help='Directory containing PDF files to rename')
    parser.add_argument('--api-key', help='Google Gemini API key (or set GEMINI_API_KEY in .env file)')
    parser.add_argument('--csv-dir', default='.', help='Directory containing CSV files (default: current directory)')
    parser.add_argument('--dry-run', action='store_true', help='Perform dry run without actually renaming files')
    parser.add_argument('--status', action='store_true', help='Show current rate limit status and exit')
    
    args = parser.parse_args()
    
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
    required_files = ['Restaurants.csv', 'Prestataires.csv']
    for file in required_files:
        if not (csv_dir / file).exists():
            logger.error(f"Required CSV file not found: {csv_dir / file}")
            return
    
    # Initialize renamer
    try:
        renamer = PDFRenamer(args.api_key, csv_dir)
        
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


if __name__ == "__main__":
    main()
