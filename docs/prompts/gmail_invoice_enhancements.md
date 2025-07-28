# Gmail Invoice Agent - Enhancement Requirements

## Project Context
I have a working Gmail Invoice Agent that extracts invoice data from emails using Claude AI. The system currently works but needs two specific improvements to increase accuracy and coverage.

## Current Working System
- Gmail API integration with OAuth authentication ✅
- Claude AI classification and data extraction ✅  
- CSV export functionality ✅
- Swedish/English keyword support ✅
- Basic invoice detection and processing ✅

## Required Enhancements

### 1. Dynamic Gmail Query from Config
**Current Issue**: Gmail search query is hardcoded in `gmail_server.py`
**Required Change**: Build search query dynamically from `config/config.yaml` keywords

**Current hardcoded query in gmail_server.py line ~45:**
```python
query = f'after:{start_date.strftime("%Y/%m/%d")} (subject:faktura OR subject:räkning OR subject:invoice OR subject:bill OR has:attachment filetype:pdf)'
```

**Required**: Generate this query from config file sections:
- `invoice_keywords.invoice_indicators.swedish`
- `invoice_keywords.invoice_indicators.english` 
- `common_vendors.swedish`
- `common_vendors.english`

**Implementation**: Create method `_build_search_query()` that constructs Gmail search string from config keywords.

### 2. Enhanced Keyword Matching (Subject AND Body)
**Current Issue**: Gmail query only searches email subjects
**Required Change**: Search both subject AND body content for all keywords

**Current query pattern**: `subject:faktura OR subject:räkning`
**Required pattern**: `(subject:faktura OR faktura) OR (subject:räkning OR räkning)`

This allows finding invoices where keywords appear in email body text, not just subject lines.

## Files to Modify

### gmail_server.py
- Add `_build_search_query(config)` method
- Modify `fetch_emails()` to use dynamic query from config
- Update constructor to accept config parameter

### email_classifier.py  
- Update to handle improved keyword matching results
- Ensure compatibility with enhanced email content

### config/config.yaml
- Ensure all Swedish/English keywords are comprehensive
- Verify vendor lists are complete

## Expected Outcomes

1. **Better Coverage**: Find more invoices by searching email bodies
2. **Dynamic Queries**: Easy to add new vendors/keywords via config
3. **Improved Accuracy**: More complete data for Claude analysis
4. **Maintainable**: Easy to adjust search terms without code changes

## Implementation Priority
1. Dynamic query building (highest impact, lowest complexity)
2. Subject+Body keyword search (high impact, low complexity)

## Testing Requirements
- Verify dynamic query produces same or better results
- Test with emails containing invoice keywords in body text
- Ensure backwards compatibility with existing CSV format
- Verify all config keywords are properly included in search

## Configuration Example
The enhanced system should work with existing config structure and automatically build queries like:
```
after:2024-01-01 ((subject:faktura OR faktura) OR (subject:räkning OR räkning) OR (subject:invoice OR invoice) OR (subject:bill OR bill) OR (from:vattenfall OR from:telia) OR has:attachment filetype:pdf)
```

## Success Criteria
- [ ] Gmail queries built dynamically from config keywords
- [ ] Keywords searched in both subject and body content
- [ ] Backwards compatible with existing functionality  
- [ ] Easy to add new keywords via config file
- [ ] Improved invoice detection coverage