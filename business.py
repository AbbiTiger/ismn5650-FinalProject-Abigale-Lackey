import json
import os
import requests
from datetime import datetime
from aitool import AITradingTool
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File paths for data storage
POSITIONS_FILE = 'current_positions.txt'
TRADING_HISTORY_FILE = 'trading_log.txt'

# Mothership API configuration
MOTHERSHIP_URL = "https://mothership-crg7hzedd6ckfegv.eastus-01.azurewebsites.net"
MOTHERSHIP_API_KEY = os.getenv('MOTHERSHIP_API_KEY')

def get_mothership_api_key():
    """Return the mothership API key from environment"""
    return MOTHERSHIP_API_KEY

def load_previous_prices():
    """Load the previous market prices from the positions file"""
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, 'r') as f:
                data = json.load(f)
                # Extract current_price from each position
                return {item['ticker']: item['current_price'] for item in data}
        except:
            return {}
    return {}

def save_positions(payload):
    """Save current positions to a local file in the format matching Assignment6PositionsSample.txt"""
    positions = payload.get('Positions', [])
    market_summary = payload.get('Market_Summary', [])
    
    # Create market prices dictionary
    market_prices = {
        item['ticker']: item['current_price'] 
        for item in market_summary
    }
    
    # Build positions in the required format
    positions_data = []
    for position in positions:
        ticker = position['ticker']
        quantity = position['quantity']
        purchase_price = position['purchase_price']
        current_price = market_prices.get(ticker, purchase_price)
        
        # Calculate unrealized P&L
        unrealized_pnl = (current_price - purchase_price) * quantity
        
        positions_data.append({
            "ticker": ticker,
            "quantity": quantity,
            "purchase_price": purchase_price,
            "current_price": current_price,
            "unrealized_pnl": round(unrealized_pnl, 2)
        })
    
    # Save to file
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions_data, f, indent=2)

def log_ai_recommendations(recommendations, date_str, market_summary):
    """Log AI trading recommendations to the trading history file"""
    # Load existing history
    history = []
    if os.path.exists(TRADING_HISTORY_FILE):
        try:
            with open(TRADING_HISTORY_FILE, 'r') as f:
                history = json.load(f)
        except:
            history = []
    
    # Create price lookup from market summary
    price_lookup = {item['ticker']: item['current_price'] for item in market_summary}
    
    # Add each recommendation to history
    for rec in recommendations:
        ticker = rec['ticker']
        current_price = price_lookup.get(ticker, 0.0)
        
        transaction = {
            'date': date_str,
            'ticker': ticker,
            'action': rec['action'],
            'price': current_price,
            'note': f"AI recommendation: {rec['action']} {rec['quantity']} shares"
        }
        
        if rec['quantity'] > 0:
            transaction['quantity'] = rec['quantity']
        
        history.append(transaction)
    
    # Save updated history
    with open(TRADING_HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def make_trade(trade_id, recommendations):
    """
    Post trade recommendations to the mothership API
    
    Args:
        trade_id: The unique trade ID from the /tick endpoint
        recommendations: List of trade recommendations from AI
        
    Returns:
        Updated positions from the API or None on error
    """
    api_key = get_mothership_api_key()
    if not api_key:
        print("Failed to get API key")
        return None
    
    # Format trades for the API
    trades = []
    for rec in recommendations:
        trades.append({
            "action": rec['action'],
            "ticker": rec['ticker'],
            "quantity": rec['quantity']
        })
    
    payload = {
        "id": trade_id,
        "trades": trades
    }
    
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{MOTHERSHIP_URL}/make_trade",
            json=payload,
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Trade successful: {result}")
            return result.get('Positions', [])
        else:
            print(f"Trade failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Error making trade: {e}")
        return None

def update_positions_from_api(api_positions, market_summary):
    """
    Update local positions file with data from the mothership API
    
    Args:
        api_positions: List of positions returned from /make_trade
        market_summary: Current market summary for price data
    """
    # Create market prices dictionary
    market_prices = {
        item['ticker']: item['current_price'] 
        for item in market_summary
    }
    
    # Build positions in the required format
    positions_data = []
    for position in api_positions:
        ticker = position['ticker']
        quantity = position['quantity']
        purchase_price = position['purchase_price']
        current_price = market_prices.get(ticker, purchase_price)
        
        # Calculate unrealized P&L
        unrealized_pnl = (current_price - purchase_price) * quantity
        
        positions_data.append({
            "ticker": ticker,
            "quantity": quantity,
            "purchase_price": purchase_price,
            "current_price": current_price,
            "unrealized_pnl": round(unrealized_pnl, 2)
        })
    
    # Save to file
    with open(POSITIONS_FILE, 'w') as f:
        json.dump(positions_data, f, indent=2)

def analyze_tick(payload: dict, trade_id: str) -> dict:
    """
    Analyze the tick payload using AI and execute trades.
    
    Args:
        payload: Dictionary containing Positions, Market_Summary, and market_history
        trade_id: Unique trade ID from the URL path parameter
        
    Returns:
        Dictionary with analysis results
    """
    positions = payload.get('Positions', [])
    market_summary = payload.get('Market_Summary', [])
    
    # Create a lookup dictionary for current prices
    current_prices = {
        item['ticker']: item['current_price'] 
        for item in market_summary
    }
    
    # Calculate unrealized P&L
    total_unrealized_pnl = 0.0
    positions_evaluated = 0
    
    for position in positions:
        ticker = position['ticker']
        quantity = position['quantity']
        purchase_price = position['purchase_price']
        
        # Find current price for this ticker
        if ticker in current_prices:
            current_price = current_prices[ticker]
            
            # Calculate unrealized P&L for this position
            # P&L = (current_price - purchase_price) * quantity
            position_pnl = (current_price - purchase_price) * quantity
            total_unrealized_pnl += position_pnl
            positions_evaluated += 1
    
    # Get AI recommendations
    recommendations = []
    ai_success = False
    
    try:
        ai_tool = AITradingTool()
        assistant_text, recommendations = ai_tool.evaluate_portfolio(payload)
        
        print(f"AI Analysis: {assistant_text}")
        print(f"AI Recommendations: {recommendations}")
        ai_success = True
        
    except Exception as e:
        print(f"Error in AI analysis: {e}")
        # Create fallback STAY recommendations for all non-CASH positions
        for position in positions:
            if position['ticker'] != 'CASH':
                recommendations.append({
                    "action": "STAY",
                    "ticker": position['ticker'],
                    "quantity": 0
                })
    
    # Get date from payload or use current date
    date_str = payload.get('DAY', datetime.now().strftime('%Y-%m-%d'))
    
    # Log AI recommendations (pass market_summary)
    if recommendations:
        log_ai_recommendations(recommendations, date_str, market_summary)
        
        # Make trades via API
        updated_positions = make_trade(trade_id, recommendations)
        
        # Update local positions with API response
        if updated_positions:
            update_positions_from_api(updated_positions, market_summary)
        else:
            # If trade failed, still update positions with current market data
            save_positions(payload)
    else:
        # No recommendations, just save positions
        save_positions(payload)
    
    # Return the analysis result in the expected format (matching Assignment 5/6)
    return {
        "result": "success",
        "summary": {
            "positions_evaluated": positions_evaluated,
            "unrealized_pnl": round(total_unrealized_pnl, 2)
        },
        "decisions": []  # Empty decisions list for Assignment 7 (AI handles this now)
    }

def get_dashboard_data():
    """Load data for the dashboard display"""
    # Load current positions
    positions_data = []
    if os.path.exists(POSITIONS_FILE):
        try:
            with open(POSITIONS_FILE, 'r') as f:
                positions_data = json.load(f)
        except:
            positions_data = []
    
    # Load trading history
    trading_history = []
    if os.path.exists(TRADING_HISTORY_FILE):
        try:
            with open(TRADING_HISTORY_FILE, 'r') as f:
                trading_history = json.load(f)
        except:
            trading_history = []
    
    return {
        'positions': positions_data,
        'trading_history': trading_history
    }