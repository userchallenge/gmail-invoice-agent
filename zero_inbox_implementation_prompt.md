# Zero Inbox Agent - Complete Implementation Guide for Claude Code

## Project Overview
Implement a Zero Inbox Agent system that extends the existing gmail-invoice-agent repository using Atomic Agents framework. The system categorizes emails and performs specific actions based on predefined rules, building toward automated inbox management.

## Implementation Requirements

### Technical Stack
- **Framework**: Atomic Agents (https://github.com/BrainBlend-AI/atomic-agents.git)
- **Repository**: Build on existing https://github.com/userchallenge/gmail-invoice-agent.git
- **Database**: SQLite with SQLAlchemy
- **Interface**: Jupyter Notebook with step-by-step execution
- **Integration**: Extend existing Gmail fetching and cleaning functionality

### Target Categories (MVP)
Focus on implementing these 3 specific category/subcategory combinations:
1. **Other/Advertising**: Summarize categorization reasoning
2. **Other/Rest**: Summarize uncategorized emails with reasoning  
3. **Review/Job search**: Identify companies/roles of interest

## Phase-by-Phase Implementation

### Phase 1: Database Creation

Create comprehensive SQLite database schema using SQLAlchemy:

#### Email Storage Table
```sql
emails (
    id: INTEGER PRIMARY KEY
    email_id: TEXT UNIQUE (Gmail message ID)
    sender: TEXT
    subject: TEXT  
    body: TEXT (cleaned text content)
    pdf_content: TEXT (extracted PDF text)
    html_content: TEXT (original HTML)
    date_received: DATETIME
    date_processed: DATETIME
    has_attachments: BOOLEAN
    attachment_count: INTEGER
    created_at: DATETIME DEFAULT CURRENT_TIMESTAMP
)
```

#### Email Categories Table (based on Zero Inbox structure)
```sql
email_categories (
    id: INTEGER PRIMARY KEY
    email_id: INTEGER (FK to emails.id)
    category: TEXT (Other, Reading, Review, Task)
    subcategory: TEXT (Advertising, Rest, Job search, etc.)
    category_description: TEXT
    agent_action: TEXT (specific action to perform)
    supporting_information: TEXT (keywords, rules, context)
    classification_confidence: FLOAT
    classified_at: DATETIME
    classified_by: TEXT (agent name)
)
```

#### Agent Actions Table
```sql
agent_actions (
    id: INTEGER PRIMARY KEY
    email_id: INTEGER (FK to emails.id)
    category: TEXT
    subcategory: TEXT
    action_performed: TEXT (specific action executed)
    action_result: TEXT (output/summary from agent)
    processed_at: DATETIME
    agent_name: TEXT
    success: BOOLEAN
    error_message: TEXT
)
```

#### Human Review Table
```sql
human_reviews (
    id: INTEGER PRIMARY KEY
    email_id: INTEGER (FK to emails.id)
    original_category: TEXT
    original_subcategory: TEXT
    reviewed_category: TEXT
    reviewed_subcategory: TEXT  
    approved: BOOLEAN
    human_reasoning: TEXT
    reviewed_at: DATETIME
    reviewed_by: TEXT
)
```

**Implementation Requirements:**
- Use SQLAlchemy ORM with proper relationships
- Create database initialization function
- Add indexes for performance on email_id, category, subcategory
- Include data validation and constraints
- Populate email_categories with initial rules from CSV data

### Phase 2: Fetch Emails

Extend existing Gmail functionality to support Zero Inbox workflow:

#### Enhanced Email Fetching
- **Utilize existing**: Gmail API connection, authentication, and basic fetching
- **Extend with**: Time period filtering, duplicate prevention, enhanced cleaning
- **Add functionality**: 
  - Store raw emails in database
  - Extract and store PDF attachments as text
  - Clean HTML content while preserving structure  
  - Handle various email formats (plain text, HTML, multipart)

#### Email Cleaning Pipeline
```python
def clean_and_store_email(email_data):
    """
    Clean email content and store in database
    - Remove HTML tags but preserve line breaks
    - Extract text from PDF attachments  
    - Normalize text encoding
    - Store original and cleaned versions
    - Prevent duplicate storage
    """
```

**Configuration Integration:**
- Use existing config patterns from gmail-invoice-agent
- Add time period settings (default: 1 day)
- Configure PDF processing options
- Set duplicate prevention rules

### Phase 3: Email Categorization

Create intelligent categorization agent using Atomic Agents:

#### Categorization Agent Configuration
```python
classification_agent_config = {
    "agent_name": "EmailCategorizer",
    "system_prompt": """
    You are an email classification agent. Categorize emails based on these rules:
    
    CATEGORIES AND RULES:
    {category_rules}
    
    For each email, determine:
    1. Primary category (Other, Reading, Review, Task)
    2. Subcategory (specific type within category)  
    3. Confidence level (0.0-1.0)
    4. Brief reasoning
    
    Focus on these target categories for this MVP:
    - Other/Advertising: {advertising_rules}
    - Other/Rest: {rest_rules}  
    - Review/Job search: {job_search_rules}
    """,
    "model": "claude-3-sonnet-20240229"
}
```

#### Category Rules (from CSV data)
```python
CATEGORY_RULES = {
    "Other/Advertising": {
        "action": "Summarize the reasoning behind the categorization of this email.",
        "supporting_info": "Any email that contains advertising or is trying to drive sales without being in any of the other categories",
        "keywords": ["offer", "sale", "discount", "buy now", "limited time"]
    },
    "Other/Rest": {
        "action": "Summarize a list of sender subject and a one-two sentence summary about what the email consists of including reasoning why it didn't fit into any of the other categories",
        "supporting_info": "Anything that doesn't fit in the other categories"
    },
    "Review/Job search": {
        "action": "Identify roles and companies of interest and summarize a list for human review",
        "supporting_info": "List of companies (MUST, Polisen, Ework), roles(IT Project manager, Program Manager, Change Manager), domains (AI, Retail, ERP, Business Process, IT Steering, IT organization), key words (LinkedIn, Role, Roll, Ansökan, Application, Jobberbjudande)",
        "companies": ["MUST", "Polisen", "Ework"],
        "roles": ["IT Project manager", "Program Manager", "Change Manager"],
        "domains": ["AI", "Retail", "ERP", "Business Process", "IT Steering", "IT organization"],
        "keywords": ["LinkedIn", "Role", "Roll", "Ansökan", "Application", "Jobberbjudande"]
    }
}
```

### Phase 4: Create Actions on Email

Implement specific action agents for each target category:

#### Agent 1: Advertising Categorization Agent
```python
advertising_agent_config = {
    "agent_name": "AdvertisingAnalyzer", 
    "system_prompt": """
    Analyze advertising emails and provide categorization reasoning.
    
    Task: {CATEGORY_RULES['Other/Advertising']['action']}
    
    Supporting Information: {CATEGORY_RULES['Other/Advertising']['supporting_info']}
    
    Output Format:
    - Categorization: Other/Advertising
    - Reasoning: [Explain why this email is advertising]
    - Key Indicators: [List specific elements that identify it as advertising]
    - Sender Analysis: [Brief analysis of sender and intent]
    """,
    "model": "claude-3-sonnet-20240229"
}
```

#### Agent 2: Rest Category Agent  
```python
rest_agent_config = {
    "agent_name": "RestCategorizer",
    "system_prompt": """
    Summarize uncategorized emails that don't fit other categories.
    
    Task: {CATEGORY_RULES['Other/Rest']['action']}
    
    Output Format:
    - Sender: [Email sender]
    - Subject: [Email subject] 
    - Summary: [1-2 sentence summary of email content]
    - Reasoning: [Why this email doesn't fit other categories]
    - Suggested Action: [What should be done with this email]
    """,
    "model": "claude-3-sonnet-20240229"
}
```

#### Agent 3: Job Search Agent
```python
job_search_agent_config = {
    "agent_name": "JobSearchAnalyzer",
    "system_prompt": """
    Analyze job-related emails for opportunities of interest.
    
    Task: {CATEGORY_RULES['Review/Job search']['action']}
    
    Target Companies: {CATEGORY_RULES['Review/Job search']['companies']}
    Target Roles: {CATEGORY_RULES['Review/Job search']['roles']}
    Target Domains: {CATEGORY_RULES['Review/Job search']['domains']}
    Keywords: {CATEGORY_RULES['Review/Job search']['keywords']}
    
    Output Format:
    - Companies Mentioned: [List any target companies found]
    - Roles Identified: [List any target roles found]  
    - Domains: [List relevant domains mentioned]
    - Interest Level: [High/Medium/Low based on criteria]
    - Summary: [Brief summary for human review]
    - Recommended Action: [Apply, Research, Monitor, Ignore]
    """,
    "model": "claude-3-sonnet-20240229"  
}
```

#### Action Agent Execution
- Each agent fetches emails with matching category/subcategory
- Process emails sequentially with error handling
- Store action results in agent_actions table
- Log processing status and any errors
- Support retry mechanism for failed processing

### Phase 5: Summarize Results

Create comprehensive result summary agent:

#### Summary Agent Configuration
```python
summary_agent_config = {
    "agent_name": "ResultSummarizer",
    "system_prompt": """
    Generate a comprehensive summary of email processing results.
    
    Include:
    1. Processing Statistics
    2. Category Distribution  
    3. Action Results Summary
    4. Errors and Issues
    5. Recommended Next Steps
    """,
    "model": "claude-3-sonnet-20240229"
}
```

#### Summary Output Format
```
EMAIL PROCESSING SUMMARY
========================
Time Period: {start_date} to {end_date}
Total Emails Processed: {total_count}

CATEGORY BREAKDOWN:
- Other/Advertising: {ad_count} emails
- Other/Rest: {rest_count} emails  
- Review/Job search: {job_count} emails

DETAILED RESULTS:
{for each processed email}
- Sender: {sender}
- Date: {date} (YYMMDD:HHMM format)
- Subject: {subject}
- Category: {category}
- Subcategory: {subcategory}
- Action Result: {action_summary}
- Status: {success/error}

PROCESSING SUMMARY:
- Successfully Processed: {success_count}
- Errors Encountered: {error_count}  
- Human Review Required: {review_count}
```

### Phase 6: Manual Check of Categorization

Implement human-in-the-loop review workflow:

#### JSON Export Function
```python
def export_for_review(date_range=None):
    """
    Export processed emails to JSON format for human review
    
    JSON Structure:
    {
        "export_metadata": {
            "export_date": "2024-08-29T10:30:00",
            "date_range": {"start": "2024-08-28", "end": "2024-08-29"},
            "total_emails": 25,
            "pending_review": 25
        },
        "emails": [
            {
                "email_id": 123,
                "sender": "example@company.com", 
                "subject": "Job Opportunity - IT Project Manager",
                "date": "2024-08-29T08:15:00",
                "original_category": "Review",
                "original_subcategory": "Job search", 
                "action_result": "Companies: MUST mentioned. Role: IT Project Manager. Interest Level: High. Recommended: Apply",
                "confidence": 0.85,
                "review_fields": {
                    "approved": null,
                    "corrected_category": null,
                    "corrected_subcategory": null,
                    "human_reasoning": null
                }
            }
        ]
    }
    """
```

#### JSON Import Function  
```python
def import_human_feedback(json_file_path):
    """
    Import human review feedback and update database
    
    Process:
    1. Load JSON file with human corrections
    2. Validate review data structure
    3. Update human_reviews table
    4. Log corrections for future learning
    5. Generate feedback summary
    """
```

#### Human Review Interface
- Clear instructions for reviewers
- Standardized approval/rejection process
- Reasoning requirement for corrections
- Batch processing support
- Validation of human input

## Jupyter Notebook Structure

Create `zero_inbox_agent.ipynb` with these executable sections:

### Notebook Sections
```python
# Section 1: Setup and Configuration
# - Import libraries and initialize agents
# - Load configuration from existing config files
# - Initialize database connection

# Section 2: Database Creation and Setup  
# - Create all database tables
# - Populate initial category rules
# - Verify database structure

# Section 3: Fetch and Store Emails
# - Connect to Gmail API (reuse existing auth)
# - Fetch emails for specified time period  
# - Clean and store in database
# - Display fetch summary

# Section 4: Email Categorization
# - Load emails from database
# - Run categorization agent
# - Store category assignments
# - Show categorization results

# Section 5: Execute Action Agents
# - Run advertising analysis agent
# - Run rest categorization agent
# - Run job search analysis agent  
# - Display action results

# Section 6: Generate Summary
# - Create comprehensive processing summary
# - Display results in console
# - Generate statistics and insights

# Section 7: Export for Human Review
# - Export processed emails to JSON
# - Display export location and instructions
# - Prepare for manual review

# Section 8: Import Human Feedback (Optional)
# - Load human review results
# - Update database with corrections
# - Show feedback integration summary
```

## Configuration Management

Extend existing configuration approach:

### config/zero_inbox_config.yaml
```yaml
# Zero Inbox Agent Configuration
database:
  name: "zero_inbox.db"
  path: "data/"
  
processing:
  default_time_period_days: 1
  batch_size: 10
  max_retries: 3
  
agents:
  classification:
    model: "claude-3-sonnet-20240229"
    max_tokens: 1000
    temperature: 0.1
    
  action_agents:
    advertising:
      model: "claude-3-sonnet-20240229"
      max_tokens: 500
    rest: 
      model: "claude-3-sonnet-20240229"
      max_tokens: 500
    job_search:
      model: "claude-3-sonnet-20240229" 
      max_tokens: 800

# Category Rules from CSV data
category_rules:
  "Other/Advertising":
    action: "Summarize the reasoning behind the categorization of this email."
    supporting_info: "Any email that contains advertising or is trying to drive sales without being in any of the other categories"
    
  "Other/Rest":  
    action: "Summarize a list of sender subject and a one-two sentence summary about what the email consists of including reasoning why it didn't fit into any of the other categories"
    supporting_info: "Anything that doesn't fit in the other categories"
    
  "Review/Job search":
    action: "Identify roles and companies of interest and summarize a list for human review"
    supporting_info: "List of companies (MUST, Polisen, Ework), roles(IT Project manager, Program Manager, Change Manager), domains (AI, Retail, ERP, Business Process, IT Steering, IT organization), key words (LinkedIn, Role, Roll, Ansökan, Application, Jobberbjudande)"
    target_companies: ["MUST", "Polisen", "Ework"]
    target_roles: ["IT Project manager", "Program Manager", "Change Manager"] 
    target_domains: ["AI", "Retail", "ERP", "Business Process", "IT Steering", "IT organization"]
    keywords: ["LinkedIn", "Role", "Roll", "Ansökan", "Application", "Jobberbjudande"]

export:
  json_output_path: "output/human_review/"
  json_filename_format: "zero_inbox_review_{date}.json"
  
human_review:
  required_fields: ["approved", "human_reasoning"]
  batch_import: true
```

## Error Handling and Logging

Implement minimal but visible error handling:

### Error Categories
- **Database Errors**: Connection issues, schema problems, constraint violations
- **Gmail API Errors**: Rate limiting, authentication, network issues  
- **Agent Errors**: API failures, parsing errors, timeout issues
- **Processing Errors**: Invalid email format, missing data, classification failures

### Error Display
- Clear error messages in notebook output
- Error logging to console and file
- Continue processing on non-critical errors
- Graceful degradation when possible

### Logging Configuration
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/zero_inbox.log'),
        logging.StreamHandler()  # Console output
    ]
)
```

## Testing and Validation

Include basic testing capabilities:

### Test Data Validation
- Verify database schema creation
- Test email fetching and storage  
- Validate categorization logic
- Check action agent outputs
- Confirm JSON export/import

### Sample Email Testing
- Include test emails for each category
- Verify agent responses match expected outputs
- Test edge cases and error conditions

## Success Criteria

### MVP Success Metrics
- ✅ All database tables created successfully
- ✅ Emails fetched and stored without duplicates
- ✅ All 3 target categories processed correctly
- ✅ Action results stored in database
- ✅ Human review JSON export/import working
- ✅ Notebook executes step-by-step without errors
- ✅ Configuration system integrated with existing patterns

### Expected Outputs
- Categorized emails in database
- Action results for advertising, rest, and job search emails
- Processing summary with statistics
- JSON files ready for human review
- Clear error messages for any issues

## Implementation Notes

### Development Approach
- Start with Phase 1 (Database) and verify before proceeding
- Test each phase independently in notebook
- Reuse existing Gmail functionality whenever possible
- Follow Atomic Agents patterns established in current repo
- Keep configuration flexible for future expansion

### Future Extensibility  
- Database schema supports all categories from CSV
- Agent framework can easily add new category agents
- Configuration allows for new rules and categories
- Human feedback loop enables continuous improvement

This implementation provides a complete MVP Zero Inbox Agent system that integrates with your existing codebase while establishing the foundation for automated email management.