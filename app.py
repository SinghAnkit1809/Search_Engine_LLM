import os
import re
import requests
import urllib.parse
import gradio as gr
from bs4 import BeautifulSoup
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_api_key = os.getenv('Groq_Api_key')
client = Groq(api_key=groq_api_key)

def should_perform_web_search(query):
    """
    Determine if a web search is necessary for the query.
    
    Filters out:
    - Greetings
    - Simple questions
    - Short, casual conversation starters
    """
    # Convert to lowercase and strip
    query = query.lower().strip()
    
    # List of patterns to ignore
    ignore_patterns = [
        r'^hi+\b',
        r'^hello+\b',
        r'^hey+\b',
        r'^good (morning|afternoon|evening)',
        r'^how are you+\b',
        r'^what\'?s up+\b',
        r'^yo+\b',
        r'^greetings+\b',
        r'^hi there+\b',
        r'^thank(s| you)+\b',
        r'^cool+\b',
        r'^nice+\b'
    ]
    
    # Check if query matches any ignore patterns
    for pattern in ignore_patterns:
        if re.match(pattern, query):
            return False
    
    # Only search for queries longer than 4 words or containing specific search indicators
    search_indicators = [
        'tell me about', 
        'explain', 
        'what is', 
        'who is', 
        'how does', 
        'why do', 
        'describe', 
        'information about'
    ]
    
    # Check for search indicators or query length
    if len(query.split()) > 4:
        return True
    
    for indicator in search_indicators:
        if indicator in query:
            return True
    
    return False

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
    """Generate a more direct and concise response using Groq API with web search context."""
    try:
        prompt = f"""
        You are an expert information assistant. Provide a clear, direct, and concise answer to the query. 
        
        Key Guidelines:
        - Be as straightforward and succinct as possible
        - Provide only the most essential information
        - Only elaborate if absolutely necessary for understanding
        - Avoid unnecessary details or overly verbose explanations
        - Use simple, direct language

        Query: "{query}"

        Available Context:
        {search_context}

        Respond with a precise and direct answer.
        """

        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[
                {"role": "system", "content": "You are a concise and direct information assistant. Provide clear, brief answers."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,  # Lowered temperature for more focused responses
            max_tokens=350    # Reduced max tokens to encourage brevity
        )

        raw_response = response.choices[0].message.content.strip()
        
        # Simplify formatting for shorter responses
        if len(raw_response.split()) > 20:
            # Minimal markdown formatting for longer responses
            formatted_response = raw_response.replace('. ', '.\n\n')
            return formatted_response
        
        return raw_response
    
    except Exception as e:
        return f"Error generating response: {e}"
    
    except Exception as e:
        return f"Error generating response: {e}"

def format_markdown_response(response):
    """
    Enhance the response with markdown formatting.
    
    Strategies:
    1. If response contains multiple points, convert to bulleted list
    2. Add headers if multiple conceptual sections are detected
    3. Use emphasis (bold/italic) for key points
    """
    # Check for multiple sentences or paragraphs
    sentences = response.split('.')
    
    # If more than 3 sentences, attempt to structure
    if len(sentences) > 3:
        # Basic markdown structuring
        structured_response = "## Overview\n\n"
        structured_response += sentences[0] + ".\n\n"
        
        structured_response += "### Key Points\n\n"
        for sentence in sentences[1:4]:
            if sentence.strip():
                structured_response += f"- {sentence.strip()}.\n"
        
        # If more sentences exist, add a details section
        if len(sentences) > 4:
            structured_response += "\n### Additional Details\n\n"
            for sentence in sentences[4:]:
                if sentence.strip():
                    structured_response += f"- *{sentence.strip()}*\n"
        
        return structured_response
    
    return response

def process_query(message, history):
    """Process a query by searching, extracting context, and generating a response."""
    # Check if web search is necessary
    if not should_perform_web_search(message):
        # For casual conversations or greetings, use a simple response
        responses = [
            "Hello! How can I help you today?",
            "Hi there! What would you like to know?",
            "Hey! I'm ready to assist you.",
            "Greetings! Feel free to ask me anything.",
            "Hi! I'm here to help. What can I do for you?"
        ]
        return responses[hash(message) % len(responses)]

    # Perform web search
    search_results = search_duckduckgo(message)
    
    if not search_results:
        return "I couldn't find any relevant information. Could you rephrase your query?"

    # Collect context from search results
    search_context = ""
    for result in search_results:
        text = extract_text_from_url(result['link'])
        search_context += f"Source: {result['title']}\n{text}\n\n"

    # Generate response using context
    return generate_context_aware_response(message, search_context)

def create_gradio_interface():
    """Create a Gradio chat interface for the Web Search Assistant."""
    interface = gr.ChatInterface(
        fn=process_query,
        title="Web-Assisted Query Answering System",
        description="Ask a detailed question and get a context-aware response from web searches!",
        theme="soft",
        type="messages" 
    )
    return interface

def main():
    """Launch the Gradio interface"""
    interface = create_gradio_interface()
    interface.launch()

if __name__ == "__main__":
    main()