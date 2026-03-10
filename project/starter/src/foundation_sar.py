# Foundation SAR - Core Data Schemas and Utilities
"""Core schemas and utilities for SAR case assembly and audit logging."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

import pandas as pd
from pydantic import BaseModel, Field, field_validator, model_validator

class CustomerData(BaseModel):
    """Customer profile schema."""
    customer_id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., description="Customer full legal name")
    date_of_birth: str = Field(..., description="Customer birth date in YYYY-MM-DD format")
    ssn_last_4: str = Field(..., description="Last four digits of SSN")
    address: str = Field(..., description="Customer mailing address")
    phone: Optional[str] = Field(None, description="Customer contact phone number")
    customer_since: str = Field(..., description="Relationship start date in YYYY-MM-DD format")
    risk_rating: Literal["Low", "Medium", "High"] = Field(..., description="Customer risk rating")
    occupation: Optional[str] = Field(None, description="Customer occupation")
    annual_income: Optional[int] = Field(None, description="Customer annual income in USD")

    @field_validator("customer_id")
    @classmethod
    def validate_customer_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("customer_id cannot be empty")
        return value

    @field_validator("date_of_birth", "customer_since")
    @classmethod
    def validate_date_fields(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("ssn_last_4")
    @classmethod
    def validate_ssn_last_4(cls, value: str) -> str:
        if len(value) != 4 or not value.isdigit():
            raise ValueError("ssn_last_4 must be exactly 4 digits")
        return value

    @field_validator("annual_income")
    @classmethod
    def validate_annual_income(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("annual_income cannot be negative")
        return value

class AccountData(BaseModel):
    """Account schema."""
    account_id: str = Field(..., description="Unique account identifier")
    customer_id: str = Field(..., description="Owning customer identifier")
    account_type: str = Field(..., description="Account product type")
    opening_date: str = Field(..., description="Account opening date in YYYY-MM-DD format")
    current_balance: float = Field(..., description="Current ledger balance")
    average_monthly_balance: float = Field(..., description="Average monthly balance")
    status: str = Field(..., description="Current account status")

    @field_validator("account_id")
    @classmethod
    def validate_account_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("account_id cannot be empty")
        return value

    @field_validator("opening_date")
    @classmethod
    def validate_opening_date(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in {"Active", "Closed", "Suspended"}:
            raise ValueError("status must be Active, Closed, or Suspended")
        return value

class TransactionData(BaseModel):
    """Transaction schema."""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    account_id: str = Field(..., description="Linked account identifier")
    transaction_date: str = Field(..., description="Transaction date in YYYY-MM-DD format")
    transaction_type: str = Field(..., description="Transaction category")
    amount: float = Field(..., description="Signed transaction amount")
    description: str = Field(..., description="Transaction description")
    method: str = Field(..., description="Execution method")
    counterparty: Optional[str] = Field(None, description="Transaction counterparty")
    location: Optional[str] = Field(None, description="Transaction location")

    @field_validator("transaction_id")
    @classmethod
    def validate_transaction_id(cls, value: str) -> str:
        if not value.startswith("TXN_"):
            raise ValueError("transaction_id must start with 'TXN_'")
        return value

    @field_validator("transaction_date")
    @classmethod
    def validate_transaction_date(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: float) -> float:
        if value == 0:
            raise ValueError("amount cannot be zero")
        return value

class CaseData(BaseModel):
    """Unified SAR case assembled from customer, account, and transaction data."""
    case_id: str = Field(..., description="Unique SAR case identifier")
    customer: CustomerData = Field(..., description="Customer profile for the case")
    accounts: List[AccountData] = Field(default_factory=list, description="Customer accounts")
    transactions: List[TransactionData] = Field(..., description="Transactions under review")
    case_created_at: str = Field(..., description="ISO timestamp when case was created")
    data_sources: Dict[str, str] = Field(..., description="Source systems used to assemble the case")

    @field_validator("transactions")
    @classmethod
    def validate_transactions_not_empty(cls, value: List[TransactionData]) -> List[TransactionData]:
        if not value:
            raise ValueError("transactions list cannot be empty")
        return value

    @field_validator("case_created_at")
    @classmethod
    def validate_case_created_at(cls, value: str) -> str:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value

    @model_validator(mode="after")
    def validate_case_relationships(self) -> "CaseData":
        for account in self.accounts:
            if account.customer_id != self.customer.customer_id:
                raise ValueError("All accounts must belong to the case customer")
        account_ids = {account.account_id for account in self.accounts}
        if self.accounts:
            for transaction in self.transactions:
                if transaction.account_id not in account_ids:
                    raise ValueError("All transactions must belong to accounts in the case")
        return self

class RiskAnalystOutput(BaseModel):
    """Structured output from the risk analysis agent."""
    classification: Literal["Structuring", "Sanctions", "Fraud", "Money_Laundering", "Other"] = Field(...)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., max_length=500)
    key_indicators: List[str] = Field(..., min_length=1)
    risk_level: Literal["Low", "Medium", "High", "Critical"] = Field(...)

class ComplianceOfficerOutput(BaseModel):
    """Structured output from the compliance narrative agent."""
    narrative: str = Field(..., max_length=1000)
    narrative_reasoning: str = Field(..., max_length=500)
    regulatory_citations: List[str] = Field(..., min_length=1)
    completeness_check: bool = Field(...)

class ExplainabilityLogger:
    """Simple JSONL audit logger."""
    
    def __init__(self, log_file: str = "sar_audit.jsonl"):
        self.log_file = log_file
        self.entries: List[Dict[str, Any]] = []
    
    def log_agent_action(self, agent_type: str, action: str, case_id: str, 
                        input_data: Dict, output_data: Dict, reasoning: str, 
                        execution_time_ms: float, success: bool = True, 
                        error_message: Optional[str] = None):
        """Log an agent action with essential execution context."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "case_id": case_id,
            "agent_type": agent_type,
            "action": action,
            "input_summary": str(input_data),
            "output_summary": str(output_data),
            "reasoning": reasoning,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "error_message": error_message,
        }
        self.entries.append(entry)
        with open(self.log_file, "a", encoding="utf-8") as log_handle:
            log_handle.write(json.dumps(entry) + "\n")

class DataLoader:
    """Create unified case objects from CSV-like records."""
    
    def __init__(self, explainability_logger: ExplainabilityLogger):
        self.logger = explainability_logger
    
    def create_case_from_data(self, 
                            customer_data: Dict,
                            account_data: List[Dict],
                            transaction_data: List[Dict]) -> CaseData:
        """Create a unified case object from fragmented AML data."""
        start_time = datetime.now()
        case_id = str(uuid.uuid4())
        try:
            customer = CustomerData(**customer_data)
            accounts = [
                AccountData(**account)
                for account in account_data
                if account.get("customer_id") == customer.customer_id
            ]
            account_ids = {account.account_id for account in accounts}
            transactions = [
                TransactionData(**transaction)
                for transaction in transaction_data
                if transaction.get("account_id") in account_ids
            ]
            source_tag = f"csv_extract_{datetime.now().strftime('%Y%m%d')}"
            case = CaseData(
                case_id=case_id,
                customer=customer,
                accounts=accounts,
                transactions=transactions,
                case_created_at=datetime.now(timezone.utc).isoformat(),
                data_sources={
                    "customer_source": source_tag,
                    "account_source": source_tag,
                    "transaction_source": source_tag,
                },
            )
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={
                    "customer_id": customer_data.get("customer_id"),
                    "account_records": len(account_data),
                    "transaction_records": len(transaction_data),
                },
                output_data={
                    "customer_id": case.customer.customer_id,
                    "accounts": len(case.accounts),
                    "transactions": len(case.transactions),
                },
                reasoning="Created unified case from customer, account, and transaction extracts",
                execution_time_ms=execution_time_ms,
                success=True,
            )
            return case
        except Exception as exc:
            execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.log_agent_action(
                agent_type="DataLoader",
                action="create_case",
                case_id=case_id,
                input_data={
                    "customer_id": customer_data.get("customer_id"),
                    "account_records": len(account_data),
                    "transaction_records": len(transaction_data),
                },
                output_data={},
                reasoning=f"Case creation failed: {exc}",
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=str(exc),
            )
            raise

# ===== HELPER FUNCTIONS (PROVIDED) =====

def load_csv_data(data_dir: str = "data/") -> tuple:
    """Helper function to load all CSV files
    
    Returns:
        tuple: (customers_df, accounts_df, transactions_df)
    """
    try:
        customers_df = pd.read_csv(f"{data_dir}/customers.csv")
        accounts_df = pd.read_csv(f"{data_dir}/accounts.csv") 
        transactions_df = pd.read_csv(f"{data_dir}/transactions.csv")
        return customers_df, accounts_df, transactions_df
    except FileNotFoundError as e:
        raise FileNotFoundError(f"CSV file not found: {e}")
    except Exception as e:
        raise Exception(f"Error loading CSV data: {e}")

if __name__ == "__main__":
    print("Foundation SAR Module")
