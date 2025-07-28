# Gmail Invoice Agent - PDF Attachment Enhancement

## Project Context
I have a working Gmail Invoice Agent that extracts invoice data from emails using Claude AI. The system already has dynamic query building and searches both email subject/body content. Now I need to add PDF attachment text extraction to capture invoices sent as PDF files.

## Current Working System
- Gmail API integration with OAuth authentication ✅
- Claude AI classification and data extraction ✅  
- CSV export functionality ✅
- Swedish/English keyword support ✅
- Dynamic Gmail queries from config ✅
- Subject AND body keyword search ✅

## Required Enhancement: PDF Attachment Text Extraction

### Current Issue
Many invoices are sent as PDF attachments to emails. The system currently ignores these PDFs and only analyzes the email text content, missing valuable invoice data.

### Required Change
Extract text content from PDF attachments and include it in the Claude AI analysis alongside the email content.

## Implementation Requirements

### 1. PDF Detection and Download
- Detect emails with PDF attachments during email processing
- Download PDF attachment data via Gmail API `attachments().get()` method
- Handle Gmail API rate limiting for attachment downloads
- Add logging for PDF processing attempts

### 2. PDF Text Extraction
- Extract readable text from PDF files
- Handle various PDF formats (text-based, scanned with OCR if possible)
- Gracefully handle extraction failures (corrupted PDFs, password-protected, etc.)
- Limit processing time to avoid hanging on complex PDFs

### 3. Content Integration
- Combine email body text + PDF extracted text
- Send combined content to Claude for analysis
- Maintain original email content structure
- Add clear markers showing PDF content vs email content

### 4. Error Handling
- Continue processing if PDF extraction fails
- Log PDF processing errors without stopping email processing
- Track PDF processing success/failure status
- Handle oversized PDF files gracefully

### 5. Configuration Options
Add PDF processing settings to `config/config.yaml`:
```yaml
processing:
  pdf_processing:
    enabled: true
    max_pdf_size_mb: 10
    timeout_seconds: 30
    skip_password_protected: true
```

## Technical Implementation

### Libraries to Add
Add to `requirements.txt`:
```
PyPDF2>=3.0.0
# OR alternatively:
# pdfplumber>=0.7.0
```

### Files to Modify

#### gmail_server.py
- Add `_download_pdf_attachment(attachment_id, attachment_size)` method
- Add `_extract_pdf_text(pdf_bytes)` method  
- Modify `_get_email_details()` to process PDF attachments
- Add PDF processing to email data structure

#### email_classifier.py
- Update `_extract_with_claude()` to handle combined email+PDF content
- Add PDF processing status to output data structure
- Update prompt to Claude to indicate PDF content vs email content

#### config/config.yaml
- Add `pdf_processing` configuration section

### Data Flow
```
Email with PDF → Download PDF → Extract Text → Combine with Email → Send to Claude → Extract Invoice Data
```

### Error Scenarios to Handle
- PDF download fails (network, API limits)
- PDF is password protected
- PDF is corrupted or invalid format
- PDF is too large (>config limit)
- PDF text extraction times out
- PDF contains no extractable text (pure images)

## Expected Output Enhancement

### CSV Output
Add new columns to track PDF processing:
- `pdf_processed`: boolean (true/false)
- `pdf_filename`: name of processed PDF file
- `pdf_text_length`: character count of extracted text
- `pdf_processing_error`: error message if extraction failed

### Logging Enhancement
Add detailed PDF processing logs:
```
INFO: Found PDF attachment: invoice_march.pdf (234KB)
INFO: Extracting text from PDF: invoice_march.pdf
INFO: ✓ PDF text extracted: 1,247 characters
INFO: Sending combined email+PDF content to Claude
```

## Success Criteria
- [ ] PDF attachments automatically detected in emails
- [ ] PDF text successfully extracted and combined with email content
- [ ] Claude receives enhanced content for better invoice data extraction
- [ ] PDF processing errors handled gracefully without stopping email processing
- [ ] Configuration options allow tuning PDF processing behavior
- [ ] CSV output includes PDF processing status and metadata
- [ ] Backwards compatible with existing non-PDF email processing

## Testing Requirements
- Test with various PDF invoice formats (text-based, scanned)
- Test error handling with corrupted/protected PDFs
- Test with emails containing multiple PDF attachments
- Verify processing time limits prevent hanging
- Test with oversized PDF files
- Ensure existing email-only processing still works

## Performance Considerations
- PDF processing will increase processing time per email
- Gmail API has attachment download quotas
- Large PDFs may consume significant memory
- Consider processing PDFs asynchronously for large batches

## Implementation Priority
1. Basic PDF detection and download
2. Text extraction with error handling
3. Integration with existing Claude analysis
4. Configuration options and logging
5. CSV output enhancements

## Example Usage
After implementation, the system should:
1. Find email with PDF attachment named "Vattenfall_Invoice_March.pdf"
2. Download and extract text: "Faktura från Vattenfall... Totalt belopp: 1,250 kr..."
3. Combine with email text and send to Claude
4. Extract structured invoice data including PDF-sourced information
5. Output to CSV with PDF processing status

This enhancement should significantly increase invoice detection coverage by capturing PDF-based invoices that are currently missed.