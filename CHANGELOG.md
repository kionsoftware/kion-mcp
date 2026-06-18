# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Placeholder for next release

## [0.6.0] -- 2026-06-22

### Changed
- cryptography 46.0.6 → 49.0.0
- python-multipart 0.0.24 → 0.0.32
- pyjwt 2.12.1 → 2.13.0
- starlette 1.0.0 → 1.3.1
- authlib 1.6.9 → 1.6.12
- idna 3.11 → 3.18, lupa 2.6 → 2.8


## [0.5.0] -- 2026-05-15

### Added
- Added the ability to search accounts by account number. [#13](https://github.com/kionsoftware/kion-mcp/pull/13)

### Changed
- Fixes DXT Python pinning issues, updating fastmcp and authlib. [#12](https://github.com/kionsoftware/kion-mcp/pull/12)

## [0.4.0] -- 2026-02-09

### Changed
- Updated dependencies fastmcp, starlette, and authlib.

## [0.3.0] -- 2025-09-29

Better support for strict MCP clients and spend report tool bugfixes.

### Changed
- The fixed_spec.json used to generate tool endpoints has been changed to ensure it does not cause failures with strict clients. [#7](https://github.com/kionsoftware/kion-mcp/pull/7)

### Fixed
- Added a default spend type, and fixed issues with permissions and credit/refund math on the spend report tool. [#6]https://github.com/kionsoftware/kion-mcp/pull/6)

## [0.2.0] - 2025-08-19

PyPi build support and improved auth feedback.

### Added
- Better feedback for Authentication failures while running in Claude Desktop Extension Mode [#3](https://github.com/kionsoftware/kion-mcp/pull/3)

### Changed
- Swagger spec loading refactored to better handle PyPi installations and redundancies. [#4](https://github.com/kionsoftware/kion-mcp/pull/4)

## [0.1.1] - 2025-08-15

Initial release of the Kion MCP Server - a comprehensive Model Context Protocol server that enables AI assistants to interact with Kion cloud governance platform APIs. This release provides essential tools for cloud spend reporting, organizational management, compliance monitoring, and budget operations.

### Supported Integrations
- **Docker**: Multi-platform container support (amd64, arm64)
- **PyPI**: Standard Python package installation
- **Desktop Extensions**: Native .dxt packaging for desktop clients
