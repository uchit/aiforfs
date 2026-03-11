import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

from src.compliance_officer_agent import ComplianceOfficerAgent
from src.foundation_sar import (
    AccountData,
    CaseData,
    ComplianceOfficerOutput,
    CustomerData,
    ExplainabilityLogger,
    RiskAnalystOutput,
    TransactionData,
)
from src.risk_analyst_agent import RiskAnalystAgent
from src.workflow_integration import SARWorkflowManager


def build_case() -> CaseData:
    customer = CustomerData(
        customer_id="CUST_WF",
        name="Workflow Customer",
        date_of_birth="1988-01-01",
        ssn_last_4="1234",
        address="123 Workflow Ave",
        customer_since="2020-01-01",
        risk_rating="Medium",
    )
    account = AccountData(
        account_id="ACC_WF",
        customer_id="CUST_WF",
        account_type="Checking",
        opening_date="2020-01-01",
        current_balance=12000.0,
        average_monthly_balance=10000.0,
        status="Active",
    )
    transaction = TransactionData(
        transaction_id="TXN_WF",
        account_id="ACC_WF",
        transaction_date="2025-01-01",
        transaction_type="Cash_Deposit",
        amount=9900.0,
        description="Cash deposit near threshold",
        method="Cash",
    )
    return CaseData(
        case_id="CASE_WF",
        customer=customer,
        accounts=[account],
        transactions=[transaction],
        case_created_at=datetime.now().isoformat(),
        data_sources={"test": "data"},
    )


def test_workflow_generates_sar_for_approved_case(tmp_path: Path):
    risk_agent = Mock(spec=RiskAnalystAgent)
    risk_agent.analyze_case.return_value = RiskAnalystOutput(
        classification="Structuring",
        confidence_score=0.9,
        reasoning="1) Context review: case data reviewed. 2) Pattern signals: repeated near-threshold deposits. 3) Typology mapping: aligns with structuring. 4) Severity+confidence: High risk, 0.90 confidence. 5) Classification: Structuring.",
        key_indicators=["threshold avoidance"],
        risk_level="High",
    )

    compliance_agent = Mock(spec=ComplianceOfficerAgent)
    compliance_agent.generate_compliance_narrative.return_value = ComplianceOfficerOutput(
        narrative="Customer Workflow Customer deposited $9,900 on 2025-01-01 in a pattern consistent with structuring and possible evasion of reporting thresholds.",
        narrative_reasoning="Included customer, date, amount, and suspicious rationale.",
        regulatory_citations=["31 CFR 1020.320 (BSA)"],
        completeness_check=True,
    )

    logger = ExplainabilityLogger(str(tmp_path / "audit.jsonl"))
    workflow = SARWorkflowManager(
        risk_agent=risk_agent,
        compliance_agent=compliance_agent,
        logger=logger,
        output_dir=str(tmp_path / "outputs"),
    )

    result = workflow.process_case(
        case_data=build_case(),
        reviewer="Analyst One",
        reviewer_notes="Escalate for SAR filing.",
        approved=True,
    )

    assert "sar_document_path" in result
    sar_path = Path(result["sar_document_path"])
    assert sar_path.exists()
    payload = json.loads(sar_path.read_text(encoding="utf-8"))
    assert payload["case_id"] == "CASE_WF"
    assert payload["human_review"]["approved"] is True
    assert payload["risk_analysis"]["classification"] == "Structuring"


def test_workflow_rejected_case_does_not_generate_sar(tmp_path: Path):
    risk_agent = Mock(spec=RiskAnalystAgent)
    risk_agent.analyze_case.return_value = RiskAnalystOutput(
        classification="Other",
        confidence_score=0.4,
        reasoning="1) Context review: case data reviewed. 2) Pattern signals: low-risk activity observed. 3) Typology mapping: no clear typology match. 4) Severity+confidence: Low risk, 0.40 confidence. 5) Classification: Other.",
        key_indicators=["none"],
        risk_level="Low",
    )

    compliance_agent = Mock(spec=ComplianceOfficerAgent)
    logger = ExplainabilityLogger(str(tmp_path / "audit.jsonl"))
    workflow = SARWorkflowManager(
        risk_agent=risk_agent,
        compliance_agent=compliance_agent,
        logger=logger,
        output_dir=str(tmp_path / "outputs"),
    )

    result = workflow.process_case(
        case_data=build_case(),
        reviewer="Analyst Two",
        reviewer_notes="No filing required.",
        approved=False,
    )

    assert "sar_document_path" not in result
    compliance_agent.generate_compliance_narrative.assert_not_called()
    metrics_path = tmp_path / "outputs" / "audit_logs" / "workflow_metrics.json"
    assert metrics_path.exists()
