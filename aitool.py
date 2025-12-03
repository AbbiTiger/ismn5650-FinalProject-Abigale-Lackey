###Sample Prompt
"""
Create a basic chatGPT api integration function or class that I can use in a seperate file called aitool.py.  

I want to be able to set static in the file, system instructions, gpt model, temperature, and token limit.

The function should accept a set of JSON in the following format:

{
        "Positions": [
            {"ticker": "AAPL", "quantity": 10, "purchase_price": 180.0},
            {"ticker": "MSFT", "quantity": 5, "purchase_price": 410.0},
            {"ticker": "CASH", "quantity": 1000, "purchase_price": 1.00}
        ],
        "Market_Summary": [
            {"ticker": "AAPL", "current_price": 182.5, "category": "high"},
            {"ticker": "MSFT", "current_price": 405.0, "category": "low"}
        ],
        "market_history": [
            {"ticker": "AAPL", "price": 179.8, "day": 1},
            {"ticker": "AAPL", "price": 181.2, "day": 2},
            {"ticker": "MSFT", "price": 409.5, "day": 1},
            {"ticker": "MSFT", "price": 405.0, "day": 2}
        ]
    }

I want system instructions to tell the LLM that I need a decision made about whether I should sell, stay, or 
hold my current positions based on the current market summary.  Use the JSON provided to make the decision.
ONLY use this JSON and no publicly available market information as this is a simulated environment, so only
the JSON provided should make the decision.

You may also use the provided market_history to determine any trends recently available.

The ticker CASH in the positions list indicates how much available money we have to spend on new positions.

Stocks will be provided in 3 different categories, high risk, low risk, and medium risk.  Have a section in
the system instructions available for me to customize if I want the LLM recommendations to be a certain risk
strategy.  There will be 3 stocks in each category.  The category can be identified in the market_summary json.

You can only buy or sell at the current market price and you are not allowed to sell a stock unless you have the
quantity to sell in that current position.

This function should also return it's recommendation using tools.  The response should include the following
information for each position excluding cash.

response fields:
action: SELL, STAY, or BUY
ticker:
quantity:


I want the api key to be stored in a .env file and set static.
"""
###

# aitool.py
import os
import json
from typing import Any, Dict, List, Tuple, Optional

from dotenv import load_dotenv
from openai import OpenAI


class AITradingTool:
    """
    Basic ChatGPT integration for simulated portfolio decisions.
    - Static configuration (API key from .env, model, temp, token limit, system instructions)
    - Accepts a single JSON-like dict payload with keys:
        Positions, Market_Summary, market_history
    - Strictly uses ONLY the provided JSON to decide SELL/STAY/BUY per non-cash position
    - Returns (assistant_text, recommendations_list) where recommendations_list is an array of:
        { "action": "SELL|STAY|BUY", "ticker": "<symbol>", "quantity": <int> }
    """

    # --- Load API key from .env (static) ---
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY not found. Create a .env file with OPENAI_API_KEY=sk-... "
            "or ensure the environment variable is set."
        )

    # --- Static LLM configuration ---
    MODEL = "gpt-5-nano"
    TEMPERATURE = 1

    # --- Customizable risk strategy section (edit the triple-quoted block below) ---
    RISK_STRATEGY = """
    Risk Strategy (editable):
    - Default posture: Balanced (medium risk).
    - If user later specifies "high risk": favor buying high-category stocks when momentum (recent market_history) is positive.
    - If user later specifies "low risk": prioritize staying/holding; only buy low-category stocks if strong positive trend; avoid selling at small dips.
    - You may assume exactly 3 stocks per category (high, medium, low) in Market_Summary.
    """

    # --- System instructions: use ONLY the provided JSON; simulate trades at current prices; no shorting ---
    SYSTEM_PROMPT = f"""
You are an assistant that must make simulated portfolio trade recommendations based ONLY on the JSON the user provides.
Do NOT use or reference any publicly available market data or external knowledge. This is a closed, simulated environment.

Goals:
1) For each existing non-cash position, decide one of: SELL, STAY, or BUY.
2) You may use 'market_history' to detect very recent trends (simple up/down momentum is fine).
3) CASH in 'Positions' indicates available dollars for new buys.
4) You may only transact at 'current_price' in Market_Summary.
5) You may NOT sell a stock unless the existing position holds at least the quantity you propose to sell (no shorting).
6) If recommending BUY, ensure total cost (sum of BUY qty * current_price) does not exceed CASH.
7) Use the 'category' field in Market_Summary to interpret risk levels.
8) Your recommendations must cover each non-cash position in Positions. If recommending BUY for a symbol not in Positions, you may add it with quantity > 0 provided you respect CASH and category rules.

Output requirement:
- You MUST call the provided tool with a structured list of recommendations, one object per non-cash ticker in Positions.
- For any BUY suggestion of a new ticker not already in Positions, you MAY include it as an additional item.
- Each object must contain exactly: action (SELL|STAY|BUY), ticker (string), quantity (integer >= 0).

Important:
- Keep the natural-language rationale concise.
- Then issue a single tool call containing your final recommendations that comply with all constraints.

{RISK_STRATEGY}
""".strip()

    # --- Tool schema for structured recommendations ---
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "set_recommendations",
                "description": "Submit the final list of trade recommendations for this simulation.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "recommendations": {
                            "type": "array",
                            "description": "One item per non-cash position; optional extra items for newly proposed BUYs.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "action": {
                                        "type": "string",
                                        "enum": ["SELL", "STAY", "BUY"],
                                        "description": "Decision for the ticker."
                                    },
                                    "ticker": {
                                        "type": "string",
                                        "description": "Ticker symbol, e.g., AAPL."
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "minimum": 0,
                                        "description": "Units to buy or sell. For STAY, set 0."
                                    }
                                },
                                "required": ["action", "ticker", "quantity"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["recommendations"],
                    "additionalProperties": False
                }
            }
        }
    ]

    # --- Single shared OpenAI client (static) ---
    _client = OpenAI(api_key=OPENAI_API_KEY)

    @staticmethod
    def evaluate_portfolio(sim_payload: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Accepts the simulation JSON (dict) and returns:
          (assistant_text, recommendations_list)
        Where recommendations_list = [{action, ticker, quantity}, ...]
        """

        # Compose messages: system + user (JSON)
        messages = [
            {"role": "system", "content": AITradingTool.SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    "Here is the complete simulation payload. Use ONLY this data:\n\n"
                    + json.dumps(sim_payload, indent=2, ensure_ascii=False)
                ),
            },
        ]

        # Send to Chat Completions with tool schema
        resp = AITradingTool._client.chat.completions.create(
            model=AITradingTool.MODEL,
            messages=messages,
            temperature=AITradingTool.TEMPERATURE,
            tools=AITradingTool.TOOLS,
            tool_choice="auto",
        )

        choice = resp.choices[0]
        assistant_text: str = (choice.message.content or "").strip()

        # Parse tool call (if any)
        recommendations: List[Dict[str, Any]] = []
        tool_calls = getattr(choice.message, "tool_calls", None)

        if tool_calls:
            for call in tool_calls:
                if call.type == "function" and call.function.name == "set_recommendations":
                    try:
                        args = json.loads(call.function.arguments or "{}")
                        recs = args.get("recommendations", [])
                        if isinstance(recs, list):
                            # Ensure each item has the desired shape
                            normalized: List[Dict[str, Any]] = []
                            for item in recs:
                                action = str(item.get("action", "")).upper()
                                ticker = str(item.get("ticker", "")).strip()
                                qty = int(item.get("quantity", 0))
                                normalized.append(
                                    {"action": action, "ticker": ticker, "quantity": qty}
                                )
                            recommendations = normalized
                    except Exception:
                        # If parsing fails, leave recommendations empty but return assistant text
                        pass

        return assistant_text, recommendations
