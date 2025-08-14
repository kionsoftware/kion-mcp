# Kion MCP Server Prototype

## How to run

### Install uv (first time only)

Install `uv` using homebrew with `brew install uv`

### Install an MCP client

An MCP server needs an MCP client to run it. I recommend using Claude Desktop or VSCode CoPilot Agent Mode for running the MCP Server.

### Add this server as a tool

For your MCP client there should be a json file defining what MCP Servers it has access to. Look up where this file is for your client and add something similar to this to it (json objects vary slightly by client check your client's documentation for the exact required JSON):

```
"KionMcp": {
    "command": "uv",
    "args": [
        "--directory",
        "<absolute path to this folder>",
        "run",
        "kion-mcp-server"
    ]
}
```

NOTE: sometimes you will need to give an exact path to `uv` for some clients to work properly. Just run `which uv` and put the output of that as the command in the JSON

### Restart your client and start using the server
