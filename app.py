import os
import re
import requests
import urllib.parse
from bs4 import BeautifulSoup
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv('Groq_Api_key')
client = Groq(api_key=groq_api_key)

def search_duckduckgo(query):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        encoded_query = urllib.parse.quote(query)
        url = f'https://html.duckduckgo.com/html/?q={encoded_query}'
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for result in soup.find_all('a', class_='result__a')[:5]:
                title = result.text.strip()
                link = result.get('href')
                
                if link and link.startswith('http'):
                    results.append({
                        'title': title,
                        'link': link
                    })
            
            return results
        else:
            print(f"Search failed with status code: {response.status_code}")
            return []
    
    except Exception as e:
        print(f"Search error: {e}")
        return []

def extract_text_from_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script, style, and other non-content elements
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            # Extract text
            text = soup.get_text(separator=' ', strip=True)
            
            # Split into sentences and filter
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
            
            # Filter meaningful sentences (more than 10 words)
            filtered_sentences = [
                s for s in sentences 
                if len(s.split()) > 10 and len(s) < 500
            ]
            
            # Join first 10 sentences or less
            return ' '.join(filtered_sentences[:10])
        
        return ""
    
    except Exception as e:
        print(f"Text extraction error from {url}: {e}")
        return ""

def generate_context_aware_response(query, search_context):
    """Generate a response using Groq API with web search context."""
    try:
        prompt = f"""
        You are an expert information assistant. Use the following context to provide 
        a comprehensive and accurate answer to the query.

        Query: "{query}"

        Available Context:
        {search_context}

        Guidelines:
        - Base your answer primarily on the provided context
        - If context is insufficient, state that clearly
        - Provide a precise, informative response
        - Aim for 3-5 sentences
        - Include key details from the context
        """

        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "You are a precise and helpful information assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )

        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"Error generating response: {e}"

def main():
    print("Web-Assisted Query Answering System")
    print("Type 'exit' to quit\n")

    while True:
        # Get user query
        query = input("Enter your search request: ").strip()
        
        if query.lower() in ['exit', 'quit', 'q']:
            break

        # Perform web search
        search_results = search_duckduckgo(query)
        
        if not search_results:
            print("No search results found.")
            continue

        # Collect context from search results
        search_context = ""
        for result in search_results:
            text = extract_text_from_url(result['link'])
            search_context += f"Source: {result['title']}\n{text}\n\n"

        # Generate response using context
        answer = generate_context_aware_response(query, search_context)
        print("\n--- Answer ---")
        print(answer)
        print("\n")

if __name__ == "__main__":
    main()