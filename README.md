# Resume Automator Processor

This project automates the process of shortlisting candidates for job postings using Lever (ATS), Google Sheets, and Gemini AI. It is designed for HR teams to streamline resume evaluation, avoid duplicate processing, and maintain a clear audit trail.

---

## Features

- **Automated Resume Download:** Fetches new applicant resumes from Lever for a given job posting.
- **In-Memory Processing:** Resumes are processed in memory (no disk writes), making it cloud-friendly.
- **AI-Powered Evaluation:** Uses Gemini AI to strictly and objectively evaluate resumes against job requirements.
- **Google Sheets Integration:** 
  - HR enters the job posting ID in the `Input` sheet.
  - Results are logged in the `Results` sheet.
  - Processed candidates are tracked in the `Processed` sheet to prevent duplicate processing.
- **Duplicate Prevention:** Each (Posting_ID, Opportunity_ID) pair is checked before processing to avoid re-evaluating the same candidate.
- **Cron Scheduling:** Can be scheduled to run automatically (e.g., every two days) using cron.
- **Logging:** All actions and errors are logged for transparency and debugging.

---

## How It Works

1. **HR Workflow:**
   - HR enters the job posting ID in the `Input` sheet of the connected Google Spreadsheet.

2. **Automated Script:**
   - The script reads the latest posting ID.
   - Downloads resumes for new applicants from Lever (in memory).
   - Checks the `Processed` sheet to skip already-processed candidates.
   - Evaluates each new resume using Gemini AI.
   - Logs results in the `Results` sheet and marks candidates as processed in the `Processed` sheet.

3. **Scheduling:**
   - The script can be run manually or scheduled via cron to run automatically at set intervals.

---

## Setup Instructions

### 1. Clone the Repository
```sh
git clone https://github.com/chinmaysairam/resume_automator-processor.git
cd resume_automator-processor
```

### 2. Install Dependencies
```sh
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root with the following variables:
```
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
SPREADSHEET_ID=your_google_sheet_id
LEVER_API_KEY=your_lever_api_key
GEMINI_API_KEY=your_gemini_api_key
```

### 4. Google Sheets Setup
- Create a Google Sheet with three tabs:
  - `Input` (HR enters Posting_ID in column A)
  - `Results` (script logs evaluation results)
  - `Processed` (script logs processed candidates)

### 5. Run the Script Manually
```sh
python3 main4.py
```

### 6. (Optional) Schedule with Cron
- Create a shell script `run_main4.sh`:
  ```sh
  #!/bin/bash
  cd /path/to/resume_automator-processor
  /usr/bin/env python3 main4.py
  ```
- Make it executable:
  ```sh
  chmod +x run_main4.sh
  ```
- Add to your crontab (`crontab -e`) to run every two days at midnight:
  ```
  0 0 */2 * * /path/to/resume_automator-processor/run_main4.sh >> /path/to/resume_automator-processor/cron.log 2>&1
  ```

---

## Project Structure

```
resume_automator-processor/
├── main4.py                # Main automation script
├── lever_api.py            # Lever API integration
├── sheets_api.py           # Google Sheets integration
├── local_resume_processor.py # Resume parsing utilities
├── requirements.txt        # Python dependencies
├── .env.example            # Example environment variables (no secrets)
├── run_main4.sh            # Shell script for cron
└── logs/                   # Log files
```

---

## Customization

- **Evaluation Criteria:**  
  The evaluation prompt and scoring can be customized in `main4.py` (`evaluate_resume` function).
- **Google Sheet Structure:**  
  You can adjust the columns and sheet names in `sheets_api.py` if needed.

---

## Troubleshooting

- **API Errors:**  
  Ensure your API keys and credentials are correct and have the necessary permissions.
- **Google Sheets Issues:**  
  Make sure your service account has access to the target Google Sheet.
- **Logging:**  
  Check the `logs/` directory or `cron.log` for detailed error messages.

---

## Contributing

Pull requests and suggestions are welcome! Please open an issue or submit a PR.

---

## License

MIT License

---

**Questions?**  
Open an issue or contact the maintainer.
