# System Architecture

The SAR system is organized as a two-stage workflow:

1. `DataLoader` assembles a `CaseData` object from customer, account, and transaction records.
2. `RiskAnalystAgent` applies Chain-of-Thought reasoning and produces `RiskAnalystOutput`.
3. A mandatory human review gate approves or rejects escalation to SAR drafting.
4. `ComplianceOfficerAgent` applies a ReACT-style prompt to generate a concise SAR narrative.
5. `SARWorkflowManager` persists the final SAR JSON, audit logs, and workflow metrics.

Key audit artifacts:
- `outputs/filed_sars/*.json`: finalized SAR payloads
- `outputs/audit_logs/workflow_metrics.json`: aggregate workflow metrics
- JSONL log output from `ExplainabilityLogger`: agent and review actions

Core schemas:
- `CustomerData`, `AccountData`, `TransactionData`
- `CaseData`
- `RiskAnalystOutput`
- `ComplianceOfficerOutput`

