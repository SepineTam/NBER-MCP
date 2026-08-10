# NBER-MCP-SERVER
Here is NBER-MCP, which is made for read NBER paper list easier.

This repo has been disabled, the new one is [NBER-CLI](https://github.com/sepinetam/nber-cli], which is also could booted as a mcp server. 

## Quickly Start
### Claude Code
```bash
claude mcp add -s user nber-mcp -- uvx nber-cli mcp-server
```

### Codex
```bash
codex mcp add -- uvx nber-cli mcp-server
```

### OpenClaw
Send the message to your AI client. 
```text
Install nber-cli as a mcp server for yourself from [SepineTam/nber-cli](https://github.com/sepinetam/nber-cli) on GitHub. 
```

### Generally Config
```json
{
  "mcpServers": {
    "nber-mcp": {
      "command": "uvx",
      "args": [
        "nber-cli",
        "mcp-server"
      ]
    }
  }
}
```

