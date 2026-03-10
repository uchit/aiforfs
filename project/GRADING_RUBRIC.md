# Grading Rubric

This rubric is reconstructed from the project description so the submission package includes explicit assessment criteria.

## Foundation And Data Modeling

- Customer, account, transaction, and case schemas are implemented and validated.
- The data loader assembles unified case objects from CSV-like inputs.
- Audit logging records inputs, outputs, timestamps, and success or failure state.

## Risk Analyst Agent

- The implementation uses a Chain-of-Thought prompt structure.
- Output is structured JSON validated against the required schema.
- The agent classifies one of: `Structuring`, `Sanctions`, `Fraud`, `Money_Laundering`, `Other`.
- Error handling covers malformed or missing model output.

## Compliance Officer Agent

- The implementation uses a ReACT-style prompt structure.
- Narratives include regulatory citations.
- Narrative validation enforces the 120-word cap.
- Output is schema-validated and auditable.

## Workflow Integration

- The system includes a human-in-the-loop approval gate.
- Approved cases generate SAR JSON artifacts.
- Audit and metrics outputs are persisted under `outputs/`.
- Documentation explains architecture, prompting, regulatory context, and troubleshooting.

## Verification

- Unit tests for foundation, risk analyst, compliance officer, and workflow integration should pass.

