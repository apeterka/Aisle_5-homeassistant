"""Constants for the Aisle 5 integration."""

DOMAIN = "aisle5"

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_WEBHOOK_ID = "webhook_id"
CONF_WEBHOOK_SECRET = "webhook_secret"

# Fallback polling interval; the webhook keeps things fresh in real time,
# this is only a safety net if a push is ever missed.
UPDATE_INTERVAL_MINUTES = 15

# Default radius (meters) for zones auto-created from store coordinates.
DEFAULT_ZONE_RADIUS = 150
