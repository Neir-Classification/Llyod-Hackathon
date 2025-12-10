import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
else:
    client = OpenAI(api_key=api_key)
    try:
        # List available models
        models = client.models.list()
        print("Successfully authenticated with OpenAI API")
        print(f"\nAvailable models ({len(models.data)} total):")
        for model in models.data:
            print(f"  - {model.id}")
    except Exception as e:
        print(f"Error: {str(e)}")