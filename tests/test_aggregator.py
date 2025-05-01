import unittest
import threading
import time
from linux_edr.aggregator import Aggregator


class TestAggregator(unittest.TestCase):
    def test_add_and_snapshot(self):
        # Create aggregator with small buffer size
        agg = Aggregator(maxlen=5)

        # Add some events
        agg.add({"id": 1, "command": "ls"})
        agg.add({"id": 2, "command": "cat"})
        agg.add({"id": 3, "command": "grep"})

        # Take snapshot and verify
        events = agg.snapshot_and_clear()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["id"], 1)
        self.assertEqual(events[1]["id"], 2)
        self.assertEqual(events[2]["id"], 3)

        # Buffer should be empty after snapshot
        self.assertEqual(len(agg.snapshot_and_clear()), 0)

    def test_buffer_size_limit(self):
        # Create aggregator with small buffer size
        agg = Aggregator(maxlen=3)

        # Add more events than buffer size
        for i in range(5):
            agg.add({"id": i, "command": f"cmd{i}"})

        # Should only have the last 3 events
        events = agg.snapshot_and_clear()
        self.assertEqual(len(events), 3)
        self.assertEqual(events[0]["id"], 2)
        self.assertEqual(events[1]["id"], 3)
        self.assertEqual(events[2]["id"], 4)

    def test_thread_safety(self):
        # Create aggregator
        agg = Aggregator(maxlen=1000)

        # Function to add events from multiple threads
        def add_events(start_id, count):
            for i in range(count):
                agg.add({"id": start_id + i, "command": f"cmd{start_id + i}"})

        # Create and start threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_events, args=(i * 100, 100))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Should have all 500 events
        events = agg.snapshot_and_clear()
        self.assertEqual(len(events), 500)

    def test_max_age_filtering(self):
        """Test that events older than max_age_seconds are filtered out."""
        # Create aggregator with short max age
        agg = Aggregator(maxlen=100, max_age_seconds=0.1)

        # Add some events
        agg.add({"id": 1, "command": "ls"})
        agg.add({"id": 2, "command": "cat"})

        # Wait for events to become stale
        time.sleep(0.2)

        # Add a fresh event
        agg.add({"id": 3, "command": "grep"})

        # Take snapshot - should only have the fresh event
        events = agg.snapshot_and_clear()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["id"], 3)

    def test_add_empty_event(self):
        """Test that adding an empty event returns False and doesn't add to buffer."""
        agg = Aggregator(maxlen=10)

        # Add an empty event
        result = agg.add({})
        self.assertFalse(result)

        # Add a None event (should be caught by the if not event check)
        result = agg.add(None)
        self.assertFalse(result)

        # Buffer should still be empty
        self.assertEqual(len(agg.snapshot_and_clear()), 0)

    def test_get_stats(self):
        """Test the get_stats method returns correct statistics."""
        agg = Aggregator(maxlen=100)

        # Add some events
        for i in range(10):
            agg.add({"id": i, "command": f"cmd{i}"})

        # Simulate a dropped event by directly incrementing counter
        agg.total_dropped += 1

        # Get stats
        stats = agg.get_stats()

        # Verify stats
        self.assertEqual(stats["buffer_size"], 10)
        self.assertEqual(stats["buffer_capacity"], 100)
        self.assertEqual(stats["total_received"], 10)
        self.assertEqual(stats["total_dropped"], 1)
        self.assertEqual(stats["buffer_usage_percent"], 10.0)

    def test_timestamp_handling(self):
        """Test internal timestamp handling with max_age_seconds."""
        # Create aggregator with max_age
        agg = Aggregator(maxlen=10, max_age_seconds=1.0)

        # Add event with timestamp already set
        event_with_timestamp = {"id": 1, "command": "ls", "_timestamp": time.monotonic()}
        agg.add(event_with_timestamp)

        # Add event without timestamp
        agg.add({"id": 2, "command": "grep"})

        # Both should have timestamps in the buffer
        self.assertEqual(len(agg.buffer), 2)

        # Both events should have _timestamp
        self.assertIn("_timestamp", agg.buffer[0])
        self.assertIn("_timestamp", agg.buffer[1])

        # Take snapshot - timestamps should be removed
        events = agg.snapshot_and_clear()
        self.assertEqual(len(events), 2)
        for event in events:
            self.assertNotIn("_timestamp", event)


if __name__ == "__main__":
    unittest.main()
