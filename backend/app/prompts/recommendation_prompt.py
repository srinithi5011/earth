RECOMMENDATION_PROMPT = """\
Using ONLY the evidence below, write ONE specific, actionable recommendation implementing the \
intervention category "{intervention_category}" for this environmental state. Do not invent \
statistics not present in the evidence text. Be concrete (e.g. name a specific crop/species \
pairing or practice), not generic.

Environmental state:
{state}

Evidence:
{evidence}

Respond with ONLY the recommendation text (2-3 sentences), no headers, no commentary.
"""
