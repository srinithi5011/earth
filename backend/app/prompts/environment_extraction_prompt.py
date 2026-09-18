ENVIRONMENT_EXTRACTION_PROMPT = """\
Extract environmental variables mentioned in the user's message into the JSON schema below. \
Only include fields that are explicitly stated or very strongly implied. Use null for anything \
not mentioned. Do not guess numeric values.

Schema:
{schema}

User message:
\"\"\"{message}\"\"\"

Respond with ONLY the JSON object, no commentary.
"""
