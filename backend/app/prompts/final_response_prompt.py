FINAL_RESPONSE_PROMPT = """\
Write a concise, professional response (4-8 sentences) to the user summarizing the environmental \
assessment, key drivers, and top recommendation, in plain language a farmer or land manager would \
understand. Do not add any claim not present in the structured data below.

Structured data:
{structured_data}

Respond with ONLY the response text, no headers, no commentary.
"""
