# Compliance Officer Agent - ReACT Implementation
"""ReACT-style compliance narrative agent for SAR workflows."""

import json
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv

from src.foundation_sar import ComplianceOfficerOutput

load_dotenv()

class ComplianceOfficerAgent:
    """Compliance narrative agent using a ReACT-style prompt."""
    
    def __init__(self, openai_client, explainability_logger, model="gpt-4"):
        """Initialize the Compliance Officer Agent
        
        Args:
            openai_client: OpenAI client instance
            explainability_logger: Logger for audit trails
            model: OpenAI model to use
        """
        self.client = openai_client
        self.logger = explainability_logger
        self.model = model
        self.system_prompt = """
You are a Senior Compliance Officer drafting a FinCEN SAR narrative with a ReACT framework.
REASONING PHASE:
1. Review the Risk Analyst findings.
2. Identify the suspicious activity facts, dates, amounts, and parties.
3. Map the activity to BSA/AML and SAR filing expectations.
4. Plan a concise narrative with regulatory terminology.

ACTION PHASE:
1. Draft a SAR-ready narrative of 120 words or fewer.
2. State why the activity is suspicious.
3. Include precise dates, amounts, and customer identifiers when available.
4. Return JSON only with narrative, narrative_reasoning, regulatory_citations, completeness_check.

Maintain formal Compliance Officer tone and BSA/AML focus.
""".strip()

    def generate_compliance_narrative(self, case_data, risk_analysis) -> 'ComplianceOfficerOutput':
        """Generate a validated SAR narrative from a case and risk analysis."""
        start_time = datetime.now()
        case_id = getattr(case_data, "case_id", "unknown_case")
        try:
            prompt = (
                "Generate a SAR narrative using the ReACT framework.\n\n"
                f"Case Summary:\n"
                f"- Customer: {case_data.customer.name} ({case_data.customer.customer_id})\n"
                f"- Risk Rating: {case_data.customer.risk_rating}\n"
                f"- Transactions:\n{self._format_transactions_for_compliance(case_data.transactions)}\n\n"
                f"Risk Analysis:\n{self._format_risk_analysis_for_prompt(risk_analysis)}"
            )
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.2,
                max_tokens=800,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            response_content = response.choices[0].message.content
            json_content = self._extract_json_from_response(response_content)
            result = ComplianceOfficerOutput.model_validate(json.loads(json_content))
            validation = self._validate_narrative_compliance(result.narrative)
            if not validation["is_compliant"]:
                raise ValueError(validation["error"])
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="ComplianceOfficer",
                action="generate_narrative",
                case_id=case_id,
                input_data={"case_id": case_id, "classification": risk_analysis.classification},
                output_data=result.model_dump(),
                reasoning=result.narrative_reasoning,
                execution_time_ms=execution_time_ms,
                success=True,
            )
            return result
        except Exception as exc:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            reason = f"JSON parsing failed: {exc}" if isinstance(exc, (json.JSONDecodeError, ValueError)) else f"Narrative generation failed: {exc}"
            self.logger.log_agent_action(
                agent_type="ComplianceOfficer",
                action="generate_narrative",
                case_id=case_id,
                input_data={"case_id": case_id},
                output_data={},
                reasoning=reason,
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(exc),
            )
            if "No JSON content found" in str(exc) or "Expecting value" in str(exc) or "Extra data" in str(exc):
                raise ValueError("Failed to parse Compliance Officer JSON output") from exc
            raise

    def _extract_json_from_response(self, response_content: str) -> str:
        """Extract a JSON object from plain text or fenced code blocks."""
        if not response_content or not response_content.strip():
            raise ValueError("No JSON content found")
        content = response_content.strip()
        if "```json" in content:
            start = content.index("```json") + len("```json")
            end = content.index("```", start)
            return content[start:end].strip()
        if "```" in content:
            start = content.index("```") + len("```")
            end = content.index("```", start)
            return content[start:end].strip()
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON content found")
        return content[start:end + 1]

    def _format_risk_analysis_for_prompt(self, risk_analysis) -> str:
        """Format risk analysis results for the compliance prompt."""
        return (
            f"- Classification: {risk_analysis.classification}\n"
            f"- Confidence: {risk_analysis.confidence_score:.2f}\n"
            f"- Risk Level: {risk_analysis.risk_level}\n"
            f"- Indicators: {', '.join(risk_analysis.key_indicators)}\n"
            f"- Analyst Reasoning: {risk_analysis.reasoning}"
        )

    def _validate_narrative_compliance(self, narrative: str) -> Dict[str, Any]:
        """Validate that the narrative meets the word-count requirement."""
        word_count = len(narrative.split())
        if word_count > 120:
            return {"is_compliant": False, "error": "Narrative exceeds 120 word limit"}
        if not narrative.strip():
            return {"is_compliant": False, "error": "Narrative cannot be empty"}
        return {"is_compliant": True, "word_count": word_count}

    def _format_transactions_for_compliance(self, transactions) -> str:
        lines = []
        for index, transaction in enumerate(transactions, start=1):
            line = (
                f"{index}. {transaction.transaction_date}: ${transaction.amount:,.2f} "
                f"{transaction.transaction_type} - {transaction.description}"
            )
            if transaction.location:
                line += f" at {transaction.location}"
            line += f" via {transaction.method}"
            lines.append(line)
        return "\n".join(lines)

def create_react_framework():
    """Return the reasoning and action framework used by the compliance agent."""
    return {
        "reasoning_phase": [
            "Review risk analysis findings",
            "Assess regulatory requirements", 
            "Identify compliance elements",
            "Plan narrative structure"
        ],
        "action_phase": [
            "Draft concise narrative",
            "Include specific details",
            "Reference activity patterns",
            "Use regulatory language"
        ]
    }

def get_regulatory_requirements():
    """Return core regulatory constraints for SAR narratives."""
    return {
        "word_limit": 120,
        "required_elements": [
            "Customer identification",
            "Suspicious activity description", 
            "Transaction amounts and dates",
            "Why activity is suspicious"
        ],
        "terminology": [
            "Suspicious activity",
            "Regulatory threshold",
            "Financial institution",
            "Money laundering",
            "Bank Secrecy Act"
        ],
        "citations": [
            "31 CFR 1020.320 (BSA)",
            "12 CFR 21.11 (SAR Filing)",
            "FinCEN SAR Instructions"
        ]
    }

def validate_word_count(text: str, max_words: int = 120) -> bool:
    """Return whether the text is within the configured word limit."""
    return len(text.split()) <= max_words

if __name__ == "__main__":
    print("Compliance Officer Agent Module")
