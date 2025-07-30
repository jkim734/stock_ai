
import time
from dotenv import load_dotenv
import os

import re
import regex
import json
load_dotenv()


from google import genai
import io
from google.genai import types
import httpx


### Gemini API 호출 모듈

model_name = "gemini-2.0-flash-001"

client = genai.Client(api_key=os.getenv("GOOGLE_AI_API_KEY"))
# .env에 넣고, gitignore에 .env 추가하고, 주석해재한다음에 사용


# doc_url_1 = "https://arxiv.org/pdf/1706.03762"
# # doc_url_2 = "https://arxiv.org/pdf/2403.05530"

# # Retrieve and upload both PDFs using the File API
# doc_data_1 = io.BytesIO(httpx.get(doc_url_1).content)
# # doc_data_2 = io.BytesIO(httpx.get(doc_url_2).content)

# sample_pdf_1 = client.files.upload(
#   file=doc_data_1,
#   config=dict(mime_type='application/pdf')
# )
# # sample_pdf_2 = client.files.upload(
# #   file=doc_data_2,
# #   config=dict(mime_type='application/pdf')
# # )

# attachments = [sample_pdf_1] # sample_pdf_2, sample_pdf_3, ...]

attachments = None

def ask_question_to_gemini_cache(prompt, attachments=None, max_retries=5, retry_delay=5):
    start_time = time.time()
    if attachments:
        prompt = [prompt]
        for pdf in attachments:
            prompt.append(pdf)
    else: 
        prompt += "NO ATTACHMENTS PROVIDED."
    for attempt in range(max_retries):
        try:
            print(f"attempt {attempt} starting at {time.time() - start_time:.2f}s")
            api_start = time.time()
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3
                )
            )
            print(f"API call took {time.time() - api_start:.2f}s")
            token_info = {
                "prompt_token_count": response.usage_metadata.prompt_token_count,
                "candidates_token_count": response.usage_metadata.candidates_token_count,
                "total_token_count": response.usage_metadata.total_token_count
            }
            print(f"Total time for successful response: {time.time() - start_time:.2f}s")
            return response.text
        except genai.errors.ServerError as e:
            if e.code == 503:
                print(f"Rate limit exceeded (attempt {attempt + 1}/{max_retries}) at {time.time() - start_time:.2f}s. Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print(f"Gemini API error (attempt {attempt + 1}/{max_retries}) at {time.time() - start_time:.2f}s: {e}")
                raise
        except Exception as e:
            print(f"Unexpected error (attempt {attempt + 1}/{max_retries}) at {time.time() - start_time:.2f}s: {e}")
            raise

    print(f"Failed after {max_retries} attempts. Total time: {time.time() - start_time:.2f}s")
    return None


def json_match(input_string):
    """
    Use regex to extract JSON from a string.
    """
    print("input_string: ", input_string)
    pattern_backticks = r'```json\s*(\{(?:[^{}]|(?R))*\})\s*```'
    m = regex.search(pattern_backticks, input_string)
    if m:
        json_str = m.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    pattern_simple = r'(\{(?:[^{}]|(?R))*\})'
    m = regex.search(pattern_simple, input_string)
    if m:
        json_str = m.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None
    return None


print(json_match(ask_question_to_gemini_cache("How do transformers work?", attachments=attachments)))