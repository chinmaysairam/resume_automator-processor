import os
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from sheets_api import SheetsAPI
from local_resume_processor import LocalResumeProcessor
import google.generativeai as genai
import json
import re
from datetime import datetime, timedelta
import logging
import time
import csv
import pandas as pd
from lever_api import LeverAPI


# Load environment variables
load_dotenv()

class QuotaManager:
    def __init__(self, max_requests=1000, reset_hours=24):
        self.max_requests = max_requests
        self.reset_hours = reset_hours
        self.requests_today = 0
        self.last_reset = datetime.now()
    
    def can_make_request(self):
        if datetime.now() - self.last_reset > timedelta(hours=self.reset_hours):
            self.requests_today = 0
            self.last_reset = datetime.now()
        return self.requests_today < self.max_requests
    
    def increment_request(self):
        self.requests_today += 1

# Initialize quota manager
quota_manager = QuotaManager()

def setup_logging():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f'logs/evaluation_{timestamp}.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return log_file

def get_google_credentials():
    credentials = None
    token_path = 'token.pickle'
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path,
                ['https://www.googleapis.com/auth/spreadsheets']
            )
            credentials = flow.run_local_server(port=0)
        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)
    return credentials

def normalize(text):
    if not text:
        return ""
    text = text.lower()
    prefixes_to_remove = [
        'job title-', 'job tittle-', 'job title:', 'job tittle:',
        'job title -', 'job tittle -', 'job title:', 'job tittle:'
    ]
    for prefix in prefixes_to_remove:
        if text.startswith(prefix):
            text = text[len(prefix):]
    text = re.sub(r'[–—\-]', '-', text)
    text = ' '.join(text.split())
    text = ''.join(c for c in text if c.isalnum() or c.isspace() or c == '-')
    text = re.sub(r'\s*-\s*', '-', text)
    return text.strip()

def find_job_config(job_configs, job_query):
    job_query_norm = normalize(job_query)
    logging.info(f"Normalized job query: {job_query_norm}")
    for job_config in job_configs:
        if job_query_norm == normalize(getattr(job_config, "job_posting", "")):
            return job_config
    for job_config in job_configs:
        if job_query_norm in normalize(getattr(job_config, "job_posting", "")):
            return job_config
    for job_config in job_configs:
        job_desc_norm = normalize(job_config.job_description)
        if job_query_norm == job_desc_norm:
            return job_config
        if job_query_norm.replace("-", "") == job_desc_norm.replace("-", ""):
            return job_config
        if job_query_norm in job_desc_norm:
            return job_config
        if job_query_norm.replace(" ", "").replace("-", "") in job_desc_norm.replace(" ", "").replace("-", ""):
            return job_config
    return None

def get_latest_posting_id(sheets_api, spreadsheet_id):
    result = sheets_api.service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Input!A2:A"
    ).execute()
    values = result.get('values', [])
    if values:
        return values[-1][0]
    else:
        return None

def is_already_processed(sheets_api, spreadsheet_id, posting_id, opportunity_id):
    """Check if a candidate has already been processed."""
    try:
        result = sheets_api.service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Processed!A:B"
        ).execute()
        values = result.get('values', [])
        
        # Check if the Processed sheet exists and has data
        if not values:
            return False
            
        # Check if the tuple (posting_id, opportunity_id) exists
        for row in values:
            if len(row) >= 2 and row[0] == posting_id and row[1] == opportunity_id:
                return True
        return False
    except Exception as e:
        logging.error(f"Error checking processed status: {str(e)}")
        return False



def log_processed_candidate(sheets_api, spreadsheet_id, posting_id, opportunity_id):
    """Log a processed candidate to the Processed sheet."""
    try:
        # Format timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Prepare the values
        values = [[posting_id, opportunity_id, timestamp]]
        
        # Try to append to the Processed sheet
        try:
            sheets_api.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range="Processed!A:C",
                valueInputOption='RAW',
                body={'values': values}
            ).execute()
        except Exception as e:
            if "Unable to parse range" in str(e):
                # Create the Processed sheet if it doesn't exist
                sheets_api.service.spreadsheets().batchUpdate(
                    spreadsheetId=spreadsheet_id,
                    body={
                        'requests': [{
                            'addSheet': {
                                'properties': {
                                    'title': 'Processed'
                                }
                            }
                        }]
                    }
                ).execute()
                
                # Add headers
                sheets_api.service.spreadsheets().values().update(
                    spreadsheetId=spreadsheet_id,
                    range="Processed!A1:C1",
                    valueInputOption='RAW',
                    body={
                        'values': [['Posting_ID', 'Opportunity_ID', 'Processed_Timestamp']]
                    }
                ).execute()
                
                # Retry the append operation
                sheets_api.service.spreadsheets().values().append(
                    spreadsheetId=spreadsheet_id,
                    range="Processed!A:C",
                    valueInputOption='RAW',
                    body={'values': values}
                ).execute()
            else:
                raise e
    except Exception as e:
        logging.error(f"Error logging processed candidate: {str(e)}")
        raise

def parse_evaluation_response(text: str) -> dict:
    try:
        decision_match = re.search(r'DECISION:\s*(SHORTLIST|REJECT)', text, re.IGNORECASE)
        decision = decision_match.group(1) if decision_match else None
        scores = {}
        score_patterns = {
            'technical': r'Technical Skills & Experience:\s*(\d+)/60',
            'skills': r'Technical Skills:\s*(\d+)/15',
            'experience': r'Experience Level:\s*(\d+)/15',
            'tools': r'Tools & Technologies:\s*(\d+)/15',
            'domain': r'Domain Knowledge:\s*(\d+)/15',
            'impact': r'Impact & Achievements:\s*(\d+)/40',
            'quantifiable': r'Quantifiable Impact:\s*(\d+)/20',
            'problem_solving': r'Problem Solving:\s*(\d+)/20'
        }
        for category, pattern in score_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                scores[category] = int(match.group(1))
            else:
                scores[category] = 0
        total_score = sum(scores.values())
        return {
            "decision": decision,
            "score": total_score,
            "scores": scores,
            "explanation": text
        }
    except Exception as e:
        logging.error(f"Error parsing evaluation response: {str(e)}")
        return {
            "decision": "ERROR",
            "score": 0,
            "scores": {},
            "explanation": text
        }

def evaluate_resume(job_description: str, recruiter_prompt: str, candidate_resume: str) -> dict:
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.0-flash',
        generation_config={
            "temperature": 0,
            "top_p": 0.1,
            "top_k": 1
        }
    )
    time.sleep(4)
    prompt = f"""   
You are an expert recruiter evaluating a candidate for a position. Your task is to thoroughly and objectively evaluate the candidate's resume against the job requirements. Be EXTREMELY strict and thorough in your evaluation. The criteria is based on the job description and the recruiter's prompt. This is a very important task and you need to be very objective in your evaluation.

EVALUATION CRITERIA (100 points total):

1. TECHNICAL SKILLS & EXPERIENCE (60 points)
   MANDATORY REQUIREMENTS (Must have ALL to pass):
   - Required technical skills as specified in job description (MANDATORY - REJECT if missing)
   - Minimum experience requirements as specified (MANDATORY - REJECT if missing)
   - Required tools/technologies mentioned in job description (MANDATORY - REJECT if missing)
   - Required domain knowledge (MANDATORY - REJECT if missing)
   
   Scoring Breakdown:
   - Technical Skills (0-15 points)
     * Basic skills: 5-7 points
     * Advanced skills: 8-15 points
   - Experience Level (0-15 points)
     * Meets minimum: 5-7 points
     * Exceeds minimum: 8-15 points
   - Tools & Technologies (0-15 points)
     * Basic proficiency: 5-7 points
     * Advanced proficiency: 8-15 points
   - Domain Knowledge (0-15 points)
     * Basic understanding: 5-7 points
     * Deep expertise: 8-15 points

2. IMPACT & ACHIEVEMENTS (40 points)
   MANDATORY REQUIREMENTS:
   - Must show quantifiable impact in previous roles
   - Must demonstrate problem-solving abilities
   
   Scoring Breakdown:
   - Quantifiable Impact (0-20 points)
     * Basic metrics mentioned: 5-10 points
     * Specific numbers and results: 11-20 points
   - Problem Solving (0-20 points)
     * Basic problem solving: 5-10 points
     * Complex problem solving with results: 11-20 points

DECISION RULES:
- REJECT if:
  * Missing ANY mandatory technical skill
  * Less than required experience
  * No quantifiable impact shown
  * Total score below 65
  * Missing any mandatory requirement
- SHORTLIST if:
  * Has ALL mandatory technical skills
  * Shows quantifiable impact
  * Total score 66 or above
  * Meets ALL experience requirements

---

**Job Description:**
{job_description}

**Recruiter's Prioritized Criteria:**
{recruiter_prompt}

**Candidate's Resume:**
{candidate_resume}

---

Respond with a clear, structured evaluation in this EXACT format:

DECISION: [SHORTLIST / REJECT]

SCORES:
1. Technical Skills & Experience: [X]/60
   - Technical Skills: [X]/15
   - Experience Level: [X]/15
   - Tools & Technologies: [X]/15
   - Domain Knowledge: [X]/15

2. Impact & Achievements: [X]/40
   - Quantifiable Impact: [X]/20
   - Problem Solving: [X]/20

TOTAL SCORE: [Sum of all scores]

DETAILED ANALYSIS:
[Provide a detailed analysis of the candidate's resume against each criterion. Justify each score and highlight any areas of strength or concern.]

RED FLAGS:
[List any specific red flags found in the resume, if any.]

IMPORTANT: Be extremely strict and objective. Only evaluate what is clearly stated in the resume. Avoid assumptions. If any mandatory requirement is missing or unclear, REJECT the candidate.
"""
    max_retries = 5
    base_delay = 60
    max_delay = 300
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            text = response.text.strip()
            logging.info("\nEvaluation Results:\n")
            logging.info(text)
            return parse_evaluation_response(text)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg:
                if "quota_value: 1000" in error_msg:
                    logging.error("Free tier quota exceeded. Please upgrade your plan or try again tomorrow.")
                    raise Exception("Free tier quota exceeded")
                else:
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logging.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}), waiting {delay} seconds...")
                    time.sleep(delay)
            elif "503" in error_msg:
                delay = min(base_delay * (2 ** attempt), max_delay)
                logging.warning(f"Service unavailable (attempt {attempt + 1}/{max_retries}), waiting {delay} seconds...")
                time.sleep(delay)
            elif "timeout" in error_msg.lower():
                delay = min(base_delay * (2 ** attempt), max_delay)
                logging.warning(f"Timeout occurred (attempt {attempt + 1}/{max_retries}), waiting {delay} seconds...")
                time.sleep(delay)
            else:
                logging.error(f"Unexpected error: {error_msg}")
                if attempt == max_retries - 1:
                    raise
    raise Exception("Failed to get evaluation after all retries")

def process_local_resumes():
    try:
        log_file = setup_logging()
        logging.info("Starting resume evaluation...")
        credentials = get_google_credentials()
        sheets_api = SheetsAPI(credentials)
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        job_posting_id = get_latest_posting_id(sheets_api, spreadsheet_id)
        if not job_posting_id:
            logging.error("No Posting_id found in Input sheet.")
            return
        logging.info(f"Processing job query: {job_posting_id}")
        job_configs = sheets_api.get_job_configs(spreadsheet_id)
        target_job_config = find_job_config(job_configs, job_posting_id)
        if not target_job_config:
            logging.error(f"\nNo job configuration found matching '{job_posting_id}' in Google Sheets.")
            logging.info("\nAvailable jobs in Google Sheets:")
            for idx, job_config in enumerate(job_configs, 1):
                logging.info(f"{idx}. {job_config.job_description[:120].replace(chr(10), ' ')}")
            return
        logging.info("\nJob Configuration:")
        logging.info("-" * 50)
        logging.info(f"Job Description:\n{target_job_config.job_description[:200]}...")
        logging.info(f"\nRecruiter Prompt:\n{target_job_config.recruiter_prompt[:200]}...")
        logging.info("-" * 50)
        lever_api = LeverAPI(os.getenv("LEVER_API_KEY"))
        
        # Initialize batch processing variables
        batch_size = 50
        max_resumes = 600  # Maximum number of resumes to process
        offset = 0
        total_processed = 0
        total_failed = 0
        total_skipped = 0
        
        while total_processed + total_skipped < max_resumes:
            # Download batch of resumes
            downloaded_resumes = lever_api.download_resume(
                posting_id=target_job_config.job_posting,
                limit=batch_size,
                offset=offset
            )
            
            if not downloaded_resumes:
                logging.info(f"No more resumes to process after offset {offset}")
                break
                
            logging.info(f"Downloaded batch of {len(downloaded_resumes)} resumes from Lever (in memory).")
            resume_processor = LocalResumeProcessor(
                candidates_dir=None  # Not used for in-memory
            )
            
            if not quota_manager.can_make_request():
                logging.error("Free tier quota exceeded for today. Please try again tomorrow.")
                break
                
            results = []
            processed_count = 0
            failed_count = 0
            skipped_count = 0
            
            for resume_bytes, candidate_id, candidate_name in downloaded_resumes:
                # Check if we've reached the maximum limit
                if total_processed + total_skipped + processed_count + skipped_count >= max_resumes:
                    logging.info(f"Reached maximum limit of {max_resumes} resumes")
                    break
                    
                logging.info(f"\nProcessing resume {processed_count + 1}/{len(downloaded_resumes)}: {candidate_id} ({candidate_name})")
                # Check if already processed
                if is_already_processed(sheets_api, spreadsheet_id, job_posting_id, candidate_id):
                    logging.info(f"Skipping {candidate_id} - already processed")
                    skipped_count += 1
                    continue
                    
                if not quota_manager.can_make_request():
                    logging.error(f"Free tier quota exceeded. Processed {processed_count} out of {len(downloaded_resumes)} resumes in this batch.")
                    logging.info("Saving partial results and stopping.")
                    save_results(results)
                    return
                    
                try:
                    resume_text = resume_processor.convert_pdf_to_text(resume_bytes)
                    if not resume_text:
                        logging.error(f"Could not parse resume for {candidate_id}")
                        failed_count += 1
                        continue
                        
                    quota_manager.increment_request()
                    evaluation = evaluate_resume(
                        job_description=target_job_config.job_description,
                        recruiter_prompt=target_job_config.recruiter_prompt,
                        candidate_resume=resume_text
                    )
                    results.append({
                        "candidate_id": candidate_id,
                        "decision": evaluation["decision"],
                        "score": evaluation["score"],
                        "scores": evaluation["scores"],
                        "explanation": evaluation["explanation"]
                    })
                    sheets_api.log_result(
                        spreadsheet_id,
                        target_job_config.job_description,
                        candidate_id,
                        evaluation["decision"],
                        evaluation["explanation"]
                    )
                    # Log the processed candidate
                    log_processed_candidate(sheets_api, spreadsheet_id, job_posting_id, candidate_id)
                    processed_count += 1
                    logging.info(f"Decision for {candidate_id}: {evaluation['decision']}")
                except Exception as e:
                    if "Free tier quota exceeded" in str(e):
                        logging.error(f"Free tier quota exceeded. Processed {processed_count} out of {len(downloaded_resumes)} resumes in this batch.")
                        logging.info("Saving partial results and stopping.")
                        save_results(results)
                        return
                    logging.error(f"Error processing resume for {candidate_id}: {str(e)}")
                    failed_count += 1
                    continue
                    
            # Update totals
            total_processed += processed_count
            total_failed += failed_count
            total_skipped += skipped_count
            
            # Save batch results
            save_results(results)
            
            # Log batch summary
            logging.info(f"\nBatch Summary (offset {offset}):")
            logging.info(f"- Successfully processed: {processed_count}")
            logging.info(f"- Failed to process: {failed_count}")
            logging.info(f"- Skipped (already processed): {skipped_count}")
            logging.info(f"- Total processed so far: {total_processed}")
            logging.info(f"- Total skipped so far: {total_skipped}")
            logging.info(f"- Remaining until max limit: {max_resumes - (total_processed + total_skipped)}")
            
            # Move to next batch
            offset += batch_size
            
            # If we got fewer resumes than the batch size, we're done
            if len(downloaded_resumes) < batch_size:
                break
                
        # Log final summary
        logging.info(f"\nFinal Evaluation Summary:")
        logging.info(f"- Total processed: {total_processed}")
        logging.info(f"- Total failed: {total_failed}")
        logging.info(f"- Total skipped: {total_skipped}")
        logging.info(f"- Maximum limit: {max_resumes}")
        
    except Exception as e:
        logging.error(f"Error in process_local_resumes: {str(e)}")
        import traceback
        logging.error("\nFull error traceback:")
        logging.error(traceback.format_exc())

def save_results(results):
    if not results:
        logging.warning("No results to save")
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f'evaluation_results_{timestamp}.csv'
    with open(results_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['candidate_id', 'decision', 'score', 'scores', 'explanation'])
        writer.writeheader()
        for result in results:
            result['scores'] = json.dumps(result['scores'])
            writer.writerow(result)
    logging.info(f"Results saved to {results_file}")

def main():
    process_local_resumes()

if __name__ == "__main__":
    main() 