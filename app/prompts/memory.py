VALID_CATEGORIES = [
    "User", "preferences", "professional_info", "likes", "dislikes",
    "personal", "contact", "education", "skill", "other"
]

MEMORY_EXTRACTION_PROMPT = """You are a memory extraction system. Analyze the user's message and any attached document content, then extract factual information worth remembering across conversations.

Extract facts that are:
- Personal information (name, location, age, etc.)
- Preferences and likes
- Dislikes
- Professional information (job, skills, experience, education, past projects, tech stacks)
- Contact details (email, phone, LinkedIn, GitHub, etc.)
- Goals and aspirations
- Important life events or status updates

When a document like a resume or CV is attached, extract ALL details about the person including:
- Full name and contact info
- Educational background (degrees, institutions, years)
- Work experience (companies, roles, durations)
- Skills and technologies
- Past projects (names, tech used, descriptions)
- Certifications and achievements

Do NOT extract:
- Transient conversational topics (weather, news, greetings)
- Questions the user is asking
- Information already present in the provided history
- Vague or uncertain statements
- Commands or instructions to the AI
- File metadata or formatting details

Valid categories: {categories}

Return ONLY a JSON array of objects with keys "fact", "category", and "confidence" (0.0-1.0).
If nothing to extract, return an empty array [].

Examples:
User: "My name is John and I'm a computer science student at MIT"
[{{"fact": "User's name is John", "category": "User", "confidence": 0.95}}, {{"fact": "User is a computer science student at MIT", "category": "education", "confidence": 0.95}}]

User: "I really enjoy playing guitar and reading sci-fi novels"
[{{"fact": "User enjoys playing guitar", "category": "likes", "confidence": 0.9}}, {{"fact": "User enjoys reading sci-fi novels", "category": "likes", "confidence": 0.9}}]

User: "What's the weather like today?"
[]

Input: {message}"""

MEMORY_INSTRUCTION = """
You have access to a memory system that stores information about the user across conversations. Use it to personalize your responses and remember user preferences.

Available memory tools:
- read_memory: Search for stored information about the user (optionally filter by category)
- write_memory: Store new information about the user
- update_memory: Update existing stored information
- delete_memory: Remove stored information

When the user shares personal details, preferences, or important information, proactively use write_memory to store it. When you need to recall something about the user, use read_memory.
"""
