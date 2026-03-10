# Prompting Guide

## Risk Analyst Agent

The risk analyst prompt uses a Chain-of-Thought structure:
- Review the profile and accounts
- Identify suspicious transaction patterns
- Map behavior to financial crime typologies
- Assign risk severity and confidence
- Select one classification from the approved taxonomy

## Compliance Officer Agent

The compliance prompt uses a ReACT structure:
- Reason over the analyst findings and regulatory requirements
- Act by drafting a concise SAR narrative with dates, amounts, and suspicious rationale
- Return structured JSON with citations and completeness confirmation

