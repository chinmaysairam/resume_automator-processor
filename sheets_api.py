from typing import List
from dataclasses import dataclass
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from dotenv import load_dotenv
load_dotenv()
@dataclass
class JobConfig:
    job_posting: str
    job_description: str
    recruiter_prompt: str

class SheetsAPI:
    def __init__(self, credentials: Credentials):
        self.service = build('sheets', 'v4', credentials=credentials)
        self.sheet = self.service.spreadsheets()

    def get_job_configs(self, spreadsheet_id: str, range_name: str = "myproject!A2:C") -> List[JobConfig]:
        """Fetch job posting, job description, and recruiter prompt from the Google Sheet."""
        result = self.sheet.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])
        # print(values)
        if not values:
            return []
        job_configs = []
        for row in values:
            if len(row) < 3:
                continue
            job_configs.append(JobConfig(
                job_posting=row[0],
                job_description=row[1],
                recruiter_prompt=row[2]
            ))
        print(job_configs)
        return job_configs

    def log_result(self, spreadsheet_id: str, job_description: str, applicant_name: str, 
                  decision: str, explanation: str, range_name: str = "Results!A2:F"):
        """Log the shortlisting result to a separate sheet with timestamp."""
        # Format timestamp in a readable format
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        values = [[
            job_description,
            applicant_name,
            decision,
            explanation,
            timestamp
        ]]
        
        body = {
            'values': values
        }
        
        try:
            self.sheet.values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
        except Exception as e:
            if "Unable to parse range" in str(e):
                # If the range is invalid, try to create the sheet first
                try:
                    # Create the Results sheet if it doesn't exist
                    self.sheet.batchUpdate(
                        spreadsheetId=spreadsheet_id,
                        body={
                            'requests': [{
                                'addSheet': {
                                    'properties': {
                                        'title': 'Results'
                                    }
                                }
                            }]
                        }
                    ).execute()
                    
                    # Add headers
                    self.sheet.values().update(
                        spreadsheetId=spreadsheet_id,
                        range="Results!A1:F1",
                        valueInputOption='RAW',
                        body={
                            'values': [['Job Description', 'Applicant Name', 'Decision', 'Explanation', 'Timestamp']]
                        }
                    ).execute()
                    
                    # Retry the append operation
                    self.sheet.values().append(
                        spreadsheetId=spreadsheet_id,
                        range=range_name,
                        valueInputOption='RAW',
                        body=body
                    ).execute()
                except Exception as create_error:
                    raise Exception(f"Failed to create Results sheet: {str(create_error)}")
            else:
                raise e

def get_google_credentials1():
    """Initialize Google credentials from OAuth client file."""
    credentials = None
    token_path = 'token.pickle'
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    
    # Load credentials from token.pickle if it exists
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            credentials = pickle.load(token)
    
    # If credentials don't exist or are invalid, get new ones
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path,
                ['https://www.googleapis.com/auth/spreadsheets']
            )
            credentials = flow.run_local_server(port=0)
        
        # Save credentials for future use
        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)
    
    return credentials

if __name__ == "__main__":
    # Test SheetsAPI functionality
    credentials = get_google_credentials1()
    sheets_api = SheetsAPI(credentials)
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    print("Fetching job configs from Google Sheets...")
    job_configs = sheets_api.get_job_configs(spreadsheet_id)
    # for idx, job in enumerate(job_configs, 1):
    #     print(f"Job {idx} description: {job.job_description[:80]}")
    #     print(f"Recruiter prompt: {job.recruiter_prompt[:80]}")
    #     print("-")
    # # Log a test result
    # print("Logging a test result to Results sheet...")
    # sheets_api.log_result(
    #     spreadsheet_id,
    #     job_description="Test Job Description",
    #     applicant_name="Test Applicant",
    #     decision="SHORTLIST",
    #     explanation="This is a test log entry."
    # )
    # print("Test result logged.")


        