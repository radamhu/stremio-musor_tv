"""Unit tests for midnight boundary detection in time parsing."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from scraper import MusorTvScraper


class TestMidnightBoundary(unittest.TestCase):
    """Test cases for _infer_start_iso with midnight boundary scenarios."""
    
    def test_full_datetime_format(self):
        """Full datetime format should always be parsed correctly."""
        result = MusorTvScraper._infer_start_iso("2025.10.18 22:30")
        expected = datetime(2025, 10, 18, 22, 30).isoformat()
        self.assertEqual(result, expected)
    
    def test_full_datetime_with_extra_text(self):
        """Full datetime should be extracted from surrounding text."""
        result = MusorTvScraper._infer_start_iso("Start: 2025.10.18 22:30 - Some Movie")
        expected = datetime(2025, 10, 18, 22, 30).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_time_only_same_day_afternoon(self, mock_datetime):
        """Time-only format in the afternoon should use current day."""
        # Mock current time: 15:00 (3 PM)
        mock_now = datetime(2025, 10, 18, 15, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Parse time: 18:30 (6:30 PM) - same day, a few hours ahead
        result = MusorTvScraper._infer_start_iso("18:30")
        expected = datetime(2025, 10, 18, 18, 30, 0).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_time_only_late_night_needs_next_day(self, mock_datetime):
        """Time-only format for early morning should use next day when scraped late."""
        # Mock current time: 23:00 (11 PM on Oct 18)
        mock_now = datetime(2025, 10, 18, 23, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Parse time: 01:30 (1:30 AM)
        # This is 22.5 hours in the past if we use today's date
        # Should be adjusted to tomorrow (Oct 19)
        result = MusorTvScraper._infer_start_iso("01:30")
        expected = datetime(2025, 10, 19, 1, 30, 0).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_time_only_early_morning_same_day(self, mock_datetime):
        """Early morning time scraped in early morning should use same day."""
        # Mock current time: 02:00 (2 AM on Oct 18)
        mock_now = datetime(2025, 10, 18, 2, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Parse time: 06:00 (6 AM) - same day, a few hours ahead
        result = MusorTvScraper._infer_start_iso("06:00")
        expected = datetime(2025, 10, 18, 6, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_boundary_case_exactly_12_hours_past(self, mock_datetime):
        """Time exactly 12 hours in the past should use today (not adjusted)."""
        # Mock current time: 18:00 (6 PM on Oct 18)
        mock_now = datetime(2025, 10, 18, 18, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Parse time: 06:00 (6 AM) - exactly 12 hours ago
        # Should NOT be adjusted (only > 12 hours triggers adjustment)
        result = MusorTvScraper._infer_start_iso("06:00")
        expected = datetime(2025, 10, 18, 6, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_boundary_case_just_over_12_hours_past(self, mock_datetime):
        """Time just over 12 hours in the past should be adjusted to next day."""
        # Mock current time: 18:30 (6:30 PM on Oct 18)
        mock_now = datetime(2025, 10, 18, 18, 30, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Parse time: 06:00 (6 AM) - 12.5 hours ago
        # Should be adjusted to next day
        result = MusorTvScraper._infer_start_iso("06:00")
        expected = datetime(2025, 10, 19, 6, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_near_midnight_crossing(self, mock_datetime):
        """Programs just after midnight should be next day when scraped late."""
        # Mock current time: 23:45 (11:45 PM on Oct 18)
        mock_now = datetime(2025, 10, 18, 23, 45, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Parse time: 00:15 (12:15 AM)
        # This is 23.5 hours in the past if today, should be adjusted to tomorrow
        result = MusorTvScraper._infer_start_iso("00:15")
        expected = datetime(2025, 10, 19, 0, 15, 0).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_late_night_movie_scenario(self, mock_datetime):
        """Real-world scenario: Late night movie at 02:00 scraped at 22:00."""
        # Mock current time: 22:00 (10 PM on Oct 18)
        mock_now = datetime(2025, 10, 18, 22, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        # Parse time: 02:00 (2 AM) - late night movie
        # This is 20 hours in the past if today, should be adjusted to tomorrow
        result = MusorTvScraper._infer_start_iso("02:00")
        expected = datetime(2025, 10, 19, 2, 0, 0).isoformat()
        self.assertEqual(result, expected)
    
    def test_no_time_pattern_fallback(self):
        """If no time pattern is found, should return current time."""
        result = MusorTvScraper._infer_start_iso("No time here!")
        # Just verify it's a valid ISO format datetime
        parsed = datetime.fromisoformat(result)
        self.assertIsInstance(parsed, datetime)


class TestTimeParsingEdgeCases(unittest.TestCase):
    """Additional edge case tests for time parsing."""
    
    def test_single_digit_hour(self):
        """Single digit hours should be parsed correctly."""
        result = MusorTvScraper._infer_start_iso("2025.10.18 9:30")
        expected = datetime(2025, 10, 18, 9, 30).isoformat()
        self.assertEqual(result, expected)
    
    @patch('scraper.datetime')
    def test_single_digit_hour_time_only(self, mock_datetime):
        """Single digit hours in time-only format should work."""
        mock_now = datetime(2025, 10, 18, 15, 0, 0)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        
        result = MusorTvScraper._infer_start_iso("9:30")
        # 9:30 AM when current time is 3 PM = 5.5 hours in the past
        # Should use today (< 12 hours)
        expected = datetime(2025, 10, 18, 9, 30, 0).isoformat()
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
