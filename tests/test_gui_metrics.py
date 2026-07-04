"""Test GUI Metrics Display - Dashboard Cards"""

import pytest
import customtkinter as ctk
from sage.gui.config import GUIConfig
from sage.store import connect

pytestmark = pytest.mark.gui


class TestMetricCards:
    """Test dashboard metric cards display correctly"""

    def test_metric_card_creation(self):
        """Test: MetricCard widget can be created"""
        from sage.gui.widgets.metric_card import MetricCard

        root = ctk.CTk()
        card = MetricCard(root, label="Test", value="42", subtitle="Items")

        assert card.label == "Test"
        assert card._value == "42"

        root.destroy()

    def test_token_metric_card(self):
        """Test: TokenMetricCard displays used | saved"""
        from sage.gui.widgets.metric_card import DualMetricCard

        root = ctk.CTk()
        card = DualMetricCard(root, label="Tokens")

        # Test update method exists and works
        card.update_metric(
            total_value="887K | 2.1M",
            session_value="50K | 100K",
            total_hint="Used | Saved",
            session_hint="Used | Saved",
            detail="Real compression"
        )

        assert card.total_value.cget("text") == "887K | 2.1M"
        assert card.session_value.cget("text") == "50K | 100K"

        root.destroy()

    def test_dual_metric_card_layout(self):
        """Test: DualMetricCard has Total and Session columns"""
        from sage.gui.widgets.metric_card import DualMetricCard

        root = ctk.CTk()
        card = DualMetricCard(root, label="Commands")

        # Check that both column labels exist
        assert hasattr(card, "total_title")
        assert hasattr(card, "session_title")
        assert hasattr(card, "total_value")
        assert hasattr(card, "session_value")

        root.destroy()


class TestDashboardMetrics:
    """Test dashboard fetches and displays real data"""

    def test_fetch_compression_metrics(self):
        """Test: Dashboard can fetch compression stats from DB"""
        with connect() as conn:
            # Ensure table exists
            conn.execute("""
                CREATE TABLE IF NOT EXISTS context_compression (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER,
                    created_at TEXT NOT NULL,
                    original_tokens INTEGER NOT NULL,
                    compressed_tokens INTEGER NOT NULL,
                    saved_tokens INTEGER NOT NULL
                )
            """)

            cursor = conn.execute("""
                SELECT
                    SUM(original_tokens) as original,
                    SUM(compressed_tokens) as compressed,
                    SUM(saved_tokens) as saved
                FROM context_compression
            """)
            row = cursor.fetchone()

            original = row[0] or 0
            compressed = row[1] or 0
            saved = row[2] or 0

            print(f"\n📊 Dashboard Data Source:")
            print(f"   Original: {original:,} tokens")
            print(f"   Compressed: {compressed:,} tokens")
            print(f"   Saved: {saved:,} tokens")

            # These should match your actual DB
            assert original >= 0
            assert compressed >= 0
            assert saved >= 0

    def test_format_count_helper(self):
        """Test: _format_count helper formats numbers correctly"""
        # Import the formatting function
        from sage.gui.app import SAGEApp

        app = SAGEApp()

        # Test exact formatting
        test_cases = [
            (0, "0"),
            (42, "42"),
            (999, "999"),
            (1000, "1K"),
            (1500, "1K"),
            (50000, "50K"),
            (887000, "887K"),
            (1000000, "1.0M"),
            (2100000, "2.1M"),
        ]

        for value, expected in test_cases:
            result = app._format_count(value)
            print(f"   {value:,} -> {result} (expected {expected})")
            assert result == expected, f"Format mismatch: {value} -> {result}, expected {expected}"

        app.destroy()

    def test_token_card_receives_correct_data(self):
        """Test: Token card receives data in correct format"""
        from sage.gui.app import SAGEApp

        app = SAGEApp()

        # Simulate metric update with large numbers
        all_used = 887000
        all_saved = 2100000
        session_used = 50000
        session_saved = 100000

        # Format the way the app does
        all_used_k = app._format_count(all_used)
        all_saved_k = app._format_count(all_saved)
        sess_used_k = app._format_count(session_used)
        sess_saved_k = app._format_count(session_saved)

        print(f"\n💳 Token Card Data:")
        print(f"   Total: {all_used_k} | {all_saved_k}")
        print(f"   Session: {sess_used_k} | {sess_saved_k}")

        # Update the token card
        app.tokens_card.update_metric(
            total_value=f"{all_used_k} | {all_saved_k}",
            session_value=f"{sess_used_k} | {sess_saved_k}",
            total_hint="Used | Saved",
            session_hint="Used | Saved",
            detail="Real compression"
        )

        # Verify the card displays the values
        displayed = app.tokens_card.total_value.cget("text")
        print(f"   Displayed: {displayed}")

        assert "887K" in displayed
        assert "2.1M" in displayed

        app.destroy()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
