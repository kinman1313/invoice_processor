import os
import sqlite3
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
INVOICE_MODEL = os.getenv("INVOICE_MODEL", "claude-3-opus-20240229")
DB_PATH = "invoice_app.db"

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def get_db_connection():
    """Get read-only connection to DB"""
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def get_database_schema() -> str:
    """Return schema of key tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    schema_str = ""
    tables = ["vendors", "invoices", "purchase_orders", "goods_receipts"]
    
    for table in tables:
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        schema_str += f"\nTable: {table}\n"
        for col in columns:
            schema_str += f"  - {col['name']} ({col['type']})\n"
            
    conn.close()
    return schema_str

def run_sql_query(query: str) -> str:
    """Execute a read-only SQL query"""
    # Safety Check
    if not query.lower().strip().startswith("select"):
        return "Error: Only SELECT queries are allowed for safety."
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "No results found."
            
        # Format as list of dicts
        results = [dict(row) for row in rows]
        return json.dumps(results, indent=2)
        
    except Exception as e:
        return f"SQL Error: {str(e)}"

def process_chat_query(user_query: str, history: list = None) -> str:
    """
    Main entry point for chat.
    Orchestrates the conversation with Claude to answer finance questions.
    """
    
    schema = get_database_schema()
    
    system_prompt = f"""You are an expert Financial Analyst Assistant.
You have access to a SQLite database with the following schema:
{schema}

Your goal is to answer user questions about spend, vendors, and invoices.
1. Start by thinking about which SQL query will answer the question.
2. Use the `run_sql_query` tool to execute it.
3. specific rules:
    - Always use 'LIKE' for string matching if unsure of exact case.
    - Currency is in float (e.g. 5000.0).
    - Dates are stored as YYYY-MM-DD strings.
4. Analyze the returned JSON data.
5. Provide a clear, natural language answer to the user.
6. If the result is a large list, summarize it (e.g. "Top 5 vendors are...").

If you cannot answer, explain why.
"""

    tools = [
        {
            "name": "run_sql_query",
            "description": "Run a SQLite SELECT query to fetch data.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The SQL SELECT query to run"
                    }
                },
                "required": ["query"]
            }
        }
    ]

    # Construct messages
    messages = []
    if history:
         messages.extend(history)
         
    messages.append({"role": "user", "content": user_query})
    
    # Agent Loop
    for _ in range(5): # Max turns
        response = client.messages.create(
            model=INBOX_MODEL if "INBOX_MODEL" in globals() else INVOICE_MODEL, # Fallback safe
            max_tokens=1024,
            system=system_prompt,
            messages=messages,
            tools=tools
        )
        
        # Check if we stop or need tools
        if response.stop_reason == "end_turn":
            return response.content[0].text
            
        elif response.stop_reason == "tool_use":
            # Execute tool
            tool_results = []
            
            # Append assistant's thought process so it sees it
            messages.append({"role": "assistant", "content": response.content})
            
            for block in response.content:
                if block.type == "tool_use":
                    result = run_sql_query(block.input["query"])
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })
            
            messages.append({"role": "user", "content": tool_results})
            
    return "I tried to find the answer but ran into a loop. Please try a simpler question."
