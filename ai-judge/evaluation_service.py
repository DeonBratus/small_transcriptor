"""
Evaluation service using the new processor architecture.
"""

import requests
import json
from typing import Generator, Optional, Dict, Any
from processors import ProcessorFactory, BaseFileProcessor


class EvaluationService:
    """Service for evaluating documents and presentations."""
    
    def __init__(self, vision_model: str = "llava", eval_model: str = "llama3.2", 
                 ollama_base_url: str = "http://localhost:11434"):
        """
        Initialize evaluation service.
        
        Args:
            vision_model: Model for image description
            eval_model: Model for evaluation
            ollama_base_url: Base URL for Ollama API
        """
        self.vision_model = vision_model
        self.eval_model = eval_model
        self.ollama_base_url = ollama_base_url.rstrip('/')
    
    def evaluate_document(self, doc_path: str, presentation_path: Optional[str] = None) -> str:
        """
        Evaluate document and optionally presentation.
        
        Args:
            doc_path: Path to document file
            presentation_path: Optional path to presentation file
            
        Returns:
            Evaluation result
        """
        # Process document
        doc_processor = ProcessorFactory.create_processor(doc_path)
        doc_text = doc_processor.process()
        
        # Process presentation if provided
        presentation_text = ""
        if presentation_path:
            pptx_processor = ProcessorFactory.create_processor(
                presentation_path, 
                vision_model=self.vision_model,
                ollama_base_url=self.ollama_base_url
            )
            presentation_text = pptx_processor.process()
        
        # Build prompt and evaluate
        if presentation_text:
            task_prompt = self._build_thesis_presentation_prompt(doc_text, presentation_text)
        else:
            task_prompt = self._build_thesis_only_prompt(doc_text)
        
        full_prompt = f"{self._system_prompt()}\n\n{task_prompt}"
        
        return self._call_evaluation_model(full_prompt)
    
    def evaluate_document_stream(self, doc_path: str, presentation_path: Optional[str] = None) -> Generator[str, None, None]:
        """
        Stream evaluation results.
        
        Args:
            doc_path: Path to document file
            presentation_path: Optional path to presentation file
            
        Yields:
            Evaluation result chunks
        """
        # Process document
        doc_processor = ProcessorFactory.create_processor(doc_path)
        doc_text = doc_processor.process()
        
        # Process presentation if provided
        presentation_text = ""
        if presentation_path:
            pptx_processor = ProcessorFactory.create_processor(
                presentation_path,
                vision_model=self.vision_model,
                ollama_base_url=self.ollama_base_url
            )
            presentation_text = pptx_processor.process()
        
        # Build prompt and evaluate
        if presentation_text:
            task_prompt = self._build_thesis_presentation_prompt(doc_text, presentation_text)
        else:
            task_prompt = self._build_thesis_only_prompt(doc_text)
        
        full_prompt = f"{self._system_prompt()}\n\n{task_prompt}"
        
        yield from self._call_evaluation_model_stream(full_prompt)
    
    def _call_evaluation_model(self, prompt: str) -> str:
        """Call evaluation model with prompt."""
        try:
            payload = {
                "model": self.eval_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 2500
                }
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=300
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "Evaluation failed")
            else:
                return f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            return f"Error during evaluation: {str(e)}"
    
    def _call_evaluation_model_stream(self, prompt: str) -> Generator[str, None, None]:
        """Call evaluation model with streaming."""
        try:
            payload = {
                "model": self.eval_model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": 0.0,
                    "num_predict": 2500
                }
            }

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=300
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            if 'response' in data:
                                yield data['response']
                            if data.get('done', False):
                                break
                        except json.JSONDecodeError:
                            continue
            else:
                yield f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            yield f"Error during evaluation: {str(e)}"
    
    @staticmethod
    def _system_prompt() -> str:
        """Get system prompt for evaluation."""
        return """
You are an experienced academic reviewer and pedagogue. For every request you must produce exactly two sections in this order:

1) A short free-text reasoning section bracketed by "<THOUGHT>" and "</THOUGHT>". In this section, give concise, specific, reviewer-style notes about the submission (intuition, main strengths/weaknesses you will weigh, and reasoning steps you used). Keep this section focused and specific to the provided document (max ~200-300 words).

2) A machine-readable evaluation bracketed by "<JSON>" and "</JSON>". Output only valid JSON in this block (no extra text). Follow the schema described in the incoming task prompt (the task prompt will request either thesis-only fields or thesis+presentation fields). For each numeric rating, use the requested integer scale. For list fields, return JSON arrays of strings. For boolean fields, use true/false.

Always obey the specific fields, labels and rating scales specified in the task prompt. If the task prompt includes both a thesis and presentation, include the presentation fields. If the task prompt contains only a thesis, omit presentation fields.

Do not output anything else outside the two sections. Be concise and deterministic: set tone professional, neutral, and specific. When you mention weaknesses, be constructive and give concrete ways to improve.
"""
    
    @staticmethod
    def _build_thesis_presentation_prompt(doc_text: str, presentation_text: str) -> str:
        """Build prompt for thesis and presentation evaluation."""
        return f"""
Instructions:
Evaluate the following THESIS/DOCUMENT and the PRESENTATION according to the general evaluation criteria below.
Return two sections exactly as the system prompt requires: <THOUGHT> and <JSON>.

Evaluation criteria (main, general — labels you must use in the JSON):
1. "Relevance" / "Актуальность темы доклада"
2. "Literature_and_Originality" / "Полнота обзора и оригинальность"
3. "Practical_Significance" / "Практическая значимость"
4. "Presentation_and_QA" / "Качество презентации и ответов на вопросы"
5. "Author_Contribution" / "Личный вклад автора"

--- DOCUMENT BEGIN ---
{doc_text}
--- DOCUMENT END ---

--- PRESENTATION TRANSCRIPT BEGIN ---
{presentation_text}
--- PRESENTATION TRANSCRIPT END ---

Please produce:
- <THOUGHT>: brief, specific notes about reasoning and priorities for scoring the document and presentation (max ~200-300 words).
- <JSON>: an object with the following fields (in this exact order):

- "Summary": string. Short summary of the paper and its main contributions.
- "Strengths": [string]. List of strengths.
- "Weaknesses": [string]. List of weaknesses or missing parts.
- "Relevance": integer 1-4 (low, medium, high, very high).
- "Literature_and_Originality": integer 1-4 (low, medium, high, very high).
- "Practical_Significance": integer 1-4 (low, medium, high, very high).
- "Author_Contribution": integer 1-4 (low, medium, high, very high).
- "Presentation_and_QA": integer 1-4 (low, medium, high, very high).
- "PresentationNotes": [string]. Brief, concrete notes about delivery and answers to questions.
- "Soundness": integer 1-4 (poor, fair, good, excellent).
- "Questions": [string]. Clarifying questions for the authors.
- "Limitations": [string]. Limitations and possible negative societal impacts.
- "Ethical_Concerns": boolean.
- "Overall": integer 1-10 (1 = Very Strong Reject, 2 = Strong Reject, 3 = Reject, 4 = Borderline reject, 5 = Borderline, 6 = Weak Accept, 7 = Accept, 8 = Strong Accept, 9 = Very Strong Accept, 10 = Award quality).
- "Confidence": integer 1-5 (low, medium, high, very high, absolute).
- "Decision": string, one of ["Accept", "Reject"].

Return only the two required blocks. Do not add extra commentary.
"""
    
    @staticmethod
    def _build_thesis_only_prompt(doc_text: str) -> str:
        """Build prompt for thesis-only evaluation."""
        return f"""
Instructions:
Evaluate the following THESIS/DOCUMENT according to the general evaluation criteria below.
Return two sections exactly as the system prompt requires: <THOUGHT> and <JSON>.

Evaluation criteria (main, general — translated and written as labels you must use in the JSON):
1. "Relevance" / "Актуальность темы доклада" — How relevant the topic is to current challenges in the field.
2. "Literature_and_Originality" / "Полнота обзора и оригинальность" — Completeness of literature review, analysis of prior solutions and their shortcomings, and the originality/novelty / theoretical significance of the proposed solution.
3. "Practical_Significance" / "Практическая значимость" — Practical impact and the feasibility/quality of practical implementation (if applicable).
4. "Author_Contribution" / "Личный вклад автора" — Degree of author's personal contribution to the solution.
5. "PresentationQuality" is NOT required in this variant (omit presentation fields).

--- DOCUMENT BEGIN ---
{doc_text}
--- DOCUMENT END ---

Please produce:
- <THOUGHT>: brief, specific notes about reasoning and priorities for scoring this document.
- <JSON>: an object with the following fields (in this exact order):

- "Summary": string. Short summary of the paper and its main contributions.
- "Strengths": [string]. List of strengths.
- "Weaknesses": [string]. List of weaknesses or missing parts.
- "Relevance": integer 1-4 (low, medium, high, very high).
- "Literature_and_Originality": integer 1-4 (low, medium, high, very high).
- "Practical_Significance": integer 1-4 (low, medium, high, very high).
- "Author_Contribution": integer 1-4 (low, medium, high, very high).
- "Soundness": integer 1-4 (poor, fair, good, excellent).
- "Questions": [string]. Clarifying questions for the authors.
- "Limitations": [string]. Limitations and possible negative societal impacts.
- "Ethical_Concerns": boolean.
- "Overall": integer 1-10 (1 = Very Strong Reject, 2 = Strong Reject, 3 = Reject, 4 = Borderline reject, 5 = Borderline, 6 = Weak Accept, 7 = Accept, 8 = Strong Accept, 9 = Very Strong Accept, 10 = Award quality).
- "Confidence": integer 1-5 (low, medium, high, very high, absolute).
- "Decision": string, one of ["Accept", "Reject"].

Return only the two required blocks. Do not add extra commentary.
"""
