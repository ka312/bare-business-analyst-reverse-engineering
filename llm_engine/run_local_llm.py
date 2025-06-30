import requests
import os
import json
import time

OLLAMA_API_URL = "http://localhost:11434/api/generate"

# Load BRD prompt template
def load_brd_prompt():
    """Load the BRD prompt template with error handling."""
    try:
        with open("prompts/brd_prompt.txt", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("Warning: brd_prompt.txt not found, using default prompt")
        return """
You are an expert Business Analyst AI assistant specialized in analyzing software projects and generating Business Requirements Documents (BRDs).

Your task is to analyze the following Python project and generate a BRD suitable for business stakeholders, product managers, and leadership teams.

Focus on the business problem being solved, the value proposition, user goals, key functional and non-functional requirements, and stakeholder needs.

Avoid low-level technical details.

Return your output in the following format:

---

# Business Requirements Document (BRD)

**Project Title:** <Infer from Code>

**Version:** 1.0

**Date:** <today's date>

---

## 1. Executive Summary
<High-level summary of the project's business purpose>

## 2. Business Objectives
- <Objective 1>
- <Objective 2>

## 3. Scope
**In Scope:**
- <What this system includes>

**Out of Scope:**
- <What this system excludes>

## 4. Stakeholders
- <List of relevant roles>

## 5. Functional Requirements
| ID | Requirement Description |
|----|--------------------------|
| FR1 | <Requirement> |
| FR2 | <Requirement> |

## 6. Non-Functional Requirements
| ID | Requirement Description |
|----|--------------------------|
| NFR1 | <Requirement> |
| NFR2 | <Requirement> |

## 7. Assumptions
- <Any assumed context>

## 8. Constraints
- <Any limits>

## 9. Technical Architecture (if inferred)
- <Briefly describe system setup if clear from code>

## 10. Success Metrics
- <How business success is measured>

---

Here is the project code:

{{CODE_BLOCK}}
"""
    except Exception as e:
        print(f"Error loading BRD prompt: {e}")
        return "Analyze the following code and provide business requirements:\n\n{{CODE_BLOCK}}"


def check_ollama_connection():
    """Check if Ollama is running and accessible."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False


def generate_brd(function_source, model):
    """Generate Business Requirements Document from code."""
    # Input validation
    if not function_source or not function_source.strip():
        return "Error: No code provided for analysis."
    
    if not model:
        return "Error: No model specified."
    
    # Check Ollama connection
    if not check_ollama_connection():
        return "Error: Cannot connect to Ollama. Please ensure Ollama is running on localhost:11434"
    
    # Load and prepare prompt
    prompt_template = load_brd_prompt()
    prompt = prompt_template.replace("{{CODE_BLOCK}}", function_source)
    
    # Truncate prompt if too long (some models have context limits)
    if len(prompt) > 32000:  # Conservative limit
        print(f"Warning: Prompt is {len(prompt)} characters, truncating...")
        code_part = function_source[:20000]  # Keep first 20k chars of code
        prompt = prompt_template.replace("{{CODE_BLOCK}}", code_part + "\n\n[... code truncated ...]")
    
    payload = {
        "model": model, 
        "prompt": prompt, 
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 4096  # Context window
        }
    }
    
    try:
        print(f"Making request to Ollama with model: {model}")
        print(f"Prompt length: {len(prompt)} characters")
        
        # Add retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    OLLAMA_API_URL,
                    json=payload,
                    timeout=300  # 5 minutes timeout
                )
                
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result.get("response", "").strip()
                    
                    if generated_text:
                        return generated_text
                    else:
                        return "Error: Empty response from LLM."
                
                elif response.status_code == 404:
                    return f"Error: Model '{model}' not found. Please check if the model is installed in Ollama."
                
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    print(f"Error response: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        print(f"Retrying in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                    
                    return f"Error: {error_msg}"
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"Request timed out, retrying... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)
                    continue
                return "Error: Request timed out. The model might be too slow or the prompt too long."
                
            except requests.exceptions.ConnectionError:
                return "Error: Cannot connect to Ollama. Please ensure Ollama is running."
                
        return "Error: Max retries exceeded."
        
    except requests.exceptions.RequestException as e:
        return f"Error: Request failed - {str(e)}"

def generate_process_flow(code_source, model):
    """Generate Business Process Flow from code."""
    # Input validation
    if not code_source or not code_source.strip():
        return "Error: No code provided for process flow analysis."
    
    if not model:
        return "Error: No model specified."
    
    # Check Ollama connection
    if not check_ollama_connection():
        return "Error: Cannot connect to Ollama. Please ensure Ollama is running on localhost:11434"
    
    # Process flow prompt template
    process_flow_prompt = """
You are an expert Business Analyst AI assistant specialized in analyzing software code and extracting business process flows.

Your task is to analyze the following Python code and identify the business process steps, workflow, and decision points.

Focus on:
1. Main business processes and workflows
2. Decision points and conditional logic
3. Data flow and transformations
4. User interactions and system responses
5. Sequential steps in business operations

Return your output as a numbered list of business process steps in this format:

1. [Step Description] - [Business Purpose]
2. [Step Description] - [Business Purpose]
3. [Decision Point] - [Condition and Outcomes]
4. [Step Description] - [Business Purpose]

Keep each step concise but descriptive enough for business stakeholders to understand.

Here is the code to analyze:

{{CODE_BLOCK}}
"""
    
    # Prepare prompt
    prompt = process_flow_prompt.replace("{{CODE_BLOCK}}", code_source)
    
    # Truncate prompt if too long
    if len(prompt) > 32000:
        print(f"Warning: Process flow prompt is {len(prompt)} characters, truncating...")
        code_part = code_source[:20000]
        prompt = process_flow_prompt.replace("{{CODE_BLOCK}}", code_part + "\n\n[... code truncated ...]")
    
    payload = {
        "model": model, 
        "prompt": prompt, 
        "stream": False,
        "options": {
            "temperature": 0.7,
            "top_p": 0.9,
            "num_ctx": 4096
        }
    }
    
    try:
        print(f"Making process flow request to Ollama with model: {model}")
        print(f"Process flow prompt length: {len(prompt)} characters")
        
        # Add retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    OLLAMA_API_URL,
                    json=payload,
                    timeout=300
                )
                
                print(f"Process flow response status: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    generated_text = result.get("response", "").strip()
                    
                    if generated_text:
                        return generated_text
                    else:
                        return "Error: Empty response from LLM for process flow generation."
                
                elif response.status_code == 404:
                    return f"Error: Model '{model}' not found. Please check if the model is installed in Ollama."
                
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    print(f"Process flow error response: {error_msg}")
                    
                    if attempt < max_retries - 1:
                        print(f"Retrying process flow generation in 2 seconds... (attempt {attempt + 1}/{max_retries})")
                        time.sleep(2)
                        continue
                    
                    return f"Error: {error_msg}"
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"Process flow request timed out, retrying... (attempt {attempt + 1}/{max_retries})")
                    time.sleep(2)
                    continue
                return "Error: Process flow request timed out. The model might be too slow or the prompt too long."
                
            except requests.exceptions.ConnectionError:
                return "Error: Cannot connect to Ollama. Please ensure Ollama is running."
                
        return "Error: Max retries exceeded for process flow generation."
        
    except requests.exceptions.RequestException as e:
        return f"Error: Process flow request failed - {str(e)}"
  