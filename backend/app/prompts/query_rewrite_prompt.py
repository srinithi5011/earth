QUERY_REWRITE_PROMPT = """\
Rewrite the following environmental state and user message into a single, information-dense \
search query optimized for retrieving relevant scientific/technical passages from a biodiversity \
and environmental-science knowledge base. Include key metric names, land use, region, and \
qualitative levels (low/high). Do not add speculative details.

Environmental state:
{state}

User message:
\"\"\"{message}\"\"\"

Respond with ONLY the rewritten query text, one line, no commentary.
"""
