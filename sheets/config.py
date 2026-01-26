"""
Configuration for Google Sheets brand reporting system
"""

# Tab names (frozen)
TAB_BRAND_OVERVIEW = "Brand_Overview"
TAB_ALL_TIME_STATS = "All_Time_Stats"
TAB_WEEKLY_SNAPSHOTS = "Weekly_Snapshots"
TAB_CHART_DATA = "Chart_Data"

# Weekly_Snapshots column schema (LOCKED - DO NOT REORDER)
WEEKLY_SNAPSHOT_COLUMNS = [
    'iso_week',
    'week_start',
    'week_end',
    'total_reviews',
    'total_reviews_last_week',
    'wow_change',
    'wow_change_pct',
    'avg_rating',
    'avg_rating_last_week',
    'wow_rating_change',
    'positive_count',
    'positive_pct',
    'neutral_count',
    'neutral_pct',
    'negative_count',
    'negative_pct',
    'rating_5',
    'rating_4',
    'rating_3',
    'rating_2',
    'rating_1',
    'reviews_with_reply',
    'response_rate_pct',
    'avg_response_hours',
    'avg_response_days',
    'verified_count',
    'organic_count',
    'reviews_edited',
    'generated_at'
]

# JSON path mapping for weekly data
WEEKLY_COLUMN_PATHS = {
    'iso_week': 'report_metadata.iso_week',
    'week_start': 'report_metadata.week_start',
    'week_end': 'report_metadata.week_end',
    'total_reviews': 'week_stats.review_volume.total_this_week',
    'total_reviews_last_week': 'week_stats.review_volume.total_last_week',
    'wow_change': 'week_stats.review_volume.wow_change',
    'wow_change_pct': 'week_stats.review_volume.wow_change_pct',
    'avg_rating': 'week_stats.rating_performance.avg_rating_this_week',
    'avg_rating_last_week': 'week_stats.rating_performance.avg_rating_last_week',
    'wow_rating_change': 'week_stats.rating_performance.wow_change',
    'positive_count': 'week_stats.sentiment.positive.count',
    'positive_pct': 'week_stats.sentiment.positive.percentage',
    'neutral_count': 'week_stats.sentiment.neutral.count',
    'neutral_pct': 'week_stats.sentiment.neutral.percentage',
    'negative_count': 'week_stats.sentiment.negative.count',
    'negative_pct': 'week_stats.sentiment.negative.percentage',
    'rating_5': 'week_stats.rating_distribution.5_stars',
    'rating_4': 'week_stats.rating_distribution.4_stars',
    'rating_3': 'week_stats.rating_distribution.3_stars',
    'rating_2': 'week_stats.rating_distribution.2_stars',
    'rating_1': 'week_stats.rating_distribution.1_star',
    'reviews_with_reply': 'week_stats.response_performance.reviews_with_response',
    'response_rate_pct': 'week_stats.response_performance.response_rate_pct',
    'avg_response_hours': 'week_stats.response_performance.avg_response_time_hours',
    'avg_response_days': 'week_stats.response_performance.avg_response_time_days',
    'verified_count': 'week_stats.review_volume.by_source.verified_invited',
    'organic_count': 'week_stats.review_volume.by_source.organic',
    'reviews_edited': 'week_stats.response_performance.reviews_edited',
    'generated_at': 'report_metadata.generated_at'
}

# Chart_Data table locations (fixed ranges)
CHART_RATING_TREND = {'start_row': 2, 'max_rows': 100}
CHART_VOLUME_TREND = {'start_row': 105, 'max_rows': 100}
CHART_SENTIMENT = {'start_row': 208, 'max_rows': 4}
CHART_RATING_DIST = {'start_row': 215, 'max_rows': 5}
CHART_NEGATIVE_THEMES = {'start_row': 223, 'max_rows': 10}

# Service account permissions
# Options: 'writer', 'reader', 'owner'
SHARE_WITH_SERVICE_ACCOUNT = True
SERVICE_ACCOUNT_ROLE = 'writer'

# Default sheet formatting
DEFAULT_FONT = 'Arial'
DEFAULT_FONT_SIZE = 10
HEADER_FONT_SIZE = 11
HEADER_BOLD = True