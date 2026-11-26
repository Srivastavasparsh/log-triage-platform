import logging
import traceback
from pathlib import Path

Path("logs").mkdir(exist_ok=True)

logger = logging.getLogger("billing-service")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("logs/billing.log")
file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
logger.addHandler(file_handler)


def calculate_unit_price(total_amount: float, item_count: int) -> float:
    try:
        discount_rate = 0.10
        net_amount = total_amount * (1 - discount_rate)
        if item_count == 0:
            return 0.0
        return round(net_amount / item_count, 2)
    except Exception as error:
        trace = traceback.format_exc()
        logger.error(f"Unhandled {type(error).__name__}: {error}\n{trace}")
        raise
