# Email Processing CLI - Complete Reference

## Basic Command Structure
```bash
python -m email_processing.cli [OPTIONS]
```

## ✅ Date Options (can be combined with any processing command)

### Date Filtering Options
```bash
--days N                    # Number of days back to fetch emails (default: 1)
--from-date YYYY-MM-DD     # Fetch emails from specific date to now
--to-date YYYY-MM-DD       # End date for date range (requires --from-date)
--date YYYY-MM-DD          # Fetch emails from single specific date
```

### Date Validation Rules
- `--date` cannot be used with `--from-date` or `--to-date`
- `--to-date` requires `--from-date`
- All dates must be in YYYY-MM-DD format
- `--to-date` must be after `--from-date`

## ✅ Processing Commands

### 1. Full Pipeline (Default)
Runs complete workflow: Fetch → Categorize → Summarize → Show Stats

```bash
# Default: last 1 day
python -m email_processing.cli

# Last N days
python -m email_processing.cli --days 7

# From specific date to now
python -m email_processing.cli --from-date 2025-01-24

# Specific date range
python -m email_processing.cli --from-date 2025-01-24 --to-date 2025-01-28

# Single specific date
python -m email_processing.cli --date 2025-01-25
```

### 2. Individual Processing Steps

```bash
# Only fetch and store emails
python -m email_processing.cli --fetch-only

# Only categorize existing emails
python -m email_processing.cli --categorize-only

# Only summarize existing information emails
python -m email_processing.cli --summarize-only

# Show processing statistics
python -m email_processing.cli --stats
```

### 3. Combined Date + Processing Examples

```bash
# Fetch last 3 days only
python -m email_processing.cli --fetch-only --days 3

# Fetch specific date range only
python -m email_processing.cli --fetch-only --from-date 2025-01-20 --to-date 2025-01-25

# Fetch single date only
python -m email_processing.cli --fetch-only --date 2025-01-24
```

## ✅ Database Management Commands

### 1. Delete All Tables (Empty Database)
Empties all tables (emails, categorizations, summaries), keeps database file structure, re-populates categories

```bash
# Interactive confirmation
python -m email_processing.cli --delete-database

# Skip confirmation
python -m email_processing.cli --delete-database --force
```

### 2. Delete Processing Results
Clears categorizations and summaries tables, resets email categories to NULL, keeps emails intact

```bash
# Interactive confirmation
python -m email_processing.cli --delete-result-tables

# Skip confirmation
python -m email_processing.cli --delete-result-tables --force
```

### 3. Delete Specific Result Table
Clears specific table only, resets related email fields if needed

```bash
# Clear only categorizations table
python -m email_processing.cli --delete-result-table --table categorizations

# Clear only summaries table
python -m email_processing.cli --delete-result-table --table summaries

# Skip confirmation
python -m email_processing.cli --delete-result-table --table categorizations --force
python -m email_processing.cli --delete-result-table --table summaries --force
```

## ✅ Email Fetching Behavior

### Scope & Filtering
- **Inbox Only:** Fetches only inbox emails (excludes sent, spam, drafts, archives)
- **Gmail Query:** Uses `in:inbox after:YYYY/MM/DD before:YYYY/MM/DD` format
- **Exact Dates:** Date boundaries match Gmail GUI search behavior exactly
- **Duplicates:** Prevents storing duplicate emails based on email_id

### Content Processing
- **HTML Conversion:** Converts HTML email body to markdown and clean text
- **PDF Extraction:** Extracts and stores text from PDF attachments
- **Data Storage:** Stores emails with sender, subject, date, body variations, and PDF text

### Global Options
```bash
--force    # Skip confirmation prompts for delete operations
```

## ✅ Common Usage Patterns

```bash
# Daily processing (most common)
python -m email_processing.cli

# Weekly catch-up
python -m email_processing.cli --days 7

# Process specific period
python -m email_processing.cli --from-date 2025-01-20 --to-date 2025-01-25

# Fresh start - clear everything and reprocess
python -m email_processing.cli --delete-database --force
python -m email_processing.cli --days 7

# Redo categorization only
python -m email_processing.cli --delete-result-table --table categorizations --force
python -m email_processing.cli --categorize-only

# Quick stats check
python -m email_processing.cli --stats
```

