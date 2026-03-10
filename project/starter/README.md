# SAR Processing System

This project implements an AI-assisted Suspicious Activity Report workflow for financial crime review. The delivered system includes:

- validated customer, account, transaction, case, and agent-output schemas
- audit logging and case assembly utilities
- a Chain-of-Thought risk analyst agent
- a ReACT-based compliance officer agent
- a workflow manager with a human approval gate, SAR file generation, and metrics output

The current starter implementation passes the provided automated test suite.

## Setup

```bash
cd project/starter
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.template .env
```

Set `OPENAI_API_KEY` in `.env`. In Vocareum, this should typically start with `voc-`.

## Structure

```text
starter/
├── .env.template
├── README.md
├── data/
├── docs/
├── notebooks/
├── outputs/
│   ├── audit_logs/
│   └── filed_sars/
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── foundation_sar.py
│   ├── risk_analyst_agent.py
│   ├── compliance_officer_agent.py
│   ├── workflow_integration.py
│   └── test_scenarios.py
└── tests/
```

## Implemented Criteria

### Foundation
- `CustomerData`, `AccountData`, `TransactionData`, `CaseData`
- `RiskAnalystOutput`, `ComplianceOfficerOutput`
- `ExplainabilityLogger`
- `DataLoader`

### Agent Layer
- `RiskAnalystAgent` supports `Structuring`, `Sanctions`, `Fraud`, `Money_Laundering`, and `Other`
- `ComplianceOfficerAgent` enforces structured JSON, citations, and the 120-word narrative cap

### Workflow Integration
- `SARWorkflowManager` performs:
  - risk analysis
  - human review
  - compliance narrative generation
  - SAR JSON persistence
  - workflow metrics persistence

## Documentation

- [system_architecture.md](/Users/u.vyas/Downloads/cd14685-fin-serv-agentic-c1-classroom/project/starter/docs/system_architecture.md)
- [prompting_guide.md](/Users/u.vyas/Downloads/cd14685-fin-serv-agentic-c1-classroom/project/starter/docs/prompting_guide.md)
- [regulatory_context.md](/Users/u.vyas/Downloads/cd14685-fin-serv-agentic-c1-classroom/project/starter/docs/regulatory_context.md)
- [troubleshooting.md](/Users/u.vyas/Downloads/cd14685-fin-serv-agentic-c1-classroom/project/starter/docs/troubleshooting.md)
- [RUBRIC_ALIGNMENT.md](/Users/u.vyas/Downloads/cd14685-fin-serv-agentic-c1-classroom/project/RUBRIC_ALIGNMENT.md)
- [GRADING_RUBRIC.md](/Users/u.vyas/Downloads/cd14685-fin-serv-agentic-c1-classroom/project/GRADING_RUBRIC.md)

## Tests

```bash
.venv/bin/python -m pytest tests -q
```

Expected result for the provided starter suite:

```text
32 passed
```

Phase-specific:

```bash
.venv/bin/python -m pytest tests/test_foundation.py -q
.venv/bin/python -m pytest tests/test_risk_analyst.py -q
.venv/bin/python -m pytest tests/test_compliance_officer.py -q
.venv/bin/python -m pytest tests/test_workflow_integration.py -q
```

## Workflow Example

```python
from src import create_vocareum_openai_client
from src.foundation_sar import DataLoader, ExplainabilityLogger
from src.risk_analyst_agent import RiskAnalystAgent
from src.compliance_officer_agent import ComplianceOfficerAgent
from src.workflow_integration import SARWorkflowManager

client = create_vocareum_openai_client()
logger = ExplainabilityLogger("outputs/audit_logs/sar_audit.jsonl")
loader = DataLoader(logger)

# Build a CaseData instance from your customer/account/transaction records.
risk_agent = RiskAnalystAgent(client, logger)
compliance_agent = ComplianceOfficerAgent(client, logger)
workflow = SARWorkflowManager(risk_agent, compliance_agent, logger)
```

Approved workflow runs write SAR payloads to `outputs/filed_sars/` and metrics to `outputs/audit_logs/`.
