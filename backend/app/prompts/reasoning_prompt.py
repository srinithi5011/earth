REASONING_PROMPT = """\
Explain, in 2-4 sentences, why the following triggered conditions and relationship chain matter \
together. You must reference at least 3 distinct metrics from the data below. Do not introduce \
any relationship not present in the chain.

Triggered conditions:
{triggered_conditions}

Relationship chain (source -> relationship -> target, direction, strength):
{relationship_chain}

Respond with ONLY the explanation prose, no headers, no commentary.
"""
