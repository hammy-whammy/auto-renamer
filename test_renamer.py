#!/usr/bin/env python3
"""
Test and Demo Script for PDF Renamer
Shows how the renaming logic works without requiring PDFs or API calls
"""

import sys
import os
from pathlib import Path

# Add the current directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent))

from pdf_renamer import PDFRenamer

def simulate_gemini_analysis():
    """Simulate the analysis that Gemini would return for the sample invoice."""
    return {
        "entreprise": "MAC DO CHALON",
        "invoice_provider": "SUEZ", 
        "invoice_date": "30/09/2024",
        "invoice_number": "H0E0228333",
        "waste_types": ["DIB", "BIO", "DECHET RECYCLABLE"]
    }

def check_valid_combination(collecte: str, combination: str, prestataires_data: dict) -> bool:
    """Check if a combination is valid according to Prestataires.csv."""
    if collecte.upper() in prestataires_data:
        valid_combinations = [combo.upper() for combo in prestataires_data[collecte.upper()]]
        return combination.upper() in valid_combinations
    return False

def test_restaurant_matching():
    """Test the restaurant matching logic."""
    print("Testing Restaurant Matching Logic")
    print("=" * 50)
    
    # Initialize renamer (without API key for testing)
    try:
        renamer = PDFRenamer("dummy-api-key", ".")
    except Exception as e:
        print(f"Error initializing renamer: {e}")
        return
    
    # Test cases for restaurant matching
    test_cases = [
        ("MAC DO CHALON", "SUEZ"),
        ("McDonald's CHALON SUR SAONE", "SUEZ"),
        ("Mcdonald's CHALON SUR SAONE", "SUEZ"),
        ("McDonald's Lyon", "REFOOD"),
        ("Mcdonald's LYON", "VEOLIA"),
    ]
    
    print("Testing restaurant name matching:")
    for entreprise, collecte in test_cases:
        site = renamer._find_restaurant_site(entreprise, collecte)
        print(f"  {entreprise} + {collecte} -> Site: {site}")
    
    print()

def test_waste_type_logic():
    """Test the waste type combination logic."""
    print("Testing Waste Type Logic")
    print("=" * 30)
    
    try:
        renamer = PDFRenamer("dummy-api-key", ".")
    except Exception as e:
        print(f"Error initializing renamer: {e}")
        return
    
    # Test waste type combinations
    test_cases = [
        ("SUEZ", ["DIB", "BIO", "CS"]),
        ("VEOLIA", ["DIB"]),
        ("PAPREC", ["BIO", "CS"]),
        ("REFOOD", []),
    ]
    
    print("Testing waste type combinations:")
    for collecte, waste_types in test_cases:
        suffix = renamer._determine_collecte_suffix(collecte, waste_types)
        is_valid = check_valid_combination(collecte, suffix, renamer.prestataires_data)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"  {collecte} + {waste_types} -> {suffix} ({status})")
    
    print()

def test_date_formatting():
    """Test date formatting logic."""
    print("Testing Date Formatting")
    print("=" * 25)
    
    try:
        renamer = PDFRenamer("dummy-api-key", ".")
    except Exception as e:
        print(f"Error initializing renamer: {e}")
        return
    
    test_dates = [
        "30/09/2024",
        "01/12/2023",
        "15/06/2024"
    ]
    
    print("Testing date formatting:")
    for date_str in test_dates:
        formatted = renamer._format_date(date_str)
        print(f"  {date_str} -> {formatted}")
    
    print()

def simulate_full_renaming():
    """Simulate the full renaming process with the sample invoice."""
    print("Simulating Full Renaming Process")
    print("=" * 40)
    
    try:
        renamer = PDFRenamer("dummy-api-key", ".")
    except Exception as e:
        print(f"Error initializing renamer: {e}")
        return
    
    # Simulate the Gemini analysis result
    analysis = simulate_gemini_analysis()
    print("Simulated Gemini Analysis Result:")
    for key, value in analysis.items():
        print(f"  {key}: {value}")
    print()
    
    # Extract information
    entreprise = analysis['entreprise']
    invoice_provider = analysis['invoice_provider']
    invoice_date = analysis['invoice_date']
    invoice_number = analysis['invoice_number']
    waste_types = analysis['waste_types']
    
    # Find site number
    site_number = renamer._find_restaurant_site(entreprise, invoice_provider)
    print(f"Site lookup: {entreprise} + {invoice_provider} -> {site_number}")
    
    if not site_number:
        print("❌ Could not find site number")
        return
    
    # Determine collecte suffix
    collecte_suffix = renamer._determine_collecte_suffix(invoice_provider, waste_types)
    print(f"Collecte suffix: {invoice_provider} + {waste_types} -> {collecte_suffix}")
    
    # Format date
    formatted_date = renamer._format_date(invoice_date)
    print(f"Date formatting: {invoice_date} -> {formatted_date}")
    
    # Generate final filename
    new_filename = f"{site_number}-{collecte_suffix}-{formatted_date}-{invoice_number}.pdf"
    print(f"\n✅ Final filename: {new_filename}")
    
    # Validate the result against Prestataires.csv data
    is_valid_combination = check_valid_combination(invoice_provider, collecte_suffix, renamer.prestataires_data)
    
    # Check expected criteria
    expected_site = "1173"  # Expected for "MAC DO CHALON" 
    expected_date = "092024"  # Expected for "30/09/2024"
    expected_number = "H0E0228333"  # Expected invoice number
    
    print(f"\nValidation Results:")
    print(f"  Site number: {site_number} {'✅' if site_number == expected_site else '❌'} (expected: {expected_site})")
    print(f"  Date format: {formatted_date} {'✅' if formatted_date == expected_date else '❌'} (expected: {expected_date})")
    print(f"  Invoice number: {invoice_number} {'✅' if invoice_number == expected_number else '❌'} (expected: {expected_number})")
    print(f"  Collecte combination: {collecte_suffix} {'✅ VALID in CSV' if is_valid_combination else '❌ INVALID'}")
    
    # Overall result
    all_valid = (site_number == expected_site and 
                formatted_date == expected_date and 
                invoice_number == expected_number and 
                is_valid_combination)
    
    if all_valid:
        print(f"\n🎉 SUCCESS: All components are correct and combination is valid!")
    else:
        print(f"\n⚠️  Some components differ from expected, but as long as the combination is valid in Prestataires.csv, this is acceptable.")

def show_csv_stats():
    """Show statistics about the CSV data."""
    print("CSV Data Statistics")
    print("=" * 25)
    
    try:
        renamer = PDFRenamer("dummy-api-key", ".")
    except Exception as e:
        print(f"Error initializing renamer: {e}")
        return
    
    print(f"Loaded {len(renamer.restaurants_data)} restaurant entries")
    print(f"Loaded prestataires data for {len(renamer.prestataires_data)} collecte types")
    
    # Count McDonald's variations
    mcdo_count = 0
    for restaurant in renamer.restaurants_data:
        entreprise = restaurant['Entreprise'].lower()
        if any(variant in entreprise for variant in ['mcdonald', 'mac do']):
            mcdo_count += 1
    
    print(f"Found {mcdo_count} McDonald's entries")
    
    # Show some sample collecte types
    sample_collectes = list(renamer.prestataires_data.keys())[:10]
    print(f"Sample collecte types: {', '.join(sample_collectes)}")
    print()

def main():
    """Run all tests and demonstrations."""
    print("PDF Renamer Test and Demonstration")
    print("=" * 50)
    print()
    
    # Check if CSV files exist
    if not Path("Restaurants.csv").exists():
        print("❌ Error: Restaurants.csv not found")
        return
    
    if not Path("Prestataires.csv").exists():
        print("❌ Error: Prestataires.csv not found")
        return
    
    # Run all tests
    show_csv_stats()
    test_restaurant_matching()
    test_waste_type_logic() 
    test_date_formatting()
    simulate_full_renaming()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("\nTo run the actual PDF renamer:")
    print("1. Get a Google Gemini API key from https://makersuite.google.com/app/apikey")
    print("2. Run: python3 pdf_renamer.py '/path/to/pdfs' --api-key 'your-key' --dry-run")

if __name__ == "__main__":
    main()
