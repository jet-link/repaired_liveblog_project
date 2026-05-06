"""Tests for trending velocity scoring."""

import math
import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model

from smart_blog.models import Item, ItemStatsHourly, TrendingItem, ViewEvent
from smart_blog.services import trending_service as ts

User = get_user_model()


class TrendingFormulaTests(TestCase):
    def test_trend_score_formula_basic(self):
        """Score uses log-based formula with velocity bonus."""
        h = 10.0
        score = ts.trend_score_from_stats(100, 10, 5, 2, 1, h)
        raw = 100 * 0.5 + 10 * 3.0 + 5 * 5.0 + 2 * 4.0 + 1 * 6.0
        base = math.log10(max(raw, 1))
        age_penalty = math.pow(h + 2, 1.5)
        expected = base / age_penalty
        self.assertAlmostEqual(score, expected, places=6)

    def test_trend_score_with_velocity_bonus(self):
        """Velocity bonus boosts the score when engagement_1h > engagement_prev_1h."""
        h = 10.0
        score_no_velocity = ts.trend_score_from_stats(100, 10, 5, 0, 0, h, 0, 0)
        score_with_velocity = ts.trend_score_from_stats(100, 10, 5, 0, 0, h, 10, 5)
        self.assertGreater(score_with_velocity, score_no_velocity)

    def test_growth_rate_from_engagement(self):
        growth = ts.growth_rate_from_engagement(10, 2, 1, 0, 0, 5, 1, 0, 0, 0)
        eng_1h = 10 + 2 * 3 + 1 * 5
        eng_prev = 5 + 1 * 3
        self.assertAlmostEqual(growth, eng_1h / eng_prev, places=5)

    def test_growth_rate_zero_prev(self):
        growth = ts.growth_rate_from_engagement(5, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        self.assertEqual(growth, 5.0)


class TrendingTrustFilterTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("trend_u1", "t1@test.com", "pass")
        self.user.profile.trust_score = 2.0
        self.user.profile.save()
        self.item = Item.objects.create(
            author=self.user,
            title="Low trust post",
            text="Body",
            slug="low-trust-trend",
            is_published=True,
        )

    def test_low_trust_author_excluded_from_calculate(self):
        ts.calculate_trending()
        self.assertFalse(TrendingItem.objects.filter(item=self.item).exists())

    def test_ok_trust_included(self):
        self.user.profile.trust_score = 3.0
        self.user.profile.save()
        ts.calculate_trending()
        self.assertTrue(TrendingItem.objects.filter(item=self.item).exists())


class TrendingStaleCleanupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("trend_u2", "t2@test.com", "pass")
        self.item = Item.objects.create(
            author=self.user,
            title="Old",
            text="Body",
            slug="old-trend",
            is_published=True,
            published_date=timezone.now() - timedelta(days=30),
        )
        TrendingItem.objects.create(
            item=self.item,
            trend_score=1.0,
            views_24h=1,
            likes_24h=0,
            comments_24h=0,
            growth_rate=1.0,
        )

    def test_stale_trending_row_removed_when_outside_window(self):
        """Items older than ACTIVE_DAYS are not recalculated; stale TrendingItem deleted."""
        ts.calculate_trending()
        self.assertFalse(TrendingItem.objects.filter(item=self.item).exists())


class TrendingSevenDayWindowTests(TestCase):
    """published_date within ACTIVE_DAYS is included."""

    def setUp(self):
        self.user = User.objects.create_user("trend_u3", "t3@test.com", "pass")

    def test_recent_within_window_gets_trending_row(self):
        item = Item.objects.create(
            author=self.user,
            title="Recent",
            text="Body",
            slug="recent-7d",
            is_published=True,
            published_date=timezone.now() - timedelta(days=ts.ACTIVE_DAYS - 1),
        )
        ts.calculate_trending()
        self.assertTrue(TrendingItem.objects.filter(item=item).exists())


class TrendingRollupTests(TestCase):
    """Hourly rollup writes ItemStatsHourly from ViewEvent."""

    def setUp(self):
        self.user = User.objects.create_user("trend_u4", "t4@test.com", "pass")
        self.item = Item.objects.create(
            author=self.user,
            title="Rollup",
            text="Body",
            slug="rollup-test",
            is_published=True,
        )

    def test_rollup_hourly_creates_row_for_view_event_in_bucket(self):
        now = timezone.now()
        hour_start, hour_end = ts.previous_completed_hour_bounds(now)
        ve = ViewEvent.objects.create(item=self.item)
        ViewEvent.objects.filter(pk=ve.pk).update(created_at=hour_start + timedelta(minutes=30))
        n = ts.rollup_item_stats_hourly_for_hour(hour_start_local=hour_start, now=now)
        self.assertGreaterEqual(n, 1)
        row = ItemStatsHourly.objects.get(item=self.item, hour_start=hour_start)
        self.assertEqual(row.views, 1)


class TrendingBatchAggregationTests(TestCase):
    """Batch aggregation computes correct counts from ViewEvent."""

    def setUp(self):
        self.user = User.objects.create_user("trend_u5", "t5@test.com", "pass")
        self.item = Item.objects.create(
            author=self.user,
            title="Batch",
            text="Body",
            slug="batch-agg-test",
            is_published=True,
        )

    def test_calculate_trending_with_view_events(self):
        for _ in range(5):
            ViewEvent.objects.create(item=self.item)
        ts.calculate_trending()
        t = TrendingItem.objects.get(item=self.item)
        self.assertEqual(t.views_24h, 5)
        self.assertGreater(t.trend_score, 0)
