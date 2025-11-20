import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import Transaction, Account, Goal, Debt, BudgetCategory, Notification

app = FastAPI(title="Personal Finance API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Utilities ----------
COLL_TRANSACTION = "transaction"
COLL_ACCOUNT = "account"
COLL_GOAL = "goal"
COLL_DEBT = "debt"
COLL_BUDGET = "budgetcategory"
COLL_NOTIFICATION = "notification"


def start_of_period(now: datetime, timeframe: str) -> datetime:
    if timeframe == "daily":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if timeframe == "weekly":
        # ISO week starts Monday
        start = now - timedelta(days=(now.weekday()))
        return start.replace(hour=0, minute=0, second=0, microsecond=0)
    if timeframe == "monthly":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if timeframe == "yearly":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now


def ensure_seed_data():
    """Seed minimal demo data if empty collections to make the dashboard feel alive."""
    if db is None:
        return

    if db[COLL_ACCOUNT].count_documents({}) == 0:
        create_document(COLL_ACCOUNT, {
            "name": "Checking",
            "type": "checking",
            "starting_balance": 2500.0,
            "icon": "Wallet"
        })
        create_document(COLL_ACCOUNT, {
            "name": "Savings",
            "type": "savings",
            "starting_balance": 8000.0,
            "icon": "PiggyBank"
        })
        create_document(COLL_ACCOUNT, {
            "name": "Credit Card",
            "type": "credit",
            "starting_balance": -1200.0,
            "icon": "CreditCard"
        })

    if db[COLL_GOAL].count_documents({}) == 0:
        create_document(COLL_GOAL, {"name": "Emergency Fund", "target_amount": 10000, "current_amount": 4000})
        create_document(COLL_GOAL, {"name": "Vacation", "target_amount": 3000, "current_amount": 1200})
        create_document(COLL_GOAL, {"name": "New Car", "target_amount": 20000, "current_amount": 3500})

    if db[COLL_DEBT].count_documents({}) == 0:
        create_document(COLL_DEBT, {"name": "Credit Card", "balance": 1200, "interest_rate": 19.99, "minimum_payment": 50})
        create_document(COLL_DEBT, {"name": "Student Loan", "balance": 8500, "interest_rate": 4.2, "minimum_payment": 120})
        create_document(COLL_DEBT, {"name": "Car Loan", "balance": 5400, "interest_rate": 3.5, "minimum_payment": 180})

    # Add some example recent transactions if very empty
    if db[COLL_TRANSACTION].count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        seed = [
            {"amount": 3200, "description": "Salary", "category": "Salary", "kind": "income", "date": now - timedelta(days=10)},
            {"amount": 200, "description": "Freelance Gig", "category": "Freelance", "kind": "income", "date": now - timedelta(days=4)},
            {"amount": 65, "description": "Groceries", "category": "Food", "kind": "expense", "date": now - timedelta(days=3)},
            {"amount": 1200, "description": "Rent", "category": "Rent", "kind": "expense", "date": now - timedelta(days=15)},
            {"amount": 35, "description": "Transport Card", "category": "Transport", "kind": "expense", "date": now - timedelta(days=2)},
            {"amount": 300, "description": "Emergency Fund", "category": "Emergency Fund", "kind": "savings", "date": now - timedelta(days=1)},
            {"amount": 150, "description": "Credit Card Payment", "category": "Credit Card", "kind": "debt", "date": now - timedelta(days=6)},
        ]
        for t in seed:
            t["recurring"] = False
            create_document(COLL_TRANSACTION, t)


@app.get("/")
def read_root():
    ensure_seed_data()
    return {"message": "Personal Finance Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": "❌ Not Set",
        "database_name": "❌ Not Set",
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            response["collections"] = db.list_collection_names()
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response


# ---------- Models for API ----------
class TransactionIn(BaseModel):
    amount: float
    description: Optional[str] = None
    category: str
    kind: str  # income | expense | savings | debt
    account: Optional[str] = None
    date: Optional[datetime] = None
    recurring: Optional[bool] = False


# ---------- Endpoints ----------
@app.get("/api/accounts")
def list_accounts():
    ensure_seed_data()
    return get_documents(COLL_ACCOUNT)


@app.get("/api/goals")
def list_goals():
    ensure_seed_data()
    return get_documents(COLL_GOAL)


@app.get("/api/debts")
def list_debts():
    ensure_seed_data()
    return get_documents(COLL_DEBT)


@app.get("/api/budgets")
def list_budgets():
    ensure_seed_data()
    # If none, create some default categories with budgets
    if db[COLL_BUDGET].count_documents({}) == 0:
        for name, amt in [("Food", 400), ("Rent", 1200), ("Transport", 150), ("Shopping", 250), ("Entertainment", 150)]:
            create_document(COLL_BUDGET, {"name": name, "monthly_budget": amt})
    return get_documents(COLL_BUDGET)


@app.get("/api/transactions")
def list_transactions(timeframe: Optional[str] = Query(None, regex="^(daily|weekly|monthly|yearly)$")):
    ensure_seed_data()
    if timeframe:
        now = datetime.now(timezone.utc)
        start = start_of_period(now, timeframe)
        return get_documents(COLL_TRANSACTION, {"date": {"$gte": start}})
    return get_documents(COLL_TRANSACTION)


@app.post("/api/transactions")
def add_transaction(t: TransactionIn):
    ensure_seed_data()
    try:
        payload = {
            "amount": abs(t.amount),
            "description": t.description,
            "category": t.category,
            "kind": t.kind,
            "account_id": t.account,
            "date": t.date or datetime.now(timezone.utc),
            "recurring": bool(t.recurring),
        }
        _id = create_document(COLL_TRANSACTION, payload)
        return {"inserted_id": _id}
    except Exception as e:
        raise HTTPException(500, f"Error creating transaction: {str(e)}")


@app.get("/api/summary")
def summary(timeframe: str = Query("monthly", regex="^(daily|weekly|monthly|yearly)$")):
    ensure_seed_data()
    now = datetime.now(timezone.utc)
    start = start_of_period(now, timeframe)
    txs = get_documents(COLL_TRANSACTION, {"date": {"$gte": start}})

    income = sum(t.get("amount", 0) for t in txs if t.get("kind") == "income")
    expenses = sum(t.get("amount", 0) for t in txs if t.get("kind") == "expense")
    savings = sum(t.get("amount", 0) for t in txs if t.get("kind") == "savings")
    debt_payments = sum(t.get("amount", 0) for t in txs if t.get("kind") == "debt")
    cash_flow = income - expenses  # savings/debt reduce cash but are intentional allocations

    # Aggregate by categories for charts
    income_sources: Dict[str, float] = {}
    expense_categories: Dict[str, float] = {}
    for t in txs:
        cat = t.get("category", "Other")
        amt = float(t.get("amount", 0))
        if t.get("kind") == "income":
            income_sources[cat] = income_sources.get(cat, 0) + amt
        elif t.get("kind") == "expense":
            expense_categories[cat] = expense_categories.get(cat, 0) + amt

    # Budget usage for month only (uses current month budgets)
    budgets = list_budgets()
    budget_usage: List[Dict[str, Any]] = []
    if timeframe in ("monthly", "weekly", "daily"):
        month_start = start_of_period(now, "monthly")
        month_expenses = get_documents(COLL_TRANSACTION, {"date": {"$gte": month_start}, "kind": "expense"})
        by_cat: Dict[str, float] = {}
        for t in month_expenses:
            by_cat[t.get("category", "Other")] = by_cat.get(t.get("category", "Other"), 0.0) + float(t.get("amount", 0))
        for b in budgets:
            spent = by_cat.get(b.get("name"), 0.0)
            budget_usage.append({
                "name": b.get("name"),
                "spent": spent,
                "budget": float(b.get("monthly_budget", 0)),
            })

    # Goals and debts
    goals = list_goals()
    debts = list_debts()

    # Net worth = sum of positive accounts + savings goals - debts balances (simple approximation)
    accounts = list_accounts()
    cash_on_hand = sum(float(a.get("starting_balance", 0)) for a in accounts if a.get("type") in ("checking", "savings", "cash"))
    total_debt = sum(float(d.get("balance", 0)) for d in debts)
    total_goals = sum(float(g.get("current_amount", 0)) for g in goals)
    net_worth = cash_on_hand + total_goals - total_debt

    return {
        "timeframe": timeframe,
        "metrics": {
            "net_worth": net_worth,
            "cash_on_hand": cash_on_hand,
            "total_debt": total_debt,
            "cash_flow": cash_flow,
            "income": income,
            "expenses": expenses,
            "savings": savings,
            "debt_payments": debt_payments,
        },
        "income_sources": income_sources,
        "expense_categories": expense_categories,
        "budget_usage": budget_usage,
        "goals": goals,
        "debts": debts,
        "accounts": accounts,
    }


@app.get("/api/notifications")
def get_notifications():
    ensure_seed_data()
    # Create computed notifications (budget nearing, goal milestones)
    notifs: List[Dict[str, Any]] = []

    # Budget nearing 90%
    budgets = list_budgets()
    month_summary = summary("monthly")
    usage_by_name = {b["name"]: b for b in month_summary.get("budget_usage", [])}
    for b in budgets:
        name = b.get("name")
        info = usage_by_name.get(name)
        if not info:
            continue
        budget = float(info.get("budget", 0))
        spent = float(info.get("spent", 0))
        if budget > 0 and spent >= 0.9 * budget:
            notifs.append({
                "kind": "budget",
                "message": f"You're at {int(spent / budget * 100)}% of your {name} budget",
                "date": datetime.now(timezone.utc)
            })

    # Simple upcoming bill example if any debt minimums exist
    for d in month_summary.get("debts", []):
        if float(d.get("minimum_payment", 0)) > 0:
            notifs.append({
                "kind": "bill",
                "message": f"Upcoming bill: {d.get('name')} minimum payment ${d.get('minimum_payment'):.0f}",
                "date": datetime.now(timezone.utc)
            })

    # Goal milestones 50%, 75%, 100%
    for g in month_summary.get("goals", []):
        target = max(1.0, float(g.get("target_amount", 0)))
        current = float(g.get("current_amount", 0))
        pct = current / target
        if pct >= 1.0:
            notifs.append({"kind": "goal", "message": f"Goal reached: {g.get('name')}", "date": datetime.now(timezone.utc)})
        elif pct >= 0.75:
            notifs.append({"kind": "goal", "message": f"Great! {g.get('name')} is 75% funded", "date": datetime.now(timezone.utc)})
        elif pct >= 0.5:
            notifs.append({"kind": "goal", "message": f"Halfway there on {g.get('name')}", "date": datetime.now(timezone.utc)})

    # Also include static stored notifications if any
    stored = get_documents(COLL_NOTIFICATION)
    return stored + notifs


# Health check hello
@app.get("/api/hello")
def hello():
    return {"message": "Hello from Personal Finance API"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
