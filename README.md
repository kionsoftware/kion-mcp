# Kion MCP Server

## Installation

> [!TIP]
> For more detailed installation and usage instructions, please see our [support documentation](https://support.kion.io/hc/en-us/articles/38760650970765-MCP-Server-Installation-and-Configuration)

### Claude Desktop Extension
`uv` is currently a requirement for the desktop extension. Please see [installation instructions](https://docs.astral.sh/uv/getting-started/installation/)

Once `uv` is installed, the Claude Desktop Extension can be installed by downloading the `.dxt` archive from the releases section, and then the archive can be installed via the extension settings in Claude Destkop, double clicking the file, or dragging the file onto the extension settings.

### Dockerhub
Releases are published to the `kionsoftware/kion-mcp` repository, and can be run directly using docker.

### Pypi
This package can be installed via pip.
`pip install kion-mcp-server`

## Development Setup

### Install uv

Install `uv` using homebrew with `brew install uv`

### Install an MCP client

An MCP server needs an MCP client to run it. For development - [the mcp inspector](https://github.com/modelcontextprotocol/inspector) is a great tool for getting up and running with the server.

### Add this server as a tool

For your MCP client there should be a json file defining what MCP Servers it has access to. Look up where this file is for your client and add something similar to this to it (json objects vary slightly by client check your client's documentation for the exact required JSON. MCP inspector has fields that can be configured directly.):

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
