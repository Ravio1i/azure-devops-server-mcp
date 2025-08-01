# Security Considerations

## 1. Introduction

This document provides security considerations for the Model Context Protocol (MCP), complementing the MCP Authorization specification. This document identifies security risks, attack vectors, and best practices specific to MCP implementations.
The primary audience for this document includes developers implementing MCP authorization flows, MCP server operators, and security professionals evaluating MCP-based systems. This document should be read alongside the MCP Authorization specification and OAuth 2.0 security best practices.

## 2. Attachs and Mitigations

### 2.1 ​Confused Deputy Problem

Attackers can exploit MCP servers proxying other resource servers, creating “confused deputy” vulnerabilities.

## 2.1.1 Attack Description

When an MCP proxy server uses a static client ID to authenticate with a third-party authorization server that does not support dynamic client registration, the following attack becomes possible:

1. A user authenticates normally through the MCP proxy server to access the third-party API.
2. During this flow, the third-party authorization server sets a cookie on the user agent indicating consent for the static client ID
3. An attacker later sends the user a malicious link containing a crafted authorization request which contains a malicious redirect URI along with a new dynamically registered client ID
4. When the user clicks the link, their browser still has the consent cookie from the previous legitimate request
5. The third-party authorization server detects the cookie and skips the consent screen
6. The MCP authorization code is redirected to the attacker’s server (specified in the malicious redirect_uri parameter during dynamic client registration)
7. The attacker exchanges the stolen authorization code for access tokens for the MCP server without the user’s explicit approval
8. The attacker now has access to the third-party API as the compromised user

## 2.1.2 Mitigation

MCP proxy servers using static client IDs MUST obtain user consent for each dynamically registered client before forwarding to third-party authorization servers (which may require additional consent).

For Azure DevOps Server MCP:

- **Not applicable**: This server does not act as an MCP proxy server. It connects directly to Azure DevOps Server using Personal Access Tokens (PATs) and does not proxy OAuth flows or use dynamic client registration.

## 2.2 Token Passthrough

“Token passthrough” is an anti-pattern where an MCP server accepts tokens from an MCP client without validating that the tokens were properly issued to the MCP server and passes them through to the downstream API. ([src](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices#token-passthrough))

### Mitigation

MCP servers MUST NOT accept any tokens that were not explicitly issued for the MCP server.

For Azure DevOps Server MCP, this was implemented by:

- **Direct token validation**: The server requires pre-configured Personal Access Tokens (PATs) via environment variables (`AZURE_DEVOPS_SERVER_TOKEN` in `AzureDevOpsServerClient`)
- **No token passthrough**: Client tokens are not accepted or passed through to downstream APIs
- **Environment-based authentication**: Tokens must be explicitly configured for this MCP server instance, preventing unauthorized token reuse

## 2.3 Session Hijacking

Session hijacking is an attack vector where a client is provided a session ID by the server, and an unauthorized party is able to obtain and use that same session ID to impersonate the original client and perform unauthorized actions on their behalf.

### ​Mitigation

To prevent session hijacking and event injection attacks, the following mitigations should be implemented:
MCP servers that implement authorization MUST verify all inbound requests. MCP Servers MUST NOT use sessions for authentication.

MCP servers MUST use secure, non-deterministic session IDs. Generated session IDs (e.g., UUIDs) SHOULD use secure random number generators. Avoid predictable or sequential session identifiers that could be guessed by an attacker. Rotating or expiring session IDs can also reduce the risk.

MCP servers SHOULD bind session IDs to user-specific information. When storing or transmitting session-related data (e.g., in a queue), combine the session ID with information unique to the authorized user, such as their internal user ID. Use a key format like <user_id>:<session_id>. This ensures that even if an attacker guesses a session ID, they cannot impersonate another user as the user ID is derived from the user token and not provided by the client.
MCP servers can optionally leverage additional unique identifiers.

For Azure DevOps Server MCP, this was implemented by:

- **Stateless authentication**: No session IDs are used; authentication is handled per-request via PAT tokens
- **No session management**: The server does not maintain user sessions, eliminating session hijacking attack vectors
- **Token-based security**: Uses Azure DevOps PAT tokens which are validated by Azure DevOps Server directly
- **Rate limiting**: Implemented request rate limiting to prevent abuse and resource exhaustion attacks
