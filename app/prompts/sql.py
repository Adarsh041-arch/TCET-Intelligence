SQL_SYSTEM_PROMPT = """You are a SQL expert. Generate SQL queries based on the user's question and recent conversation history.
Consider the context from previous messages to understand follow-up questions and references.
Return ONLY the SQL query, no explanation."""

SQL_QUERY_TEMPLATE = """Given the following database schema, recent conversation history, and execution plan, convert this natural language question into a SQL query.
Only return the SQL query, nothing else. Use JOINs across tables when the plan requires it.

Schema:
{table_info}

Recent Conversation:
{chat_history}

Plan:
{plan}

Current Question: {question}

SQL Query:"""

SQL_PLANNING_PROMPT = """You are a SQL planning expert. Analyze the database schema and the user's question to produce a short, concrete plan for answering it with SQL.

Schema:
{table_info}

Recent Conversation:
{chat_history}

Current Question: {question}

Produce a plan covering:
1. Which tables are needed
2. Any JOINs required (and the join keys)
3. Any filters, grouping, aggregation, or ordering
4. Potential pitfalls (ambiguous columns, type mismatches)

Keep it under 8 lines. Do NOT write the SQL query yet. Plan only:"""

SQL_RETRY_PROMPT = """The previous SQL query failed. Reason over the error and generate a corrected query.

Schema:
{table_info}

Plan:
{plan}

Original Question: {question}

Previous SQL Query:
{previous_query}

Error / Problem:
{error}

Analyze what went wrong (wrong column/table name, bad join, syntax, type issue), fix it, and return ONLY the corrected SQL query, no explanation:"""

SQL_RESPONSE_PROMPT = """You are a helpful assistant that presents database query results in a clear, structured table format.

Given the query result below, format it as a well-structured markdown table with proper alignment and formatting.
- Include column headers
- Align numeric columns to the right
- Align text columns to the left
- If there are many rows, show the first 50 and mention how many more exist
- Add a brief summary statement before the table explaining what the data shows

Query Result:
{query_result}

Format this as a clean, professional table:"""
