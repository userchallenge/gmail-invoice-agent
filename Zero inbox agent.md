# Zero inbox agent

## **Instructions:**

This must be built on and follow atomic agents ([**repo**](https://github.com/userchallenge/gmail-invoice-agent.git)) approach and architecture.

Utilize existing gmail/email fetching methods and cleaning functionality that already has been built, but create a new notebook so I can run the functionality step-by-step.

A database built on Sqlalchemy and sqlite must be built

Use a method for exporting and importing CSV-files for manual check of categorization

Start with Category/Subcategory: Other/Advertising, Other/Rest and Review/Job search

# Zero inbox agent purpose, goal and instructions

The purpose of the zero-inbox-agent is to minimize clutter by categorizing all emails and suggest action according to rules per category.

The goal is short term to always have an empty inbox where all emails have been acted on. Over time, the ambition is to automate more and more as the agent learns what to do with different types of email.

I have described how different types of email shall be categorized and what information they need in [](https://www.notion.so/25d850b247ab80d9a4aeeeead5e2fb3a?pvs=21).

Below is also a process description for the intended workflow.

## **Process**

### **Fetch emails**

1. Fetch all emails from gmail for one time period (e.g. one day)
2. Clean emails so only the textual information and the extraction of pdf-files or similar included information is storeable in a database.
3. Save emails from that day in the database. Make sure no duplicates of the email are saved.

### **Email categorization**

1. One Categorizing-Agent Set category and subcategory on all emails and stores in database

### **Create actions on Email**

1. Another agent fetches relevant emails for it’s responsibility (Category/Subcategory) from database
2. The agent follows the instructions in “Agent action” column.
    1. Perform action according to instructions and store in column action_result
    2. Use supporting information for that agent (MCP, added context or similar) where available
    3. Verify results by using the existing humanly reviewed data from previous categorizations.
    4. Output the results to the database

### **Summarize results**

1. A summary agent fetches the actions from the database and prints a summary of the whole categorization in the console

### **Manual check of categorization**

After Agents are finished and the result is summarized, every row is checked manually by a human that approves/rejects categorization.

1. Get JSON-files with results
2. Human go through JSON-files and fill in fields category, subcategory, approved, human_reasoning
    1. if approve (optional):
        1. Describe why this was correct
        2. Describe if there are other similar variations that can be categorized the same way
    2. If reject:
        1. Set new categorization
        2. Document reasoning why that category was chosen
3. Updated JSON-file is uploaded and saved to the database.

## **Acceptance criteria for phase:**

### **Fetch emails**

- Emails can be extracted from a defined time period (from-to, from→, date)
- PDF-attachments can be converted to text format
- HTML-notation is removed so only relevant body text remains
- Email date, subject, body, pdf-content is stored in database

### **Email categorization**

- Category and Subcategory set on email in database

### **Create actions on Email**

- Agent for category can fetch relevant emails
- Prompt exists with clear actions on what to do
- Supporting information is provided to the agent in the prompt through configuration file
- Previously categorized data is used by the agent
- Actions are stored in database

### **Summarize results**

- Sender, date (YYMMDD:HHMM), subject, category, subcategory,

### **Manual check of categorization**

- JSON-file can be exported and imported
- Field Approved is filled with true/false
- if false
    - category and subcategory is updated
    - human_reasoning is filled out with explanation

##