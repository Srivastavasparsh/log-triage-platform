from target_app.billing import calculate_unit_price


def test_standard_order():
    assert calculate_unit_price(100.0, 2) == 45.0


def test_zero_items_edge_case():
    assert calculate_unit_price(100.0, 0) == 0.0