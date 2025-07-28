# Gmail Invoice Agent - Setup Instructions

## Prerequisites
- Python 3.8 or higher
- Gmail account
- Claude API access
- Google Cloud Project (for Gmail API)

## Step-by-Step Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set up Gmail API Access

#### Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Gmail API:
   - Go to "APIs & Services" > "Library" 
   - Search for "Gmail API"
   - Click "Enable"

#### Create Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Desktop application"
4. Name it "Gmail Invoice Agent"
5. Download the JSON file
6. Rename it to `gmail_credentials.json`
7. Place it in the `config/` directory

### 3. Configure Claude API

1. Get your Claude API key from [Anthropic Console](https://console.anthropic.com/)
2. Edit `config/config.yaml`
3. Replace `your-claude-api-key-here` with your actual API key

### 4. Test the Setup

#### Run with verbose logging first:
```bash
python demo.py --verbose
```

#### For a quick test with recent emails:
```bash
python demo.py --days-back 7 --max-emails 20
```

### 5. First Run Authentication

On first run, the script will:
1. Open your browser for Gmail authentication
2. Ask you to grant permissions to read your Gmail
3. Save authentication tokens for future use

**Important**: Grant "Read" permissions only - the app never modifies your emails.

## Directory Structure After Setup
```
gmail-invoice-agent/
├── config/
│   ├── config.yaml                 # ✅ Your API keys configured
│   ├── gmail_credentials.json      # ✅ Downloaded from Google Cloud
│   └── gmail_token.json           # ✅ Auto-generated after first auth
├── output/                         # ✅ Auto-created
│   ├── invoices.csv               # ✅ Generated invoice data
│   └── processing.log             # ✅ Application logs
├── demo.py                        # ✅ Main script
├── gmail_server.py               # ✅ Gmail integration
├── email_classifier.py          # ✅ AI classification
├── csv_exporter.py              # ✅ CSV export
└── requirements.txt              # ✅ Dependencies
```

## Configuration Options

### Processing Settings
```yaml
processing:
  default_days_back: 30    # How many days back to search
  max_emails: 100          # Maximum emails to process
  batch_size: 10          # Processing batch size
```

### Invoice Keywords
The system looks for these Swedish keywords (prioritized):
- faktura, räkning, förfallodag, att betala, totalt belopp
- OCR numbers, bankgiro, plusgiro

And English keywords:
- invoice, bill, payment due, total amount

### Common Swedish Vendors
Pre-configured to recognize:
- Vattenfall, Telia, ICA, Skatteverket
- Banks: Nordea, SEB, Swedbank, Handelsbanken

## Troubleshooting

### Gmail Authentication Issues
```bash
# Remove token file and re-authenticate
rm config/gmail_token.json
python demo.py
```

### API Rate Limits
- Gmail API: 1 billion quota units per day
- Claude API: Check your usage limits
- The script includes rate limiting (1 second pause every 10 emails)

### No Invoices Found
1. Check date range: `--days-back 60`
2. Verify Gmail search finds invoices manually
3. Check invoice keywords in config
4. Enable verbose logging: `--verbose`

### Common Errors

**"Gmail credentials file not found"**
- Download `credentials.json` from Google Cloud Console
- Rename to `gmail_credentials.json`
- Place in `config/` directory

**"Claude API key invalid"**
- Check your API key in `config/config.yaml`
- Verify key is active in Anthropic Console

**"No module named 'gmail_server'"**
- Ensure all Python files are in the same directory
- Run from the project root directory

## Usage Examples

### Basic usage:
```bash
python demo.py
```

### Process last week only:
```bash
python demo.py --days-back 7
```

### Custom config file:
```bash
python demo.py --config my_config.yaml
```

### Verbose logging for debugging:
```bash
python demo.py --verbose --days-back 3
```

## Expected Output

The script will:
1. ✅ Authenticate with Gmail
2. 🔍 Search for potential invoice emails
3. 🤖 Process each email with Claude AI
4. 💾 Export invoice data to CSV
5. 📊 Show summary statistics

Sample CSV output columns:
- `vendor`, `amount`, `currency`, `due_date`
- `invoice_number`, `ocr`, `description`
- `email_subject`, `email_sender`, `email_date`
- `confidence`, `processed_date`

## Security Notes

- Credentials are stored locally only
- Gmail token allows read-only access
- No email content is stored permanently
- All processing happens locally