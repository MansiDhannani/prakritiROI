import os
import httpx
from groq import Groq
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def test_groq_key():
    # Get the key from environment
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        print("❌ Error: GROQ_API_KEY not found in your .env file.")
        print("Please ensure you have a .env file with: GROQ_API_KEY=your_key_here")
        return

    print(f"🔍 Testing Groq API Key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        # Explicitly create an httpx client to avoid the 'proxies' argument bug
        # that occurs during auto-detection in some environments.
        http_client = httpx.Client(timeout=30.0)
        
        # Initialize the official Groq client with the custom http_client
        client = Groq(api_key=api_key, http_client=http_client)
        
        # Attempt a simple completion using a standard model
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Confirm if the API key is working by saying 'System Online'."}
            ],
            max_tokens=50,
            temperature=0.5
        )
        
        print("\n✨ API Key is WORKING!")
        print(f"🤖 Groq Response: {completion.choices[0].message.content}")
        http_client.close()
        
    except Exception as e:
        print("\n❌ API Key test FAILED.")
        print(f"Error details: {str(e)}")

if __name__ == "__main__":
    test_groq_key()