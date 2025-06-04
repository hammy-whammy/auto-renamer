# PDF Invoice Renamer

Automatically renames PDF invoices based on their content using AI analysis and CSV lookup tables.

## Features

- **AI-Powered Content Analysis**: Uses Google Gemini to extract key information from invoice PDFs
- **Intelligent Restaurant Matching**: Handles various McDonald's name variations (MAC DO, McDonald's, etc.)
- **Waste Type Detection**: Automatically detects DIB, BIO, CS waste types from invoice content
- **CSV-Based Lookup**: Cross-references restaurant and prestataire data for accurate site numbers
- **Safe Operation**: Includes dry-run mode to preview changes before execution
- **Comprehensive Logging**: Detailed logging for troubleshooting and verification

## Naming Convention

Files are renamed using the following format:
```
Site-Collecte(+CS/BIO/DIB)-InvoiceMonthYear-InvoiceNumber.pdf
```

### Example
- Original: `invoice_123.pdf`
- Renamed: `1173-SUEZBIODIBCS-092024-H0E0228333.pdf`

Where:
- `1173` = Site number from Restaurants.csv
- `SUEZBIODIBCS` = Collecte provider + waste types (DIB + BIO + CS)
- `092024` = Invoice month/year (September 2024)
- `H0E0228333` = Invoice number

## Requirements

- Python 3.7+
- Google Gemini API key
- Required CSV files: `Restaurants.csv`, `Prestataires.csv`

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd auto-renamer
   ```

2. **Install dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit .env and add your Google Gemini API key
   nano .env
   ```
   
   Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)

4. **Ensure CSV files are present**:
   - `Restaurants.csv` - Restaurant site mapping
   - `Prestataires.csv` - Waste collector combinations

## Usage

### Basic Usage (Recommended - with .env file)

```bash
python3 pdf_renamer.py "/path/to/invoice/directory"
```

### Start with Dry Run (Recommended)

```bash
python3 pdf_renamer.py "/path/to/invoice/directory" --dry-run
```

### Alternative: Direct API Key (Not Recommended for Security)

```bash
python3 pdf_renamer.py "/path/to/invoice/directory" --api-key "your-gemini-api-key"
```

## Command Line Options

- `directory`: Path to directory containing PDF files (required)
- `--api-key`: Google Gemini API key (required)
- `--csv-dir`: Directory containing CSV files (default: current directory)
- `--dry-run`: Preview changes without actually renaming files

## How It Works

1. **PDF Text Extraction**: Extracts text from the first page of each PDF
2. **AI Analysis**: Uses Google Gemini to identify:
   - Restaurant/company name
   - Invoice provider (collecte)
   - Invoice date
   - Invoice number
   - Waste types (DIB, BIO, CS)
3. **Data Lookup**: Cross-references extracted data with CSV files to find:
   - Site number from restaurant name and collecte
   - Valid waste type combinations
4. **Filename Generation**: Creates new filename following the required format
5. **Safe Renaming**: Renames files (or shows preview in dry-run mode)

## Supported Restaurant Name Variations

The script intelligently handles McDonald's name variations:
- McDonald's
- Mcdonald's 
- McDonalds
- MAC DO
- Mac Do
- MacDonald's
- And various combinations with location names

## Waste Type Detection

Automatically detects and categorizes:
- **DIB**: Déchets Industriels Banals
- **BIO**: Biodegradable waste
- **CS**: Déchets recyclables (Collecte Sélective)

## Error Handling

- **Missing Information**: Logs detailed errors when required data cannot be extracted
- **File Conflicts**: Skips files if target filename already exists
- **Invalid Data**: Validates against CSV data and provides feedback
- **API Errors**: Handles Gemini API failures gracefully

## Output Summary

After processing, the script provides a comprehensive summary:
- Number of files successfully processed
- Number of files that failed with reasons
- Number of files skipped with reasons

## Troubleshooting

### Common Issues

1. **"Could not extract text from PDF"**
   - PDF may be image-based or corrupted
   - Try using a different PDF reader/converter

2. **"Could not find site number"**
   - Restaurant name may not match CSV data exactly
   - Check if the restaurant exists in Restaurants.csv
   - Verify the collecte provider name

3. **"Missing required information"**
   - Invoice may have unusual format
   - Check if all required fields are present in the PDF

4. **API Errors**
   - Verify your Gemini API key is correct and active
   - Check your internet connection
   - Ensure you haven't exceeded API rate limits

### Validation Steps

1. **Always run dry-run first** to preview changes
2. **Check the log output** for any warnings or errors
3. **Verify a few renamed files manually** to ensure accuracy
4. **Keep backups** of original files

## File Structure

```
auto-renamer/
├── pdf_renamer.py          # Main script
├── requirements.txt        # Python dependencies
├── setup.sh               # Setup script
├── README.md              # This file
├── Restaurants.csv        # Restaurant/site data
└── Prestataires.csv       # Collecte provider data
```

## CSV File Format

### Restaurants.csv
```csv
Site; Entreprise; Collecte; Collecte en cours
1173;Mcdonald's CHALON SUR SAONE;SUEZ;OUI
```

### Prestataires.csv
```csv
Collecte;Combinations;
SUEZ;SUEZDIBBIO,SUEZBIO,SUEZDIBCS,SUEZDIB,SUEZBIODIBCS;
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the log output for specific error messages
3. Ensure your CSV files are properly formatted
4. Verify your API key is working

## Security Notes

- Keep your API key secure and never commit it to version control
- Use environment variables for API keys in production
- The script only reads PDF content for analysis - no data is stored or transmitted beyond the API call