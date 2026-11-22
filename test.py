from dotenv import load_dotenv; import os; from google import genai;   
load_dotenv(); c = genai.Client(api_key=os.getenv('GEMINI_API_KEY')); [print(m, '-> OK:', c.models.generate_content(model=m, contents='OK').text.strip()) if True 
    else None for m in ['gemini-3.5-flash-lite', 'gemini-3.5-flash',
    'gemini-3.6-flash', 'gemini-3.1-flash-lite', 'gemini-2.5-flash-lite']]