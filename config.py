import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
API_KEY = os.getenv('API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not API_KEY:
    raise ValueError("API_KEY not found in environment variables. Please set it in .env file")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in .env file")