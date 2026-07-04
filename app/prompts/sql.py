SQL_SYSTEM_PROMPT = "You are a SQL expert. Return ONLY the SQL query, no explanation."

SQL_QUERY_TEMPLATE = """Given the following database schema, convert this natural language question into a SQL query.
Only return the SQL query, nothing else.

Schema:
{table_info}

Question: {question}

SQL Query:"""
