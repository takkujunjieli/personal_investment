
try:
    from src.ui import backtest_view
    print("backtest_view imported successfully")
except Exception as e:
    print(f"Error importing backtest_view: {e}")

try:
    from src.ui import long_term_view
    print("long_term_view imported successfully")
except Exception as e:
    print(f"Error importing long_term_view: {e}")
