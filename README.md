# KCSC Standard MCP

Standalone MCP server package extracted from `KDHStandardChecker` for external sharing.

## Included

- `src/standard_checker/mcp_server/mcp_server.py`
- `src/standard_checker/clients/kcsc/kcsc.py`
- `src/standard_checker/parsers/excel_parser.py`
- `src/standard_checker/parsers/pdf_parser.py`
- `src/standard_checker/prompts/__init__.py`

This package is intended to expose:

- Excel/PDF parsing
- KCSC code lookup
- Review package generation for Claude/Desktop MCP usage

## Install

### Option 1. Editable install

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

### Option 2. Requirements only

```powershell
py -3 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-mcp.txt
```

## Run locally

```powershell
.venv\Scripts\Activate.ps1
kcsc-standard-mcp
```

## Claude Desktop config

Use [claude_desktop_config.example.json](./claude_desktop_config.example.json) as a base.

Windows config path is usually:

```text
%APPDATA%\Claude\claude_desktop_config.json
```

If the command is not on PATH, use the venv executable directly:

```json
{
  "mcpServers": {
    "kcsc-standard-mcp": {
      "command": "C:\\path\\to\\KCSC-STNADRD-MCP\\.venv\\Scripts\\kcsc-standard-mcp.exe",
      "env": {
        "KCSC_API_KEY": "YOUR_KCSC_API_KEY"
      }
    }
  }
}
```

## Required environment variables

- `KCSC_API_KEY`

Optional:

- `MCP_DASH_HOST`
- `MCP_DASH_PORT`

## Notes

- This extracted package currently keeps the original package path `standard_checker.*`.
- The source files were copied from the main project and are intended as a starting point for a dedicated public MCP repository.
- The copied prompt/client files may still contain text encoding issues inherited from the source project and should be cleaned before public release.
