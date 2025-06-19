# Product Requirements Document (PRD)
## PDF Invoice Renamer - Automated Invoice Processing System

### Document Information
- **Version**: 1.1
- **Date**: June 16, 2025
- **Author**: Development Team
- **Status**: Updated with Logo Recognition Implementation

---

## 1. Executive Summary

### 1.1 Product Overview
The PDF Invoice Renamer is an intelligent automation tool that processes waste management invoices and renames them according to a standardized format using AI-powered content analysis. The system extracts key information from PDF invoices and generates structured filenames for efficient document management.

### 1.2 Business Problem
- Manual invoice processing is time-consuming and error-prone
- Inconsistent file naming conventions make document retrieval difficult
- Need for automated extraction of invoice metadata (site, provider, date, invoice number)

### 1.3 Solution
An automated Python-based system that:
- Extracts text and visual content from PDF invoices using PDF-to-image conversion
- Analyzes content using Google Gemini AI's multimodal capabilities to identify key information
- Recognizes company logos (PAPREC, SUEZ, VEOLIA, etc.) for accurate provider identification
- Prioritizes visual logo recognition over text-based provider extraction
- Matches restaurant/site data against a comprehensive database
- Generates standardized filenames following the format: `Site-Collecte-MonthYear-InvoiceNumber.pdf`

---

## 2. Product Goals & Success Metrics

### 2.1 Primary Goals
1. **Automation**: Reduce manual invoice processing time by 95%
2. **Accuracy**: Achieve 98%+ accuracy in filename generation
3. **Standardization**: Ensure consistent naming convention across all invoices

### 2.2 Success Metrics
- **Processing Speed**: Process 100+ invoices per hour
- **Error Rate**: <2% incorrect filename generation
- **User Adoption**: 100% of invoice processing staff using the system
- **Cost Savings**: 80% reduction in manual processing time

---

## 3. Target Users & Use Cases

### 3.1 Primary Users
- **Operations Staff**: Process daily invoice batches
- **Finance Team**: Organize invoices for accounting and auditing

### 3.2 Use Cases

#### UC1: Batch Invoice Processing
- **Actor**: Operations Staff
- **Goal**: Process multiple PDF invoices automatically
- **Scenario**: User selects a folder containing 50+ PDF invoices, system processes all files and renames them according to standard format

#### UC2: Single Invoice Processing
- **Actor**: Finance Team Member
- **Goal**: Process individual invoices as they arrive
- **Scenario**: User processes single invoice files for immediate filing

#### UC3: Dry Run Validation
- **Actor**: Quality Assurance
- **Goal**: Validate processing logic before actual renaming
- **Scenario**: User runs system in dry-run mode to preview filename changes

---

## 4. Functional Requirements

### 4.1 Core Features

#### F1: PDF Processing with Visual Analysis
- **Requirement**: Process PDF invoices using both visual and text-based analysis
- **Input**: PDF file path
- **Output**: Image representation + extracted text string
- **Features**:
  - PDF-to-image conversion for visual analysis
  - Text extraction as fallback method
  - First page processing only for cost optimization
- **Constraints**: Must handle various PDF formats and encoding

#### F2: AI-Powered Multimodal Content Analysis
- **Requirement**: Use Google Gemini AI's multimodal capabilities to analyze invoice content
- **Input**: PDF image (primary) or extracted text (fallback)
- **Output**: Structured JSON with:
  - Company name (entreprise)
  - Invoice provider/collector (with logo recognition priority)
  - Invoice date (DD/MM/YYYY format)
  - Invoice number
- **Features**:
  - Visual logo recognition for provider identification
  - Logo priority over text-based provider extraction
  - Hybrid fallback system for reliability
- **Constraints**: Must respect API rate limits (15/minute, 1500/day)

#### F2.1: Logo Recognition System
- **Requirement**: Identify waste management company logos visually
- **Supported Logos**: PAPREC, SUEZ, VEOLIA, and other waste management providers
- **Priority**: Logo identification takes precedence over text-based provider extraction
- **Fallback**: Automatic degradation to text-only analysis if image processing fails

#### F3: Restaurant/Site Matching
- **Requirement**: Match extracted company names to site numbers using CSV database
- **Features**:
  - Fuzzy matching for McDonald's variations
  - Normalization of restaurant names
  - Site number lookup based on company and collector
- **Data Source**: Restaurants.csv (443 entries)

#### F4: Collector Name Resolution
- **Requirement**: Map full provider names to base collector names
- **Features**:
  - Fuzzy matching (e.g., "SUEZ RV Centre Est" → "SUEZ")
  - Support for major collectors: SUEZ, VEOLIA, REFOOD, PAPREC, etc.
- **Data Source**: Prestataires.csv (52 collector types)

#### F5: Filename Generation
- **Requirement**: Generate standardized filenames
- **Format**: `{Site}-{Collecte}-{MMYYYY}-{InvoiceNumber}.pdf`
- **Examples**:
  - `1173-SUEZ-092024-H0E0228333.pdf`
  - `1332-REFOOD-102024-41371683 RI.pdf`
  - `322-SUEZ-102024-F7EF196665.pdf`

#### F6: Batch Processing
- **Requirement**: Process multiple PDF files in a directory
- **Features**:
  - Progress tracking and logging
  - Error handling for individual files
  - Summary reporting
  - Dry-run mode for validation

#### F7: Enhanced Logging System
- **Requirement**: Comprehensive logging and monitoring for transparent processing insights
- **Features**:
  - **Structured Console Output**: Real-time progress with detailed status updates
  - **Detailed Log Files**: Complete processing logs saved to `logs/` directory
  - **JSON Reports**: Machine-readable processing results with complete metadata
  - **Error Analysis**: Detailed failure reasons with actionable debugging information
  - **Processing Metrics**: Success rates, API usage, timing data, and performance analytics
- **Output Formats**:
  - Console: Real-time progress with structured formatting
  - Log Files: `logs/pdf_renaming_YYYYMMDD_HHMMSS.log`
  - JSON Reports: `logs/pdf_renaming_YYYYMMDD_HHMMSS.json`
- **Configuration**: Enable/disable detailed logging via `--disable-detailed-logging` flag

### 4.2 Data Management

#### F8: CSV Data Integration
- **Restaurants.csv**:
  - Columns: Site, Entreprise, Collecte
  - 443 restaurant entries
  - UTF-8 with BOM encoding support
- **Prestataires.csv**:
  - Columns: Collecte, Combinations
  - 52 collector types

#### F9: Configuration Management
- **Environment Variables**:
  - `GEMINI_API_KEY`: Google Gemini API authentication
  - `MAX_REQUESTS_PER_MINUTE`: Rate limiting (default: 15)
  - `MAX_REQUESTS_PER_DAY`: Daily limit (default: 1500)

---

## 5. Non-Functional Requirements

### 5.1 Performance
- **Processing Speed**: 1-3 seconds per PDF (excluding AI analysis time)
- **Memory Usage**: <500MB for typical batch processing
- **Throughput**: Process 1000+ invoices per day within API limits

### 5.2 Reliability
- **Uptime**: 99.9% availability during business hours
- **Error Handling**: Graceful failure with detailed error messages
- **Data Integrity**: No corruption of original PDF files

### 5.3 Security
- **API Key Protection**: Secure storage in environment variables
- **Data Privacy**: Process files locally, only send text to AI service
- **Access Control**: File system permissions for CSV databases

### 5.4 Usability
- **Command Line Interface**: Simple, intuitive commands
- **Progress Reporting**: Real-time status updates
- **Error Messages**: Clear, actionable error descriptions
- **Documentation**: Comprehensive README and inline help

### 5.5 Scalability
- **Batch Size**: Handle 100+ files in single operation
- **API Rate Limiting**: Automatic throttling to respect service limits
- **Resource Management**: Efficient memory usage for large batches

---

## 6. Technical Architecture

### 6.1 System Components

#### Core Modules
1. **PDFRenamer**: Main orchestration class
2. **PersistentRateLimiter**: Advanced API throttling with cross-restart persistence
3. **ProcessingLogger**: Comprehensive logging system with structured output and reporting
4. **Text Extraction**: PyPDF2-based PDF processing
5. **AI Analysis**: Google Gemini integration
6. **Data Matching**: CSV-based lookup and fuzzy matching

#### Dependencies
- **Python 3.8+**: Core runtime
- **PyPDF2**: PDF text extraction
- **google-generativeai**: AI content analysis with multimodal capabilities
- **pandas**: CSV data manipulation
- **python-dotenv**: Environment configuration
- **pdf2image**: PDF-to-image conversion for visual analysis
- **Pillow (PIL)**: Image processing and manipulation

### 6.2 Data Flow
1. PDF file input
2. **PDF-to-image conversion** for visual analysis (with text extraction fallback)
3. **Multimodal AI analysis** via Gemini API (image + text)
4. **Logo recognition** for provider identification (priority over text)
5. Restaurant/site matching against CSV data
6. Collector name resolution
8. Filename generation
9. File renaming (or dry-run preview)

### 6.3 Rate Limiting & API Management

#### Persistent Rate Limiter
The system implements **PersistentRateLimiter** - an intelligent rate limiting solution that stores usage data across program runs to respect Google Gemini API free tier limits.

**Key Features:**
- ✅ **Persistent Storage**: Local `.api_usage.json` file tracks usage across restarts
- ✅ **Dual Rate Limiting**: 15 requests/minute, 1,500 requests/day
- ✅ **Historical Tracking**: 7-day usage history with automatic cleanup
- ✅ **Enhanced CLI**: Status checking, weekly summaries, counter reset
- ✅ **Privacy-Focused**: All data stays local, no cloud dependencies

**Data Structure:**
```json
{
  "daily_requests": {
    "2025-06-04": 23,
    "2025-06-03": 67,
    "2025-06-02": 45
  },
  "minute_requests": [
    "2025-06-04T13:19:43.313122",
    "2025-06-04T13:18:32.124567"
  ],
  "last_updated": "2025-06-04T13:20:12.585203"
}
```

**CLI Commands:**
```bash
# Current status with history
python pdf_renamer.py --status

# Weekly usage summary
python pdf_renamer.py --weekly-summary

# Reset counter (emergency use)
python pdf_renamer.py --reset-counter
```

#### Alternative Monitoring Solutions
For enterprise users requiring more robust tracking, Google Cloud Monitoring provides official API usage metrics:

**Setup Requirements:**
- Google Cloud Project with billing enabled
- Cloud Monitoring API access
- Service Account credentials
- Additional dependencies: `google-cloud-monitoring`

**Pros/Cons Comparison:**

| Feature | Local Persistent | Google Cloud Monitoring |
|---------|------------------|------------------------|
| Setup Complexity | ✅ Simple | ❌ Complex |
| Cross-Device Sync | ❌ Single machine | ✅ Multi-device |
| Privacy | ✅ Local only | ❌ Cloud-based |
| Cost | ✅ Free | ❌ Usage charges |
| Accuracy | ✅ Real-time | ❌ May have delays |
| Enterprise Features | ❌ Basic | ✅ Dashboards, alerts |

**Recommendation**: Use built-in persistent tracking for most use cases. Consider Google Cloud Monitoring only for enterprise requirements.

### 6.4 Enhanced Logging System

The system includes a comprehensive **ProcessingLogger** that provides transparent insights into every aspect of the PDF processing workflow, making troubleshooting and optimization straightforward.

#### Key Features
- ✅ **Multi-format Output**: Console, detailed log files, and JSON reports
- ✅ **Structured Information**: Organized data for each processing step
- ✅ **Error Analysis**: Detailed failure reasons with actionable debugging information
- ✅ **Performance Metrics**: Processing time, API usage, and success rate tracking
- ✅ **Session Management**: Complete processing session data with unique identifiers

#### Output Formats

**1. Real-time Console Output**
```
📊 Rate Limit Status:
  Today: 24/1500 (1476 remaining)
  This minute: 0/15 (15 remaining)

--------------------------------------------------
Processing file 1/3: invoice_sample.pdf
✅ SUCCESS: Would rename 'invoice_sample.pdf' → '1173-SUEZ-092024-H0E0228333.pdf'
   📊 Extracted data:
     Restaurant: MAC DO CHALON
     Site: 1173
     Collecte: SUEZ
     Invoice #: H0E0228333
     Date: 30/09/2024
```

**2. Detailed Log Files** (`logs/pdf_renaming_YYYYMMDD_HHMMSS.log`)
```
2025-06-04 15:03:04 | INFO     | ================================================================================
2025-06-04 15:03:04 | INFO     | PDF INVOICE RENAMING SESSION STARTED
2025-06-04 15:03:04 | INFO     | ================================================================================
2025-06-04 15:03:04 | INFO     | Session ID: 20250604_150304
2025-06-04 15:03:04 | INFO     | Processing file 1/5: invoice_001.pdf
2025-06-04 15:03:05 | INFO     | ✅ SUCCESS: Would rename 'invoice_001.pdf' → '1173-SUEZ-092024-H0E0228333.pdf'
2025-06-04 15:03:05 | ERROR    | ❌ FAILED: invoice_002.pdf
2025-06-04 15:03:05 | ERROR    |    Reason: Could not find site number for 'BURGER KING LYON' with collecte 'VEOLIA'
2025-06-04 15:03:05 | ERROR    |    Details: similar_restaurants: [{'name': 'Burger King LYON', 'site': '2145', 'collecte': 'SUEZ'}]
```

**3. Machine-readable JSON Reports** (`logs/pdf_renaming_YYYYMMDD_HHMMSS.json`)
```json
{
  "session_info": {
    "start_time": "2025-06-04T15:03:04.137451",
    "end_time": "2025-06-04T15:05:15.842123",
    "duration_seconds": 131.7,
    "session_id": "20250604_150304"
  },
  "summary": {
    "total_files": 5,
    "successful": 3,
    "failed": 1,
    "skipped": 1,
    "api_requests_used": 4
  },
  "detailed_results": [
    {
      "status": "success",
      "original_name": "invoice_001.pdf",
      "new_name": "1173-SUEZ-092024-H0E0228333.pdf",
      "extracted_data": {
        "restaurant_name": "MAC DO CHALON",
        "site_number": "1173",
        "collecte": "SUEZ",
        "invoice_number": "H0E0228333",
        "invoice_date": "30/09/2024"
      }
    }
  ]
}
```

#### Enhanced Error Reporting
When files fail to process, the logging system provides:
- **Missing Data Analysis**: Identifies which required fields couldn't be extracted
- **Lookup Failure Details**: Lists similar restaurant matches for debugging
- **PDF Quality Issues**: Reports on file size and text extraction problems
- **API Error Details**: Specific Gemini API error information and resolution suggestions

#### Configuration Options
```bash
# Standard processing with enhanced logging
python pdf_renamer.py /path/to/invoices --dry-run

# Disable detailed file logging (console only)
python pdf_renamer.py /path/to/invoices --dry-run --disable-detailed-logging
```

#### Log File Management
- **Automatic Generation**: Unique session IDs with timestamp-based filenames
- **Directory Structure**: All logs stored in `logs/` directory
- **Data Persistence**: Complete processing history maintained for analysis
- **No Automatic Cleanup**: Manual log management required for long-term storage

### 6.5 Integration Points
- **Google Gemini API**: External AI service for content analysis
- **Local File System**: PDF processing and CSV data access
- **Environment Configuration**: Secure API key management

---

## 7. User Interface Requirements

### 7.1 Command Line Interface
```bash
# Basic usage
python pdf_renamer.py /path/to/invoices

# Processing modes
python pdf_renamer.py /path/to/invoices --dry-run          # Test mode with preview
python pdf_renamer.py /path/to/invoices                    # Live processing mode

# Enhanced logging options
python pdf_renamer.py /path/to/invoices --dry-run          # Full logging (default)
python pdf_renamer.py /path/to/invoices --disable-detailed-logging  # Console only

# Configuration options
python pdf_renamer.py /path/to/invoices --csv-dir ./data   # Custom CSV directory

# Status and monitoring
python pdf_renamer.py --status                             # Current API usage
python pdf_renamer.py --weekly-summary                     # Weekly breakdown
python pdf_renamer.py --reset-counter                      # Reset daily counter
```

### 7.2 Output Formatting

#### Enhanced Logging Output
- **Structured Console**: Real-time progress with detailed status, emojis, and organized sections
- **Session Management**: Unique session IDs with timestamp-based identification
- **Detailed Log Files**: Complete processing history with timestamped entries
- **JSON Reports**: Machine-readable data for integration and analysis
- **Error Analysis**: Comprehensive failure details with debugging information

#### Log File Structure
```
logs/
├── pdf_renaming_20250604_150304.log    # Human-readable detailed log
├── pdf_renaming_20250604_150304.json   # Machine-readable processing report
├── pdf_renaming_20250604_163245.log    # Next session log
└── pdf_renaming_20250604_163245.json   # Next session report
```

#### Performance Metrics
- **Processing Speed**: Per-file timing and overall session duration
- **Success Rate Analysis**: Detailed success/failure/skip statistics
- **API Usage Tracking**: Request count and quota utilization
- **Error Pattern Recognition**: Common failure reasons and resolution suggestions

#### Traditional Output
- **Progress Logging**: Timestamped status messages (legacy format)
- **Summary Report**: Success/failure statistics
- **Error Details**: Specific failure reasons for each file
- **Rate Limit Status**: API usage tracking

---

## 8. Quality Assurance

### 8.1 Testing Strategy
- **Unit Tests**: Individual component validation
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Batch processing validation
- **Edge Case Testing**: Malformed PDFs, missing data

### 8.2 Validation Criteria
- **Accuracy Testing**: Manual verification of 100+ processed invoices
- **Performance Benchmarking**: Processing time measurements
- **Error Rate Analysis**: Failure pattern identification
- **User Acceptance Testing**: Operations team validation

### 8.3 Enhanced Log-based Troubleshooting

The enhanced logging system transforms debugging from guesswork into systematic analysis:

#### Common Error Patterns & Solutions

**1. Restaurant Lookup Failures**
```
❌ FAILED: invoice_sample.pdf
   Reason: Could not find site number for 'McDONALD PARIS' with collecte 'SUEZ'
   Details: similar_restaurants: [{'name': "McDonald's PARIS RÉPUBLIQUE", 'site': '1234', 'collecte': 'SUEZ'}]
```
**Resolution**: Restaurant name variation not in CSV - add to Restaurants.csv or check for typos

**2. AI Extraction Issues**
```
❌ FAILED: invoice_sample.pdf
   Reason: Missing required fields: invoice_number, invoice_date
   Details: available_fields: {'entreprise': 'MAC DO', 'invoice_provider': 'SUEZ'}
```
**Resolution**: PDF content unclear - manually verify invoice number and date visibility

**3. Rate Limit Management**
```
⏳ Rate limit reached: Used 15/15 requests this minute
   Waiting 45.2 seconds...
```
**Resolution**: Automatic system handling - processing continues after wait period

#### Log Analysis Workflows

**Batch Processing Validation**
```bash
# Process with full logging
python pdf_renamer.py /invoices/batch1 --dry-run

# Review errors before live run
cat logs/pdf_renaming_*.log | grep "FAILED\|ERROR"

# Analyze success patterns
grep "SUCCESS" logs/pdf_renaming_*.log | wc -l
```

**JSON Report Analysis**
```bash
# Extract failure reasons for analysis
cat logs/pdf_renaming_*.json | jq '.detailed_results[] | select(.status=="failed") | .reason'

# Calculate processing metrics
cat logs/pdf_renaming_*.json | jq '.summary | {success_rate: (.successful/.total_files * 100)}'
```

#### Performance Monitoring
- **Processing Time**: Session duration and per-file timing analysis
- **Success Rate Tracking**: Historical success/failure patterns
- **API Efficiency**: Request optimization and quota utilization
- **Error Trend Analysis**: Common failure patterns for CSV data improvements

---

## 9. Deployment & Operations

### 9.1 Installation Requirements
- Python 3.8+ runtime environment
- Required Python packages (via requirements.txt):
  - PyPDF2==3.0.1 (PDF text extraction)
  - google-generativeai==0.3.2 (AI analysis)
  - pdf2image==1.17.0 (PDF-to-image conversion)
  - Pillow==10.0.1 (image processing)
  - python-dotenv==1.0.0 (environment configuration)
  - pandas (CSV data manipulation)
- Google Gemini API key with multimodal capabilities
- Access to CSV database files (Liste des clients.xlsx, Prestataires.csv)

### 9.2 Configuration
- Environment variable setup (.env file)
- CSV database placement
- Directory permissions configuration

### 9.3 Monitoring & Usage Tracking

#### Built-in Persistent Monitoring
The system includes comprehensive API usage tracking via **PersistentRateLimiter**:

**Local Tracking Features:**
- **Cross-restart persistence**: `.api_usage.json` file maintains usage across program runs
- **Real-time rate limiting**: Automatic throttling to respect 15/minute, 1,500/day limits
- **Historical analysis**: 7-day usage tracking with automatic cleanup
- **Status reporting**: Detailed usage statistics and remaining quotas

**Monitoring Commands:**
```bash
# Current usage status
python pdf_renamer.py --status

# Weekly breakdown analysis
python pdf_renamer.py --weekly-summary

# Emergency counter reset
python pdf_renamer.py --reset-counter
```

**Sample Output:**
```
📊 Rate Limit Status:
  Today: 23/1500 (1477 remaining)
  This minute: 2/15 (13 remaining)
  Total lifetime requests: 156

📈 Recent Usage (last 7 days):
    2025-06-02: 45 requests
    2025-06-03: 67 requests
    2025-06-04: 23 requests
```

#### Advanced Monitoring (Enterprise Option)
For organizations requiring enhanced monitoring capabilities, **Google Cloud Monitoring** integration is available:

**Setup Requirements:**
1. **Google Cloud Project**: GCP project with billing enabled
2. **Cloud Monitoring API**: Enable monitoring service
3. **Service Account**: Create credentials for programmatic access
4. **Dependencies**: Install `google-cloud-monitoring` package

**Implementation Overview:**
```python
from google.cloud import monitoring_v3
from datetime import datetime, timedelta

def get_daily_api_usage(project_id: str, credentials_path: str) -> int:
    """Get daily API request count from Google Cloud Monitoring."""
    client = monitoring_v3.MetricServiceClient.from_service_account_file(credentials_path)
    project_name = f"projects/{project_id}"
    
    # Query for API request count metric
    interval = monitoring_v3.TimeInterval({
        "end_time": {"seconds": int(datetime.now().timestamp())},
        "start_time": {"seconds": int((datetime.now() - timedelta(days=1)).timestamp())}
    })
    
    results = client.list_time_series(
        request={
            "name": project_name,
            "filter": 'metric.type="serviceruntime.googleapis.com/api/request_count"',
            "interval": interval
        }
    )
    
    return sum(point.value.int64_value for result in results for point in result.points)
```

**MQL Query Example:**
```mql
fetch consumed_api
| metric 'serviceruntime.googleapis.com/api/request_count'
| filter (resource.service == 'aiplatform.googleapis.com')
| group_by 1d, [row_count: row_count()]
| every 1d
```

**Comparison Matrix:**

| Feature | Built-in Persistent | Google Cloud Monitoring |
|---------|-------------------|------------------------|
| **Setup** | ✅ No setup needed | ❌ Complex GCP setup |
| **Cost** | ✅ Free | ❌ Usage-based charges |
| **Accuracy** | ✅ Real-time | ❌ May have 5min delay |
| **Multi-device** | ❌ Single machine | ✅ Cross-device sync |
| **Privacy** | ✅ Local data only | ❌ Cloud-based |
| **Dashboards** | ❌ CLI only | ✅ Rich visualizations |
| **Alerting** | ❌ Manual checking | ✅ Automated alerts |
| **Enterprise** | ❌ Basic features | ✅ Advanced analytics |

**Implementation Decision Framework:**
- **Use Built-in Monitoring** for: Single-user setups, privacy requirements, simple usage tracking
- **Use Cloud Monitoring** for: Multi-user environments, enterprise compliance, advanced analytics needs

#### Additional Monitoring Metrics
- **Enhanced Logging Integration**: Complete processing transparency via ProcessingLogger
- **Session-based Analysis**: Detailed JSON reports for each processing session
- **Error Pattern Tracking**: Systematic failure analysis with actionable debugging information
- **Performance Analytics**: Processing time, success rates, and API efficiency metrics
- **Historical Trending**: Long-term usage patterns and system optimization insights
- **Error Rate Monitoring**: Failure pattern analysis via structured log files
- **Performance Metrics**: Processing time tracking per file
- **Success Rate Reporting**: Accuracy measurements and validation

---

## 10. Risk Assessment

### 10.1 Technical Risks
- **API Rate Limiting**: Mitigation via intelligent throttling
- **PDF Format Variations**: Robust text extraction handling
- **AI Analysis Accuracy**: Fallback processing for edge cases
- **CSV Data Integrity**: Validation and error handling

### 10.2 Business Risks
- **Processing Accuracy**: Comprehensive testing and validation
- **User Adoption**: Training and documentation
- **Data Security**: Secure API key management

---

## 11. Future Enhancements

### 11.1 Short-term (Next 3 months)
- **Web Interface**: Browser-based file upload and processing
- **Advanced Reporting**: Detailed analytics and insights using enhanced logging data
- **Log Dashboard**: Visual interface for processing history and error analysis
- **Multi-language Support**: Support for additional languages

### 11.2 Long-term (6+ months)
- **OCR Integration**: Enhanced text extraction for scanned PDFs
- **Machine Learning**: Custom model training for improved accuracy
- **Database Integration**: Direct database storage of invoice metadata
- **API Service**: RESTful API for system integration

---

## 12. Appendices

### 12.1 File Format Specification
```
Target Filename Format:
{Site}-{Collecte}-{MMYYYY}-{InvoiceNumber}.pdf

Where:
- Site: 3-4 digit restaurant site number
- Collecte: Base collector name (SUEZ, REFOOD, etc.)
- MMYYYY: Invoice month and year
- InvoiceNumber: Original invoice identifier
```

### 12.2 Supported Collectors
SUEZ, VEOLIA, REFOOD, PAPREC, ELISE, DERICHEBOURG, ORTEC, ATESIS, BRANGEON, COLLECTEA, and others as defined in Prestataires.csv

### 12.2.1 Logo Recognition Capabilities
The system's visual analysis can identify the following company logos:
- **PAPREC**: Green and white logo with company name
- **SUEZ**: Blue corporate logo design
- **VEOLIA**: Green corporate branding and logo
- **Other Waste Management Providers**: Additional logos as defined in Prestataires.csv

**Logo Priority System**: When both text and logo information are available, the system prioritizes logo identification for provider determination. For example, if an invoice shows "RUBO" in the text but displays a PAPREC logo, the system correctly identifies PAPREC as the provider.

**Example Success Case**: 
- **Input**: PAPREC PDF with "RUBO" text content
- **Logo Detection**: PAPREC logo identified visually
- **Output**: `1036-PAPREC-102024-PRE24100414.pdf` (correct provider)

### 12.3 Enhanced Logging System

#### Log File Structure and Formats

**Console Output Example:**
```
📊 Rate Limit Status:
  Today: 24/1500 (1476 remaining)
  This minute: 0/15 (15 remaining)

--------------------------------------------------
Processing file 1/3: invoice_sample.pdf
✅ SUCCESS: Would rename 'invoice_sample.pdf' → '1173-SUEZ-092024-H0E0228333.pdf'
   📊 Extracted data:
     Restaurant: MAC DO CHALON
     Site: 1173
     Collecte: SUEZ
     Invoice #: H0E0228333
     Date: 30/09/2024
```

**Log File Format** (`logs/pdf_renaming_YYYYMMDD_HHMMSS.log`):
```
2025-06-04 15:03:04 | INFO     | ================================================================================
2025-06-04 15:03:04 | INFO     | PDF INVOICE RENAMING SESSION STARTED
2025-06-04 15:03:04 | INFO     | ================================================================================
2025-06-04 15:03:04 | INFO     | Session ID: 20250604_150304
2025-06-04 15:03:04 | INFO     | Processing file 1/5: invoice_001.pdf
2025-06-04 15:03:05 | INFO     | ✅ SUCCESS: Would rename 'invoice_001.pdf' → '1173-SUEZ-092024-H0E0228333.pdf'
2025-06-04 15:03:05 | ERROR    | ❌ FAILED: invoice_002.pdf
2025-06-04 15:03:05 | ERROR    |    Reason: Could not find site number for 'BURGER KING LYON' with collecte 'VEOLIA'
```

**JSON Report Structure** (`logs/pdf_renaming_YYYYMMDD_HHMMSS.json`):
```json
{
  "session_info": {
    "start_time": "2025-06-04T15:03:04.137451",
    "end_time": "2025-06-04T15:05:15.842123",
    "duration_seconds": 131.7,
    "session_id": "20250604_150304"
  },
  "summary": {
    "total_files": 5,
    "successful": 3,
    "failed": 1,
    "skipped": 1,
    "api_requests_used": 4
  },
  "detailed_results": [
    {
      "status": "success",
      "original_name": "invoice_001.pdf",
      "new_name": "1173-SUEZ-092024-H0E0228333.pdf",
      "extracted_data": {
        "restaurant_name": "MAC DO CHALON",
        "site_number": "1173",
        "collecte": "SUEZ",
        "invoice_number": "H0E0228333",
        "invoice_date": "30/09/2024"
      },
      "timestamp": "2025-06-04T15:03:05.234567"
    },
    {
      "status": "failed",
      "filename": "invoice_002.pdf",
      "reason": "Could not find site number for 'BURGER KING LYON' with collecte 'VEOLIA'",
      "details": {
        "restaurant_name": "BURGER KING LYON",
        "base_collecte": "VEOLIA",
        "similar_restaurants": [
          {"name": "Burger King LYON", "site": "2145", "collecte": "SUEZ"}
        ]
      },
      "timestamp": "2025-06-04T15:03:05.987654"
    }
  ]
}
```

#### Command Line Options for Enhanced Logging
```bash
# Standard processing with full logging (default)
python pdf_renamer.py /path/to/invoices --dry-run

# Disable detailed file logging (console output only)
python pdf_renamer.py /path/to/invoices --dry-run --disable-detailed-logging

# All processing modes with enhanced logging
python pdf_renamer.py /path/to/invoices                    # Live mode
python pdf_renamer.py /path/to/invoices --dry-run          # Test mode
python pdf_renamer.py /path/to/invoices --csv-dir /custom/path
```

#### Log Analysis Commands
```bash
# Review processing errors
cat logs/pdf_renaming_*.log | grep "FAILED\|ERROR"

# Extract success rate from JSON
cat logs/pdf_renaming_*.json | jq '.summary | {success_rate: (.successful/.total_files * 100)}'

# Find common failure patterns
cat logs/pdf_renaming_*.json | jq '.detailed_results[] | select(.status=="failed") | .reason' | sort | uniq -c
```

### 12.4 API Usage Tracking Files

#### Local Storage File: `.api_usage.json`
```json
{
  "daily_requests": {
    "2025-06-04": 23,
    "2025-06-03": 67,
    "2025-06-02": 45
  },
  "minute_requests": [
    "2025-06-04T13:19:43.313122",
    "2025-06-04T13:18:32.124567"
  ],
  "last_updated": "2025-06-04T13:20:12.585203"
}
```

**Features:**
- Automatic creation and management
- Git-ignored for privacy
- 7-day data retention with automatic cleanup
- Cross-restart persistence

#### Environment Variables for Cloud Monitoring
```bash
# Optional: Google Cloud Monitoring integration
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
ENABLE_CLOUD_MONITORING=false
```

### 12.5 Error Codes and Enhanced Debugging

#### Standard Error Codes
- **E001**: PDF text extraction failure
- **E002**: AI analysis timeout or failure
- **E003**: Restaurant/site matching failure
- **E004**: Collector name resolution failure
- **E005**: Invalid date format
- **E006**: Missing required fields

#### Enhanced Debugging Information
With the enhanced logging system, each error includes:

**Detailed Context**: Complete processing state when error occurred
**Similar Matches**: For lookup failures, shows close restaurant/collector matches
**Data Availability**: Lists which fields were successfully extracted vs missing
**Resolution Suggestions**: Actionable steps to resolve common issues
**Processing Metrics**: Timing and performance data for optimization

#### Common Debugging Workflows

**Restaurant Lookup Issues (E003)**:
1. Check `similar_restaurants` in log details
2. Verify restaurant name variations in Restaurants.csv
3. Confirm collector spelling matches Prestataires.csv

**AI Extraction Problems (E002, E006)**:
1. Review `available_fields` vs `missing_fields` in error details
2. Check PDF text quality and length in log output
3. Verify invoice format matches expected patterns

**Performance Issues**:
1. Analyze `duration_seconds` in JSON session data
2. Review API wait times and rate limiting messages
3. Check processing time per file for optimization opportunities

---

**Document Status**: ✅ Complete with Enhanced Logging Integration
**Last Updated**: June 4, 2025
**Next Review**: December 2025

**Recent Updates**:
- ✅ Enhanced Logging System fully integrated (ProcessingLogger)
- ✅ Comprehensive troubleshooting workflows added
- ✅ JSON reporting and structured output documented
- ✅ Log analysis commands and debugging procedures included
