#!/bin/bash
# Setup script for PDF Invoice Renamer

echo "📄 PDF Invoice Renamer Setup"
echo "=============================="
echo

# Check if .env file exists
if [ -f ".env" ]; then
    echo "✅ .env file already exists"
    
    # Check if API key is set
    if grep -q "GEMINI_API_KEY=your_api_key_here" .env; then
        echo "⚠️  Please update your API key in the .env file"
        echo "   Edit .env and replace 'your_api_key_here' with your actual Gemini API key"
        echo
        echo "   Get your API key from: https://aistudio.google.com/app/apikey"
    else
        echo "✅ API key appears to be configured"
    fi
else
    echo "❌ .env file not found - creating one now..."
    cp .env.example .env 2>/dev/null || echo "Please create .env file manually"
fi

echo
echo "📋 Installation Steps:"
echo "1. Install dependencies: pip install -r requirements.txt"
echo "2. Get API key from: https://aistudio.google.com/app/apikey"
echo "3. Edit .env file and set your GEMINI_API_KEY"
echo "4. Test with: python pdf_renamer.py --status"
echo
echo "🚀 Usage Examples:"
echo "# Check rate limit status and usage history"
echo "python pdf_renamer.py --status"
echo
echo "# Get weekly usage summary"
echo "python pdf_renamer.py --weekly-summary"
echo
echo "# Dry run (test without renaming)"
echo "python pdf_renamer.py '/path/to/pdfs' --dry-run"
echo
echo "# Process files for real"
echo "python pdf_renamer.py '/path/to/pdfs'"
echo
echo "📊 Free Tier Limits:"
echo "• 15 requests per minute"
echo "• 1,500 requests per day"
echo "• Rate limiting is automatically handled"
echo "• Usage is tracked persistently across program runs"
