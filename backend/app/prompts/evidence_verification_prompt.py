EVIDENCE_VERIFICATION_PROMPT = """\
Verify whether the recommendation below is fully supported by the evidence provided. Check:
A. Is the recommendation itself supported by the evidence?
B. Are the claimed affected metrics supported?
C. Are any numeric claims present in the evidence (not invented)?
D. Does the evidence come from a credible source tier?
E. Is the evidence topically relevant to the environmental context?

Recommendation:
{recommendation}

Affected metrics claimed:
{affected_metrics}

Evidence:
{evidence}

Respond with ONLY a JSON object: {{"supported": true|false, "issues": ["..."]}}
"""
