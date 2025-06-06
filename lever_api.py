import os
import requests
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class Applicant:
    id: str
    name: str
    resume_url: str
    form_data: Dict
    stage: str
    

class LeverAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.lever.co/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def list_open_postings(self) -> List[Dict]:
        """List all open job postings."""
        try:
            response = requests.get(
                f"{self.base_url}/postings",
                params={"state": "published"},
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return []
        except Exception as e:
            print(f"Error listing open postings: {str(e)}")
            return []

    def list_all_postings(self) -> List[Dict]:
        """List all job postings regardless of state."""
        try:
            response = requests.get(
                f"{self.base_url}/postings",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return []
        except Exception as e:
            print(f"Error listing all postings: {str(e)}")
            return []

    def list_stages(self) -> List[Dict]:
        """List all available stages in the account."""
        try:
            response = requests.get(
                f"{self.base_url}/stages",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return []
        except Exception as e:
            print(f"Error listing stages: {str(e)}")
            return []

    def get_candidates_by_posting(self, posting_id: str) -> List[Dict]:
        """Get all candidates for a specific job posting."""
        try:
            response = requests.get(
                f"{self.base_url}/opportunities",
                params={
                    "posting_id": posting_id,
                    "archived": "false"
                },
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return []
        except Exception as e:
            print(f"Error getting candidates for posting {posting_id}: {str(e)}")
            return []

    def get_candidate_details(self, opportunity_id: str) -> Dict:
        """Get detailed information about a specific candidate."""
        try:
            response = requests.get(
                f"{self.base_url}/opportunities/{opportunity_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error getting candidate details for {opportunity_id}: {str(e)}")
            return {}

    def print_all_postings(self):
        """Print all job postings."""
        postings = self.list_all_postings()
        print("\nAll Job Postings:")
        print("-" * 50)
        for posting in postings:
            print(f"ID: {posting.get('id')}")
            print(f"Title: {posting.get('text')}")
            print(f"State: {posting.get('state', 'N/A')}")
            print(f"Department: {posting.get('categories', {}).get('department', 'N/A')}")
            print(f"Location: {posting.get('categories', {}).get('location', 'N/A')}")
            print(f"Team: {posting.get('categories', {}).get('team', 'N/A')}")
            print(f"Created: {posting.get('createdAt')}")
            print("-" * 50)

    def prin_all_open_postings(self):
        """List all open job postings."""
        postings = self.list_open_postings()
        print("\nOpen Job Postings:")
        print("-" * 50)
        for posting in postings:
            print(f"ID: {posting.get('id')}")
            print(f"Title: {posting.get('text')}")
            print(f"State: {posting.get('state', 'N/A')}")
            print("-" * 50)

    def print_all_stages(self):
        """Print all stages in the hiring process."""
        stages = self.list_stages()
        print("\nAvailable Stages:")
        print("-" * 50)
        for stage in stages:
            print(f"ID: {stage.get('id')}")
            print(f"Name: {stage.get('text')}")
            print(f"Type: {stage.get('type')}")
            print("-" * 50)

    def print_candidates_for_posting(self, posting_id: str):
        """Print all candidates for a specific job posting."""
        # Get posting details first
        posting = self.get_job_posting(posting_id)
        if not posting:
            print(f"\nError: Could not find job posting with ID {posting_id}")
            return
            
        # Get the posting title directly from the posting data
        posting_title = posting.get('text')
        if not posting_title:
            print(f"\nError: Could not get title for posting {posting_id}")
            return
            
        print(f"\nCandidates for {posting_title}:")
        print(f"Department: {posting.get('categories', {}).get('department', 'N/A')}")
        print(f"Location: {posting.get('categories', {}).get('location', 'N/A')}")
        print(f"Team: {posting.get('categories', {}).get('team', 'N/A')}")
        print("-" * 50)
        
        # Get candidates
        candidates = self.get_candidates_by_posting(posting_id)
        if not candidates:
            print("No candidates found for this position")
            return
            
        for candidate in candidates:
            print(f"Name: {candidate.get('name')}")
            print(f"ID: {candidate.get('id')}")
            print(f"Stage: {candidate.get('stage')}")
            print(f"Created: {candidate.get('createdAt')}")
            print(f"Last Activity: {candidate.get('lastActivityAt')}")
            
            # Get detailed candidate info
            details = self.get_candidate_details(candidate.get('id'))
            if details:
                print("Contact Info:")
                for contact in details.get('contact', []):
                    print(f"  - {contact.get('type')}: {contact.get('value')}")
            
            print("-" * 50)

    def test_connection(self) -> bool:
        """Test if the API key is valid and has necessary permissions."""
        try:
            response = requests.get(
                f"{self.base_url}/postings",
                headers=self.headers
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"API connection test failed: {str(e)}")
            return False

    def get_job_posting(self, posting_id: str) -> Dict:
        """Fetch job posting details from Lever."""
        try:
            response = requests.get(
                f"{self.base_url}/postings/{posting_id}",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            # The API returns the posting data wrapped in a 'data' field
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return {}
        except Exception as e:
            print(f"Error getting job posting {posting_id}: {str(e)}")
            return {}

    def move_candidate_to_stage(self, opportunity_id: str, stage_id: str) -> bool:
        """Move a candidate to a specific stage in Lever."""
        try:
            response = requests.put(
                f"{self.base_url}/opportunities/{opportunity_id}",
                headers=self.headers,
                json={"stage": stage_id}
            )
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error moving candidate {opportunity_id} to stage {stage_id}: {str(e)}")
            return False

    def get_stage_id_by_name(self, stage_name: str) -> str:
        """Get stage ID by stage name."""
        try:
            stages = self.list_stages()
            for stage in stages:
                if stage.get('text', '').lower() == stage_name.lower():
                    return stage.get('id')
            return None
        except Exception as e:
            print(f"Error getting stage ID for {stage_name}: {str(e)}")
            return None

    def tag_candidate_as_processed(self, opportunity_id: str) -> bool:
        """Tag a candidate as processed in Lever."""
        try:
            url = f"{self.base_url}/opportunities/{opportunity_id}/addTags"
            response = requests.post(
                url,
                headers=self.headers,
                json={"tags": ["processed"]}
            )
            response.raise_for_status()
            print(f"✅ Tagged candidate {opportunity_id} as processed")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to tag candidate {opportunity_id}: {str(e)} | Response: {getattr(e.response, 'text', '')}")
            return False

    def remove_processed_tag(self, opportunity_id: str) -> bool:
        """Remove the processed tag from a candidate.
        
        Args:
            opportunity_id: The ID of the candidate to untag
            
        Returns:
            bool: True if tag removal was successful, False otherwise
            
        Raises:
            Exception: If the API request fails
        """
        try:
            response = requests.delete(
                f"{self.base_url}/opportunities/{opportunity_id}/tags/processed",
                headers=self.headers
            )
            response.raise_for_status()
            print(f"✅ Removed processed tag from candidate {opportunity_id}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to remove processed tag from {opportunity_id}: {str(e)}")
            raise

    def get_candidate_tags(self, opportunity_id: str) -> List[str]:
        """Get all tags for a candidate.
        
        Args:
            opportunity_id: The ID of the candidate
            
        Returns:
            List[str]: List of tag names
            
        Raises:
            Exception: If the API request fails
        """
        try:
            response = requests.get(
                f"{self.base_url}/opportunities/{opportunity_id}",
                headers=self.headers
            )
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict) and 'data' in data:
                return data['data'].get('tags', [])
            return []
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get tags for {opportunity_id}: {str(e)}")
            raise

    def download_resume(self, posting_id: str = "225695e6-a447-4531-a9a6-af783325d22e") -> List[tuple[bytes, str, str]]:
        try:
            target_job = self.get_job_posting(posting_id)
            if not target_job:
                print(f"❌ Could not find job posting with ID: {posting_id}")
                return []

            print(f"📌 Found job posting: {target_job.get('text')}")

            new_applicant_stage_id = self.get_stage_id_by_name("New Applicant")
            if not new_applicant_stage_id:
                print("❌ Could not find New Applicant stage")
                return []

            response = requests.get(
                f"{self.base_url}/opportunities",
                params={
                    "posting_id": posting_id,
                    "archived": "false",
                    "stage_id": new_applicant_stage_id,
                    "limit": 25,
                    "sort": "-createdAt"
                },
                headers=self.headers
            )
            response.raise_for_status()
            opportunities = response.json().get("data", [])

            if not opportunities:
                print("⚠️ No candidates found in New Applicant stage")
                return []

            downloaded_resumes = []

            for opportunity in opportunities:
                candidate_id = opportunity.get("id")
                candidate_name = opportunity.get("name", "unknown")

                # Skip if already tagged "processed"
                if "processed" in opportunity.get("tags", []):
                    print(f"⏩ Skipping already processed candidate: {candidate_id}")
                    continue

                try:
                    resumes_response = requests.get(
                        f"{self.base_url}/opportunities/{candidate_id}/resumes",
                        headers=self.headers
                    )
                    resumes_response.raise_for_status()
                    resumes = resumes_response.json().get("data", [])

                    if not resumes:
                        print(f"⚠️ No resume found for candidate {candidate_id}")
                        continue

                    for resume in resumes:
                        resume_id = resume.get("id")
                        if not resume_id:
                            continue

                        download_url = f"{self.base_url}/opportunities/{candidate_id}/resumes/{resume_id}/download"
                        file_response = requests.get(download_url, headers=self.headers)
                        file_response.raise_for_status()

                        resume_bytes = file_response.content
                        print(f"📥 Downloaded resume for {candidate_name}")
                        downloaded_resumes.append((resume_bytes, candidate_id, candidate_name))

                        # Tag as processed and verify
                        try:
                            if self.tag_candidate_as_processed(candidate_id):
                                print(f"✅ Successfully tagged and processed {candidate_name}")
                            else:
                                print(f"⚠️ Failed to tag {candidate_name} as processed")
                        except Exception as tag_error:
                            print(f"❌ Error tagging {candidate_name}: {str(tag_error)}")

                except Exception as e:
                    print(f"❌ Error processing candidate {candidate_id}: {str(e)}")

            print(f"✅ Finished downloading {len(downloaded_resumes)} resumes (in memory)")
            return downloaded_resumes

        except Exception as e:
            print(f"❌ Error in download_resume: {str(e)}")
            return []
    
if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Initialize Lever API
    api = LeverAPI(os.getenv("LEVER_API_KEY"))
    
    # Test connection
    if not api.test_connection():
        print("Failed to connect to Lever API")
        exit(1)
    
    # Print all open postings
    api.list_open_postings()
    api.prin_all_open_postings()
    # api.print_all_postings()
    # # Print all stages
    api.print_all_stages()
    # api.print_candidates_for_posting("225695e6-a447-4531-a9a6-af783325d22e")
    # For each posting, print its candidates
    api.download_resume()
