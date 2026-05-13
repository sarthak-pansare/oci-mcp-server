FROM python:3.12-slim

LABEL org.opencontainers.image.title="oci-mcp-server" \
      org.opencontainers.image.description="MCP server for Oracle Cloud Infrastructure" \
      org.opencontainers.image.licenses="Apache-2.0" \
      org.opencontainers.image.source="https://github.com/your-username/oci-mcp-server"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OCI_MCP_TRANSPORT=sse \
    OCI_MCP_HOST=0.0.0.0 \
    OCI_MCP_PORT=3000

WORKDIR /app

COPY pyproject.toml ./
COPY oci_mcp ./oci_mcp
COPY server.py ./
COPY README.md ./
COPY LICENSE ./

RUN pip install --no-cache-dir .

EXPOSE 3000

ENTRYPOINT ["oci-mcp-server"]
