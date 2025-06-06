import os
from typing import List, Dict
from dataclasses import dataclass
from markitdown import MarkItDown

@dataclass
class Candidate:
    name: str
    resume_path: str
    form_data: Dict

class LocalResumeProcessor:
    def __init__(self, candidates_dir: str):
        self.candidates_dir = candidates_dir
        
        self.markitdown = MarkItDown(enable_plugins=False)

    def get_candidates(self) -> List[Candidate]:
        """Get all candidates from the candidates directory."""
        candidates = []
        for filename in os.listdir(self.candidates_dir):
            if filename.endswith(('.pdf', '.docx')):
                # Use filename without extension as candidate name
                name = os.path.splitext(filename)[0]
                resume_path = os.path.join(self.candidates_dir, filename)
                
                # For testing, we'll use dummy form data
                form_data = {
                    "Notice Period": "30 days",
                    "Current CTC": "10 LPA",
                    "Expected CTC": "15 LPA"
                }
                
                candidates.append(Candidate(
                    name=name,
                    resume_path=resume_path,
                    form_data=form_data
                ))
        return candidates

    


    def get_successful_candidates(self) -> List[str]:
        """Get all successful example resumes as markdown text."""
        candidates_texts = []
        for filename in os.listdir(self.candidates_dir):
            candidates_texts.append(filename)
        return candidates_texts    

    def parse_candidate_resume(self, candidate: Candidate) -> str:
        """Parse a candidate's resume using MarkItDown."""
        try:
            result = self.markitdown.convert(candidate.resume_path)
            return result.text_content
        except Exception as e:
            print(f"Error parsing resume {candidate.resume_path}: {str(e)}")
            return None

    def convert_pdf_to_text(self, pdf_content: bytes) -> str:
        """Convert PDF content to text using MarkItDown."""
        try:
            # Create a temporary file to store the PDF content
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file_path = temp_file.name
            
            # Convert the temporary file to text
            result = self.markitdown.convert(temp_file_path)
            
            # Clean up the temporary file
            os.unlink(temp_file_path)
            
            return result.text_content
        except Exception as e:
            print(f"Error converting PDF to text: {str(e)}")
            return None 