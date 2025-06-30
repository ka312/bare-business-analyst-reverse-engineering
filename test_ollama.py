import requests
import json

def test_ollama_api():
    """Test if Ollama API is working with codellama:13b and a short prompt"""
    url = "http://localhost:11434/api/generate"
    
    # Very short test payload
    payload = {
        "model": "codellama:13b",
        "prompt": "Say hello.",
        "stream": False
    }
    
    try:
        print("Testing Ollama API with codellama:13b...")
        response = requests.post(url, json=payload, timeout=120)
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')}")
            return True
        else:
            print(f"Error Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return False
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        return False

if __name__ == "__main__":
    test_ollama_api() 