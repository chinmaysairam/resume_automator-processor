Resume Processor

GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
SPREADSHEET_ID=your_google_sheet_id
LEVER_API_KEY=your_lever_api_key
GEMINI_API_KEY=your_gemini_api_key


## 4. Google Sheets Setup
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
  cd /path/to/recruitment_agent
  /usr/bin/env python3 main4.py
  ```
- Make it executable:
  ```sh
  chmod +x run_main4.sh
  ```
- Add to your crontab (`crontab -e`) to run every two days at midnight:
  ```
  0 0 */2 * * /path/to/recruitment_agent/run_main4.sh >> /path/to/recruitment_agent/cron.log 2>&1
  ```

---

## Project Structure

recruitment_agent/
├── main4.py # Main automation script
├── lever_api.py # Lever API integration
├── sheets_api.py # Google Sheets integration
├── local_resume_processor.py # Resume parsing utilities
├── requirements.txt # Python dependencies
├── .env # Environment variables (not committed)
├── run_main4.sh # Shell script for cron
└── logs/ # Log files




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
