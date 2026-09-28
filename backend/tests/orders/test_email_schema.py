from datetime import datetime, timezone
from src.modules.order.schemas import OrderEmailDataSchema, OrderEmailItemSchema


class TestEmailSchema:
    def test_order_email_data_schema_calculation(self):
        items = [
            OrderEmailItemSchema(
                category_name="VIP Pass",
                price_paid=150.0,
                quantity=2,
            ),
            OrderEmailItemSchema(
                category_name="Standard",
                price_paid=50.0,
                quantity=1,
            ),
        ]
        schema = OrderEmailDataSchema(
            order_id=1001,
            created_at=datetime.now(timezone.utc),
            user_email="fan@example.com",
            event_title="Rock Concert 2026",
            event_started_at=datetime(2026, 10, 1, 19, 0, tzinfo=timezone.utc),
            event_address="Madison Square Garden, NYC",
            items=items,
            refund_issued=False,
        )

        assert schema.order_id == 1001
        assert schema.user_email == "fan@example.com"
        assert schema.total_price == 350.0
        assert schema.items[0].category_name == "VIP Pass"
        assert schema.items[0].price_paid == 150.0
        assert schema.items[1].quantity == 1
