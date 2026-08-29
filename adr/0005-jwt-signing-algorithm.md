ADR-0005: JWT Signing Algorithm (RS256 vs HS256)

Date: 2026-8-29 Status: Accepted
Context

Eveto requires a stateless authentication mechanism to handle user sessions and authorize API requests. JSON Web Tokens (JWTs) are the standard choice. However, the architecture includes multiple distinct components (the core FastAPI application, Dramatiq background workers, and a mock payment provider). We must choose a signing algorithm that allows any component to verify a token's authenticity without compromising the system's overall security if a less-critical component is breached.
Options Considered
1. HS256 (HMAC with SHA-256)

    What it is: A symmetric signing algorithm. A single secret string (e.g., super-secret-key) is used to both sign the token and verify it.
    Strengths: Computationally very fast; trivial to implement (just share an environment variable); simple mental model.
    Weaknesses: The "Shared Secret" problem. Every service that needs to verify a token must possess the exact same secret. If the mock_payment_provider or a worker is compromised, the attacker gains the secret key and can forge tokens for any user (including admins), bringing down the entire system.

2. RS256 (RSA Signature with SHA-256)

    What it is: An asymmetric signing algorithm. Uses a public/private key pair (RSA). The private key signs the token; the public key verifies it.
    Strengths: Perfect for distributed systems. The Auth service holds the private key tightly. Workers, APIs, and external services only receive the public key. If a worker is breached, the attacker can only verify tokens, not forge them.
    Weaknesses: Slower cryptographic operations than HS256 (though negligible for standard web traffic); requires managing .pem key files instead of simple environment variables.

3. ES256 (ECDSA using P-256 and SHA-256)

    What it is: Another asymmetric algorithm, using Elliptic Curve Cryptography.
    Strengths: Much faster than RS256 and produces significantly shorter tokens/signatures.
    Weaknesses: Highly sensitive to implementation bugs (e.g., nonce reuse can leak the private key).

Decision

We choose RS256.

The security of a ticketing platform relies heavily on preventing unauthorized admin access and ticket reservation forgery. By using RS256, we isolate the ability to mint tokens to the core API/Auth service. Background workers and external integrations will only be provisioned with the public.pem key, ensuring that a breach in a peripheral service cannot compromise the core authentication system.
Consequences

    We must generate and securely store RSA key pairs (.pem files).
    In production, the private key must be injected securely (e.g., via Docker Secrets or Kubernetes Secrets) and never committed to version control.
    Pydantic Settings will use FilePath validators to ensure the keys exist at startup, failing fast if they are missing.
    We accept the slight CPU overhead of RSA verification on every request, which is easily mitigated by modern hardware and connection pooling.

Under what conditions would this change?

If we adopt a managed identity provider (like Auth0, AWS Cognito, or Keycloak) that defaults to a different standard, we would adapt to their default. Alternatively, if token size becomes a severe network bottleneck (e.g., sending tokens in cookies with strict size limits), we might migrate to ES256.