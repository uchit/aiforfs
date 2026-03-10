"""Workflow integration utilities for the SAR processing system."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional

from src.compliance_officer_agent import ComplianceOfficerAgent
from src.foundation_sar import CaseData, ExplainabilityLogger, RiskAnalystOutput
from src.risk_analyst_agent import RiskAnalystAgent


@dataclass
class HumanReviewDecision:
    """Represents the required human gate between the two agents."""

    reviewer: str
    approved: bool
    notes: str
    reviewed_at: str


@dataclass
class WorkflowMetrics:
    """Simple execution metrics for the two-stage workflow."""

    total_cases_processed: int = 0
    approved_cases: int = 0
    rejected_cases: int = 0
    total_processing_time_ms: float = 0.0

    @property
    def average_processing_time_ms(self) -> float:
        if self.total_cases_processed == 0:
            return 0.0
        return self.total_processing_time_ms / self.total_cases_processed

    @property
    def automation_rate(self) -> float:
        if self.total_cases_processed == 0:
            return 0.0
        return self.approved_cases / self.total_cases_processed


class SARWorkflowManager:
    """Coordinates risk analysis, human review, and SAR narrative generation."""

    def __init__(
        self,
        risk_agent: RiskAnalystAgent,
        compliance_agent: ComplianceOfficerAgent,
        logger: ExplainabilityLogger,
        output_dir: str = "outputs",
    ) -> None:
        self.risk_agent = risk_agent
        self.compliance_agent = compliance_agent
        self.logger = logger
        self.output_dir = Path(output_dir)
        self.filed_sars_dir = self.output_dir / "filed_sars"
        self.audit_logs_dir = self.output_dir / "audit_logs"
        self.filed_sars_dir.mkdir(parents=True, exist_ok=True)
        self.audit_logs_dir.mkdir(parents=True, exist_ok=True)
        self.metrics = WorkflowMetrics()

    def process_case(
        self,
        case_data: CaseData,
        reviewer: str,
        reviewer_notes: str,
        approved: Optional[bool] = None,
    ) -> Dict[str, object]:
        """Run the full workflow and persist outputs for approved cases."""
        start_time = datetime.now()
        risk_analysis = self.risk_agent.analyze_case(case_data)
        review_decision = self._human_review_gate(
            case_data=case_data,
            risk_analysis=risk_analysis,
            reviewer=reviewer,
            reviewer_notes=reviewer_notes,
            approved=approved,
        )

        result: Dict[str, object] = {
            "case_id": case_data.case_id,
            "risk_analysis": risk_analysis,
            "human_review": review_decision,
        }

        if review_decision.approved:
            compliance_output = self.compliance_agent.generate_compliance_narrative(
                case_data, risk_analysis
            )
            sar_document = self._build_sar_document(
                case_data=case_data,
                risk_analysis=risk_analysis,
                review_decision=review_decision,
                compliance_output=compliance_output,
            )
            sar_path = self._write_sar_document(case_data.case_id, sar_document)
            result["compliance_output"] = compliance_output
            result["sar_document_path"] = str(sar_path)
            self.metrics.approved_cases += 1
        else:
            self.metrics.rejected_cases += 1

        elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000
        self.metrics.total_cases_processed += 1
        self.metrics.total_processing_time_ms += elapsed_ms

        self.logger.log_agent_action(
            agent_type="WorkflowManager",
            action="process_case",
            case_id=case_data.case_id,
            input_data={
                "reviewer": reviewer,
                "approved": review_decision.approved,
                "classification": risk_analysis.classification,
            },
            output_data={
                "metrics": asdict(self.metrics),
                "sar_generated": "sar_document_path" in result,
            },
            reasoning="Coordinated risk analysis, human review, and SAR generation",
            execution_time_ms=elapsed_ms,
            success=True,
        )
        self._write_metrics_snapshot()
        return result

    def _human_review_gate(
        self,
        case_data: CaseData,
        risk_analysis: RiskAnalystOutput,
        reviewer: str,
        reviewer_notes: str,
        approved: Optional[bool] = None,
    ) -> HumanReviewDecision:
        """Implements the mandatory human-in-the-loop approval step."""
        if approved is None:
            approved = risk_analysis.risk_level in {"High", "Critical"} or (
                risk_analysis.confidence_score >= 0.75
            )

        decision = HumanReviewDecision(
            reviewer=reviewer,
            approved=approved,
            notes=reviewer_notes,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )
        self.logger.log_agent_action(
            agent_type="HumanReview",
            action="approve_case" if decision.approved else "reject_case",
            case_id=case_data.case_id,
            input_data={
                "classification": risk_analysis.classification,
                "confidence_score": risk_analysis.confidence_score,
                "risk_level": risk_analysis.risk_level,
            },
            output_data=asdict(decision),
            reasoning=reviewer_notes,
            execution_time_ms=0.0,
            success=True,
        )
        return decision

    def _build_sar_document(
        self,
        case_data: CaseData,
        risk_analysis: RiskAnalystOutput,
        review_decision: HumanReviewDecision,
        compliance_output,
    ) -> Dict[str, object]:
        return {
            "case_id": case_data.case_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "customer": case_data.customer.model_dump(),
            "accounts": [account.model_dump() for account in case_data.accounts],
            "transactions": [transaction.model_dump() for transaction in case_data.transactions],
            "risk_analysis": risk_analysis.model_dump(),
            "human_review": asdict(review_decision),
            "compliance_output": compliance_output.model_dump(),
            "data_sources": case_data.data_sources,
        }

    def _write_sar_document(self, case_id: str, sar_document: Dict[str, object]) -> Path:
        target_path = self.filed_sars_dir / f"{case_id}.json"
        target_path.write_text(json.dumps(sar_document, indent=2), encoding="utf-8")
        return target_path

    def _write_metrics_snapshot(self) -> None:
        metrics_path = self.audit_logs_dir / "workflow_metrics.json"
        metrics_path.write_text(
            json.dumps(
                {
                    **asdict(self.metrics),
                    "average_processing_time_ms": self.metrics.average_processing_time_ms,
                    "automation_rate": self.metrics.automation_rate,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

