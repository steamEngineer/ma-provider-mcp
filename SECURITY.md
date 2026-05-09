# Security Policy

## Reporting a Vulnerability

If you discover a security issue in this provider, please **do not** open a public
issue. Instead, email the maintainer directly via the address listed on the
[trudenboy GitHub profile](https://github.com/trudenboy).

We aim to acknowledge reports within 72 hours and to release a fix within 30 days
of confirmed reproduction.

## Scope

This provider exposes Music Assistant control APIs over the Model Context Protocol
(MCP). Authentication is delegated to MA's existing token system
(`mass.webserver.auth.authenticate_with_token`), and all permissions are gated
through provider configuration. The provider itself does not store credentials.
