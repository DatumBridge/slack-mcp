# Slack MCP

Thin Slack tool-server for DatumBridge. Tools: list channels, post message, list/search messages.

**Publish name:** `Slack MCP` (k8s host `slack-mcp-main`).

**Auth:** Studio **Account → Integrations → Connect Slack** (user OAuth v2). Vault injects `credentials_json`. Writes require `confirm=true`.
