import os
import re
import requests
import urllib.parse
import gradio as gr
from bs4 import BeautifulSoup
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv('Groq_Api_key'))

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
            for result in soup.find_all('a', class_='result__a')[:3]:
                title = result.text.strip()
                link = result.get('href')
                
                if link and link.startswith('http'):
                    results.append({
                        'title': title,
                        'link': link
                    })
            
            return results
        else:
            return []
    
    except Exception:
        return []

def extract_text_from_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = soup.get_text(separator=' ', strip=True)
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?)\s', text)
            
            filtered_sentences = [
                s for s in sentences 
                if len(s.split()) > 10 and len(s) < 500
            ]
            
            return ' '.join(filtered_sentences[:5])
        
        return ""
    except Exception:
        return ""

def generate_response(query, search_context):
    try:
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "You are a concise and direct information assistant, If you can analyze that user query dont need any Context then directly reply without waiting for context"},
                {"role": "user", "content": f"Query: {query}\n\nContext: {search_context}\n\nProvide a clear and direct answer."}
            ],
            temperature=0.2,
            max_tokens=350
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        return f"Error generating response: {e}"

def process_query(message, history):
    # Simple greeting handling
    if re.match(r'^(hi+|hello+|hey+|greetings|what\'?s up)\b', message.lower().strip()):
        return "Hello! How can I help you today?"

    # Perform web search
    search_results = search_duckduckgo(message)
    
    if not search_results:
        return "I couldn't find any relevant information. Could you rephrase your query?"

    # Collect context from search results
    search_context = "\n".join([
        f"Source: {result['title']}\n{extract_text_from_url(result['link'])}" 
        for result in search_results
    ])

    # Generate response using context
    return generate_response(message, search_context)

def main():
    interface = gr.ChatInterface(
        fn=process_query,
        title="Web-Assisted Query Answering System",
        description="Ask a detailed question and get a context-aware response from web searches!",
        type="messages" 
    )
    interface.launch()

if __name__ == "__main__":
    main()