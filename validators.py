def validate_tick_payload(payload: dict) -> tuple[bool, str]:
    """
    Validate the tick payload structure and data types.
    
    Args:
        payload: The JSON payload to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not isinstance(payload, dict):
        return False, "Payload must be a JSON object"
    
    # Validate Positions
    if 'Positions' not in payload:
        return False, "Missing required field: Positions"
    
    positions = payload['Positions']
    if not isinstance(positions, list):
        return False, "Positions must be a list"
    
    if len(positions) == 0:
        return False, "Positions must be a non-empty list"
    
    for i, pos in enumerate(positions):
        if not isinstance(pos, dict):
            return False, f"Position at index {i} must be an object"
        
        # Check required fields
        if 'ticker' not in pos:
            return False, f"Position at index {i} missing 'ticker'"
        if 'quantity' not in pos:
            return False, f"Position at index {i} missing 'quantity'"
        if 'purchase_price' not in pos:
            return False, f"Position at index {i} missing 'purchase_price'"
        
        # Check types
        if not isinstance(pos['ticker'], str):
            return False, f"Position at index {i}: 'ticker' must be a string"
        if not isinstance(pos['quantity'], (int, float)):
            return False, f"Position at index {i}: 'quantity' must be a number"
        if not isinstance(pos['purchase_price'], (int, float)):
            return False, f"Position at index {i}: 'purchase_price' must be a number"
    
    # Validate Market_Summary
    if 'Market_Summary' not in payload:
        return False, "Missing required field: Market_Summary"
    
    market_summary = payload['Market_Summary']
    if not isinstance(market_summary, list):
        return False, "Market_Summary must be a list"
    
    if len(market_summary) == 0:
        return False, "Market Summary must be a non-empty list"
    
    for i, item in enumerate(market_summary):
        if not isinstance(item, dict):
            return False, f"Market_Summary item at index {i} must be an object"
        
        # Check required fields
        if 'ticker' not in item:
            return False, f"Market_Summary at index {i} missing 'ticker'"
        if 'current_price' not in item:
            return False, f"Market_Summary at index {i} missing 'current_price'"
        if 'category' not in item:
            return False, f"Market_Summary at index {i} missing 'category'"
        
        # Check types
        if not isinstance(item['ticker'], str):
            return False, f"Market_Summary at index {i}: 'ticker' must be a string"
        if not isinstance(item['current_price'], (int, float)):
            return False, f"Market_Summary at index {i}: 'current_price' must be a number"
        if not isinstance(item['category'], str):
            return False, f"Market_Summary at index {i}: 'category' must be a string"
    
    # Validate market_history
    if 'market_history' not in payload:
        return False, "Missing required field: market_history"
    
    market_history = payload['market_history']
    if not isinstance(market_history, list):
        return False, "market_history must be a list"
    
    if len(market_history) == 0:
        return False, "market_history must be a non-empty list"
    
    for i, item in enumerate(market_history):
        if not isinstance(item, dict):
            return False, f"market_history item at index {i} must be an object"
        
        # Check required fields
        if 'ticker' not in item:
            return False, f"market_history at index {i} missing 'ticker'"
        if 'price' not in item:
            return False, f"market_history at index {i} missing 'price'"
        if 'day' not in item:
            return False, f"market_history at index {i} missing 'day'"
        
        # Check types
        if not isinstance(item['ticker'], str):
            return False, f"market_history at index {i}: 'ticker' must be a string"
        if not isinstance(item['price'], (int, float)):
            return False, f"market_history at index {i}: 'price' must be a number"
        # Day can now be either string (date format) or int
        if not isinstance(item['day'], (int, str)):
            return False, f"market_history at index {i}: 'day' must be a string or integer"
    
    # Validate DAY field (Assignment 7 modification)
    if 'DAY' in payload:
        if not isinstance(payload['DAY'], str):
            return False, "DAY must be a string in 'yyyy-mm-dd' format"
    
    return True, ""