# Reverse Proxy

The application is product-neutral. TLS termination, public HTTPS, mTLS, IP
allowlisting, bot verification, and product-specific rules belong in external
infrastructure.

## Routing

```text
https://your-domain.example/mcp     -> http://app:8000/mcp
https://your-domain.example/healthz -> http://app:8000/healthz
```

Pass only trusted and sanitized identity signals to the app. Configure trusted proxy
networks explicitly:

```bash
uv run tossinvest-mcp-remote serve-http \
  --host 0.0.0.0 \
  --port 8000 \
  --trusted-proxy "10.0.0.0/8"
```

## Nginx Example

```nginx
location /mcp {
    proxy_pass http://app:8000/mcp;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-Proto https;
    proxy_set_header X-Forwarded-Host $host;
}

location /healthz {
    proxy_pass http://app:8000/healthz;
}
```

## Caddy Example

```caddyfile
your-domain.example {
    reverse_proxy /mcp app:8000
    reverse_proxy /healthz app:8000
}
```

## Traefik Example

Route `/mcp` and `/healthz` to the same app service. Terminate TLS at Traefik and pass
only trusted forwarded headers to the app network.
