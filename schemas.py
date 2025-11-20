"""
Database Schemas for Personal Finance Dashboard

Each Pydantic model represents a collection in your MongoDB database.
Collection name = lowercase of the class name.
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime

Currency = float  # simple alias for readability

class Account(BaseModel):
    name: str = Field(..., description="Account name, e.g., Checking, Savings, Cash, Credit Card")
    type: Literal["checking", "savings", "cash", "credit", "investment"] = Field(
        ..., description="Account type"
    )
    starting_balance: Currency = Field(0.0, description="Starting balance for the account")
    icon: Optional[str] = Field(None, description="Optional icon name for UI")

class Transaction(BaseModel):
    amount: Currency = Field(..., gt=0, description="Positive amount for the transaction")
    description: Optional[str] = Field(None, description="Short description or memo")
    category: str = Field(..., description="Category label, e.g., Salary, Food, Rent")
    kind: Literal["income", "expense", "savings", "debt"] = Field(
        ..., description="Type of movement"
    )
    account_id: Optional[str] = Field(None, description="Associated account id (string)")
    date: datetime = Field(..., description="Date and time of the transaction")
    recurring: Optional[bool] = Field(False, description="Whether this is generated from a recurring rule")

class Goal(BaseModel):
    name: str
    target_amount: Currency = Field(..., gt=0)
    current_amount: Currency = Field(0.0, ge=0)

class Debt(BaseModel):
    name: str
    balance: Currency = Field(..., ge=0)
    interest_rate: float = Field(0.0, ge=0, description="APR as a percentage, e.g., 19.99")
    minimum_payment: Currency = Field(0.0, ge=0)

class BudgetCategory(BaseModel):
    name: str
    monthly_budget: Currency = Field(0.0, ge=0)

class Notification(BaseModel):
    kind: Literal["bill", "budget", "goal"]
    message: str
    date: datetime = Field(default_factory=datetime.utcnow)

# The examples from the template are intentionally omitted to keep the schema focused
