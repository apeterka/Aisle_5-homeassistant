"""Constants for the Aisle 5 integration."""

DOMAIN = "aisle5"

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_WEBHOOK_ID = "webhook_id"
CONF_WEBHOOK_SECRET = "webhook_secret"

# Bookkeeping: maps our internal store id (str) to the entry_id of the zone
# config entry we created for it, so later syncs can update it in place
# instead of only creating zones once and never touching them again.
CONF_ZONE_ENTRIES = "zone_entries"

# User-configurable via the integration's Options flow.
CONF_ZONE_RADIUS = "zone_radius"

# Fallback polling interval; the webhook keeps things fresh in real time,
# this is only a safety net if a push is ever missed.
UPDATE_INTERVAL_MINUTES = 15

# Default radius (meters) for zones auto-created from store coordinates,
# used until the user configures a different value via the Options flow.
DEFAULT_ZONE_RADIUS = 150
