# Firecrawl MCP Configuration

The Firecrawl MCP server has been configured in multiple locations to ensure Cursor detects it:

## Configuration Locations

1. **Global Cursor Settings**: `~/Library/Application Support/Cursor/User/settings.json`
   - Added under both `mcp.servers` and `cursor.mcp.servers` keys

2. **Workspace Settings**: `.vscode/settings.json`
   - Added under `mcp.servers` key

## Configuration Details

```json
{
  "mcp.servers": {
    "firecrawl-mcp": {
      "command": "npx",
      "args": ["-y", "firecrawl-mcp"],
      "env": {
        "FIRECRAWL_API_KEY": "fc-b4714ee8a2124d93b0ba3449b627d795"
      }
    }
  }
}
```

## Next Steps

1. **Restart Cursor completely** (quit and reopen)
2. Check **Settings → Features → MCP Servers** (or search for "MCP" in settings)
3. Look for "firecrawl-mcp" in the list of MCP servers
4. If it still doesn't appear, check the **Developer Tools Console** for errors:
   - Help → Toggle Developer Tools → Console
   - Look for MCP-related errors

## Verification

After restarting Cursor:
- Open Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`)
- Search for "MCP" or "Firecrawl"
- You should see Firecrawl MCP tools available

## Troubleshooting

If the MCP server still doesn't appear:

1. **Verify Node.js is installed**:
   ```bash
   node --version
   npx --version
   ```

2. **Test MCP server manually**:
   ```bash
   npx -y firecrawl-mcp
   ```

3. **Check Cursor logs**:
   - `~/Library/Application Support/Cursor/logs/`
   - Look for MCP-related error messages

4. **Alternative**: Use the Python `FirecrawlClient` we created, which works independently of MCP:
   ```python
   from src.ingestion import FirecrawlClient
   client = FirecrawlClient()
   ```
