# Product Requirements Document (PRD)
## PDF Invoice Renamer - Automated Invoice Processing System

### Document Information
- **Version**: 1.0
- **Date**: June 4, 2025
- **Author**: Development Team
- **Status**: Implementation Complete

---

## 1. Executive Summary

### 1.1 Product Overview
The PDF Invoice Renamer is an intelligent automation tool that processes waste management invoices and renames them according to a standardized format using AI-powered content analysis. The system extracts key information from PDF invoices and generates structured filenames for efficient document management.

### 1.2 Business Problem
- Manual invoice processing is time-consuming and error-prone
- Inconsistent file naming conventions make document retrieval difficult
- Need for automated extraction of invoice metadata (site, provider, date, invoice number)
- Requirement to categorize waste types (DIB, BIO, CS) for regulatory compliance

### 1.3 Solution
An automated Python-based system that:
- Extracts text from PDF invoices using OCR
- Analyzes content using Google Gemini AI to identify key information
- Matches restaurant/site data against a comprehensive database
- Generates standardized filenames following the format: `Site-Collecte(+WasteTypes)-MonthYear-InvoiceNumber.pdf`

---

## 2. Product Goals & Success Metrics

### 2.1 Primary Goals
1. **Automation**: Reduce manual invoice processing time by 95%
2. **Accuracy**: Achieve 98%+ accuracy in filename generation
3. **Standardization**: Ensure consistent naming convention across all invoices
4. **Compliance**: Proper categorization of waste types for regulatory requirements

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
- **Compliance Officers**: Ensure proper waste type categorization

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

#### F1: PDF Text Extraction
- **Requirement**: Extract text content from PDF invoices (first page only for cost optimization)
- **Input**: PDF file path
- **Output**: Extracted text string
- **Constraints**: Must handle various PDF formats and encoding

#### F2: AI-Powered Content Analysis
- **Requirement**: Use Google Gemini AI to analyze invoice content
- **Input**: Extracted PDF text
- **Output**: Structured JSON with:
  - Company name (entreprise)
  - Invoice provider/collector
  - Invoice date (DD/MM/YYYY format)
  - Invoice number
  - Waste types array
- **Constraints**: Must respect API rate limits (15/minute, 1500/day)

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

#### F5: Waste Type Classification
- **Requirement**: Identify and categorize waste types from invoice content
- **Supported Types**:
  - **DIB**: Déchets Industriels Banals
  - **BIO**: Biodegradable waste
  - **CS**: Collecte Sélective (recyclable waste)
- **Output**: Combined waste type suffix (e.g., DIBCS, BIOCS, DIBBIOCS)

#### F6: Filename Generation
- **Requirement**: Generate standardized filenames
- **Format**: `{Site}-{Collecte}{WasteTypes}-{MMYYYY}-{InvoiceNumber}.pdf`
- **Examples**:
  - `1173-SUEZDIBBIOCS-092024-H0E0228333.pdf`
  - `1332-REFOOD-102024-41371683 RI.pdf`
  - `322-SUEZDIBCS-102024-F7EF196665.pdf`

#### F7: Batch Processing
- **Requirement**: Process multiple PDF files in a directory
- **Features**:
  - Progress tracking and logging
  - Error handling for individual files
  - Summary reporting
  - Dry-run mode for validation

### 4.2 Data Management

#### F8: CSV Data Integration
- **Restaurants.csv**:
  - Columns: Site, Entreprise, Collecte
  - 443 restaurant entries
  - UTF-8 with BOM encoding support
- **Prestataires.csv**:
  - Columns: Collecte, Combinations
  - 52 collector types with valid waste combinations

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
3. **Text Extraction**: PyPDF2-based PDF processing
4. **AI Analysis**: Google Gemini integration
5. **Data Matching**: CSV-based lookup and fuzzy matching

#### Dependencies
- **Python 3.8+**: Core runtime
- **PyPDF2**: PDF text extraction
- **google-generativeai**: AI content analysis
- **pandas**: CSV data manipulation
- **python-dotenv**: Environment configuration

### 6.2 Data Flow
1. PDF file input
2. Text extraction (first page only)
3. AI analysis via Gemini API
4. Restaurant/site matching against CSV data
5. Collector name resolution
6. Waste type classification
7. Filename generation
8. File renaming (or dry-run preview)

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

### 6.4 Integration Points
- **Google Gemini API**: External AI service for content analysis
- **Local File System**: PDF processing and CSV data access
- **Environment Configuration**: Secure API key management

---

## 7. User Interface Requirements

### 7.1 Command Line Interface
```bash
# Basic usage
python pdf_renamer.py /path/to/invoices

# With options
python pdf_renamer.py /path/to/invoices --dry-run --csv-dir ./data

# Status checking
python pdf_renamer.py --status
```

### 7.2 Output Formatting
- **Progress Logging**: Timestamped status messages
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

---

## 9. Deployment & Operations

### 9.1 Installation Requirements
- Python 3.8+ runtime environment
- Required Python packages (via requirements.txt)
- Google Gemini API key
- Access to CSV database files

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
- **Error Rate Monitoring**: Failure pattern analysis via log files
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
- **Compliance Requirements**: Waste type classification accuracy
- **Data Security**: Secure API key management

---

## 11. Future Enhancements

### 11.1 Short-term (Next 3 months)
- **Web Interface**: Browser-based file upload and processing
- **Advanced Reporting**: Detailed analytics and insights
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
{Site}-{Collecte}{WasteTypes}-{MMYYYY}-{InvoiceNumber}.pdf

Where:
- Site: 3-4 digit restaurant site number
- Collecte: Base collector name (SUEZ, REFOOD, etc.)
- WasteTypes: Combination of DIB, BIO, CS
- MMYYYY: Invoice month and year
- InvoiceNumber: Original invoice identifier
```

### 12.2 Supported Collectors
SUEZ, VEOLIA, REFOOD, PAPREC, ELISE, DERICHEBOURG, ORTEC, ATESIS, BRANGEON, COLLECTEA, and others as defined in Prestataires.csv

### 12.3 API Usage Tracking Files

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

### 12.5 Error Codes
- **E001**: PDF text extraction failure
- **E002**: AI analysis timeout or failure
- **E003**: Restaurant/site matching failure
- **E004**: Collector name resolution failure
- **E005**: Invalid date format
- **E006**: Missing required fields

---

**Document Status**: ✅ Complete and Implemented
**Last Updated**: June 4, 2025
**Next Review**: December 2025
