# Risk Analyst Agent - Chain-of-Thought Implementation
"""Chain-of-Thought risk analysis agent for SAR workflows."""

import json
from datetime import datetime

from dotenv import load_dotenv

from src.foundation_sar import RiskAnalystOutput

load_dotenv()

class RiskAnalystAgent:
    """Risk analysis agent using a Chain-of-Thought prompt."""
    
    def __init__(self, openai_client, explainability_logger, model="gpt-4"):
        """Initialize the Risk Analyst Agent
        
        Args:
            openai_client: OpenAI client instance
            explainability_logger: Logger for audit trails
            model: OpenAI model to use
        """
        self.client = openai_client
        self.logger = explainability_logger
        self.model = model
        self.system_prompt = """
You are a Financial Crime Risk Analyst preparing a Chain-of-Thought assessment for suspicious activity review.
Use step-by-step reasoning:
1. Review the customer profile and account context.
2. Identify suspicious transaction patterns and temporal signals.
3. Map the behavior to Financial Crime typologies and regulatory concerns.
4. Assign a risk severity and confidence score.
5. Choose exactly one classification from Structuring, Sanctions, Fraud, Money_Laundering, Other.

Return valid JSON only with these fields:
- classification
- confidence_score
- reasoning
- key_indicators
- risk_level

Keep reasoning concise, professional, and suitable for audit review.
""".strip()

    def analyze_case(self, case_data) -> 'RiskAnalystOutput':
        """Analyze a case and return validated structured output."""
        start_time = datetime.now()
        case_id = getattr(case_data, "case_id", "unknown_case")
        try:
            if case_data is None:
                raise ValueError("case_data is required")
            prompt = self._format_case_for_prompt(case_data)
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0.3,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            response_content = response.choices[0].message.content
            json_content = self._extract_json_from_response(response_content)
            result = RiskAnalystOutput.model_validate(json.loads(json_content))
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="RiskAnalyst",
                action="analyze_case",
                case_id=case_id,
                input_data={"case_id": case_id, "transaction_count": len(case_data.transactions)},
                output_data=result.model_dump(),
                reasoning=result.reasoning,
                execution_time_ms=execution_time_ms,
                success=True,
            )
            return result
        except Exception as exc:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            reason = f"JSON parsing failed: {exc}" if isinstance(exc, (json.JSONDecodeError, ValueError)) else f"Analysis failed: {exc}"
            if not isinstance(exc, ValueError):
                exc = ValueError(str(exc))
            self.logger.log_agent_action(
                agent_type="RiskAnalyst",
                action="analyze_case",
                case_id=case_id,
                input_data={"case_id": case_id},
                output_data={},
                reasoning=reason,
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(exc),
            )
            if "No JSON content found" in str(exc):
                raise ValueError("Failed to parse Risk Analyst JSON output") from exc
            if "classification" in str(exc) or "confidence_score" in str(exc) or "Expecting value" in str(exc) or "Extra data" in str(exc):
                raise ValueError("Failed to parse Risk Analyst JSON output") from exc
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

    def _format_case_for_prompt(self, case_data) -> str:
        """Format case data for the analysis prompt."""
        return (
            "Analyze this SAR case using Chain-of-Thought reasoning.\n\n"
            f"Customer:\n"
            f"- ID: {case_data.customer.customer_id}\n"
            f"- Name: {case_data.customer.name}\n"
            f"- Risk Rating: {case_data.customer.risk_rating}\n"
            f"- Customer Since: {case_data.customer.customer_since}\n\n"
            f"Accounts:\n{self._format_accounts(case_data.accounts)}\n\n"
            f"Transactions:\n{self._format_transactions(case_data.transactions)}\n"
        )

    def _format_accounts(self, accounts) -> str:
        if not accounts:
            return "- No linked accounts provided"
        lines = []
        for account in accounts:
            lines.append(
                f"- {account.account_id}: {account.account_type}, "
                f"status={account.status}, current=${account.current_balance:,.2f}, "
                f"average=${account.average_monthly_balance:,.2f}"
            )
        return "\n".join(lines)

    def _format_transactions(self, transactions) -> str:
        lines = []
        for index, transaction in enumerate(transactions, start=1):
            details = (
                f"{index}. {transaction.transaction_date}: {transaction.transaction_type} "
                f"${transaction.amount:,.2f} - {transaction.description}"
            )
            if transaction.location:
                details += f" at {transaction.location}"
            if transaction.counterparty:
                details += f" with {transaction.counterparty}"
            details += f" via {transaction.method}"
            lines.append(details)
        return "\n".join(lines)

def create_chain_of_thought_framework():
    """Return the reasoning framework used by the risk agent."""
    return {
        "step_1": "Data Review - Examine all available information",
        "step_2": "Pattern Recognition - Identify suspicious indicators", 
        "step_3": "Regulatory Mapping - Connect to known typologies",
        "step_4": "Risk Quantification - Assess severity level",
        "step_5": "Classification Decision - Determine final category"
    }

def get_classification_categories():
    """Return supported SAR classification categories."""
    return {
        "Structuring": "Transactions designed to avoid reporting thresholds",
        "Sanctions": "Potential sanctions violations or prohibited parties",
        "Fraud": "Fraudulent transactions or identity-related crimes",
        "Money_Laundering": "Complex schemes to obscure illicit fund sources", 
        "Other": "Suspicious patterns not fitting standard categories"
    }

if __name__ == "__main__":
    print("Risk Analyst Agent Module")
