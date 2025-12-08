# Invoice Processing Agent - Deployment Guide

## Overview

This guide covers deploying the Invoice Processing Agent to production environments.

## Production Deployment Options

### Option 1: Docker (Recommended for Scalability)

#### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose port for Streamlit
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run application
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### docker-compose.yml

```yaml
version: '3.8'

services:
  invoice-processor:
    build: .
    ports:
      - "8501:8501"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - LOG_LEVEL=INFO
    volumes:
      - ./sample_invoices:/app/sample_invoices
      - ./uploads:/app/uploads
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Build and Run

```bash
# Build image
docker build -t invoice-processor:v1 .

# Run container
docker run -e ANTHROPIC_API_KEY=sk-ant-... -p 8501:8501 invoice-processor:v1

# Or use docker-compose
docker-compose up -d
```

### Option 2: Cloud Deployment

#### AWS ECS

```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

docker tag invoice-processor:v1 <account>.dkr.ecr.us-east-1.amazonaws.com/invoice-processor:v1
docker push <account>.dkr.ecr.us-east-1.amazonaws.com/invoice-processor:v1

# Deploy to ECS (update task definition, service)
```

#### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT/invoice-processor

# Deploy
gcloud run deploy invoice-processor \
  --image gcr.io/PROJECT/invoice-processor \
  --platform managed \
  --region us-central1 \
  --set-env-vars ANTHROPIC_API_KEY=sk-ant-...
```

#### Azure Container Instances

```bash
# Build and push to ACR
az acr build --registry <registry-name> --image invoice-processor:v1 .

# Deploy
az container create \
  --resource-group myResourceGroup \
  --name invoice-processor \
  --image <registry-name>.azurecr.io/invoice-processor:v1 \
  --environment-variables ANTHROPIC_API_KEY=sk-ant-...
```

### Option 3: Traditional Server Deployment

#### Ubuntu/Debian

```bash
# Install Python and dependencies
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Create app directory
sudo mkdir -p /opt/invoice-processor
sudo chown $USER:$USER /opt/invoice-processor

# Clone/copy application
cd /opt/invoice-processor
git clone ... .  # or copy files

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create systemd service
sudo tee /etc/systemd/system/invoice-processor.service > /dev/null <<EOF
[Unit]
Description=Invoice Processing Agent
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/invoice-processor
Environment="PYTHONUNBUFFERED=1"
Environment="ANTHROPIC_API_KEY=sk-ant-..."
ExecStart=/opt/invoice-processor/venv/bin/streamlit run app.py --server.port 8501

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable invoice-processor
sudo systemctl start invoice-processor

# Check status
sudo systemctl status invoice-processor
```

#### RHEL/CentOS

```bash
# Similar to Ubuntu, use yum instead of apt-get
sudo yum install -y python3.11 python3.11-devel

# ... rest is similar
```

## Infrastructure Requirements

### Minimum
- **CPU**: 2 cores
- **Memory**: 2GB RAM
- **Storage**: 10GB
- **Network**: Public internet access for Claude API

### Recommended Production
- **CPU**: 4-8 cores
- **Memory**: 8GB RAM
- **Storage**: 100GB (for invoice archives)
- **Network**: Dedicated outbound for API calls
- **Load Balancer**: For horizontal scaling

## Monitoring & Observability

### Application Metrics

```python
# Add to invoice_agent.py for monitoring
import time
from datetime import datetime

METRICS = {
    "total_invoices_processed": 0,
    "successful_processes": 0,
    "failed_processes": 0,
    "average_processing_time": 0,
    "api_calls": 0,
    "api_errors": 0
}

def log_metrics(result, processing_time):
    """Log processing metrics"""
    METRICS["total_invoices_processed"] += 1
    if result.get("success"):
        METRICS["successful_processes"] += 1
    else:
        METRICS["failed_processes"] += 1
    
    METRICS["average_processing_time"] = (
        (METRICS["average_processing_time"] * 
         (METRICS["total_invoices_processed"] - 1) +
         processing_time) /
        METRICS["total_invoices_processed"]
    )
```

### Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

invoice_processed_total = Counter(
    'invoice_processed_total',
    'Total invoices processed',
    ['status']
)

invoice_processing_seconds = Histogram(
    'invoice_processing_seconds',
    'Time spent processing invoice',
    buckets=[1, 2, 5, 10, 30]
)

processing_queue_length = Gauge(
    'processing_queue_length',
    'Current number of invoices in queue'
)
```

### Logging Configuration

```python
import logging
import logging.handlers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/invoice_processor.log'),
        logging.StreamHandler()
    ]
)

# Rotate logs
log_handler = logging.handlers.RotatingFileHandler(
    'logs/invoice_processor.log',
    maxBytes=10485760,  # 10MB
    backupCount=10
)
```

### Alert Rules

```yaml
# prometheus-rules.yml
groups:
  - name: invoice_processor
    rules:
      - alert: HighErrorRate
        expr: rate(invoice_processed_total{status="error"}[5m]) > 0.1
        for: 5m
        annotations:
          summary: "High error rate in invoice processing"
      
      - alert: ProcessingQueueBacklog
        expr: processing_queue_length > 100
        for: 10m
        annotations:
          summary: "Invoice processing queue building up"
      
      - alert: SlowProcessing
        expr: invoice_processing_seconds_bucket{le="5"} < 0.5
        for: 15m
        annotations:
          summary: "Invoice processing taking longer than expected"
```

## Security Best Practices

### API Key Management

```bash
# Use secrets manager instead of .env files
# AWS Secrets Manager
export ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value \
  --secret-id invoice-processor/api-key \
  --query SecretString \
  --output text)

# Or use environment variables from container orchestration
# Kubernetes
kubectl create secret generic anthropic-api-key \
  --from-literal=key=$ANTHROPIC_API_KEY

# Azure Key Vault
az keyvault secret set \
  --vault-name myKeyVault \
  --name anthropic-api-key \
  --value sk-ant-...
```

### Network Security

```bash
# Restrict outbound to Anthropic API only
# Use AWS Security Groups
aws ec2 authorize-security-group-egress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# Or use firewall rules for WAF protection
# CloudFront + WAF for DDoS protection
```

### Data Security

```python
# Encrypt sensitive data in transit
import ssl
import requests

session = requests.Session()
session.verify = True  # Always verify SSL certificates

# Don't log sensitive data
def safe_log(data):
    """Log data without exposing API keys or PII"""
    safe_data = data.copy()
    if 'api_key' in safe_data:
        safe_data['api_key'] = '***'
    logging.info(f"Processing: {safe_data}")
```

## Scaling

### Horizontal Scaling

Use a queue-based architecture for high volume:

```python
# Celery + Redis for task queue
from celery import Celery

app = Celery('invoice_processor', broker='redis://localhost:6379')

@app.task
def process_invoice_async(invoice_path):
    """Process invoice asynchronously"""
    result = process_invoice(invoice_path)
    return result

# Usage
process_invoice_async.delay('path/to/invoice.pdf')
```

### Caching Layer

```python
# Redis for caching vendor lookups
import redis

cache = redis.Redis(host='localhost', port=6379, db=0)

def get_vendor_cached(vendor_name):
    # Check cache first
    cached = cache.get(f"vendor:{vendor_name}")
    if cached:
        return json.loads(cached)
    
    # Fetch from database
    result = validate_vendor(vendor_name)
    
    # Cache for 24 hours
    cache.setex(f"vendor:{vendor_name}", 86400, json.dumps(result))
    return result
```

## Backup & Disaster Recovery

### Database Backups

```bash
# Daily backups of invoice data
0 2 * * * pg_dump invoice_db | gzip > /backup/invoice_db_$(date +\%Y\%m\%d).sql.gz

# Retain for 30 days
find /backup -name "invoice_db_*.sql.gz" -mtime +30 -delete

# Test restore
pg_restore -d invoice_db_test /backup/invoice_db_20240115.sql.gz
```

### Replication

```yaml
# PostgreSQL streaming replication
# On primary
wal_level = replica
max_wal_senders = 10

# On standby
standby_mode = 'on'
primary_conninfo = 'host=primary_ip port=5432'
```

## Performance Tuning

### API Batching

```python
def process_invoices_batch(invoice_paths, batch_size=10):
    """Process multiple invoices efficiently"""
    results = []
    
    for i in range(0, len(invoice_paths), batch_size):
        batch = invoice_paths[i:i+batch_size]
        
        # Process in parallel
        from concurrent.futures import ThreadPoolExecutor
        
        with ThreadPoolExecutor(max_workers=batch_size) as executor:
            batch_results = executor.map(process_invoice, batch)
            results.extend(batch_results)
    
    return results
```

### Connection Pooling

```python
# Reuse connections to Claude API
from anthropic import Anthropic

# Create single client instance
client = Anthropic()  # Connection pooling handled by SDK

# Use throughout application
result = client.messages.create(...)  # Reuses connection
```

## Monitoring Dashboard

### Streamlit Metrics Dashboard

```python
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Invoice Processor Metrics", layout="wide")

# Load metrics from database
metrics_df = pd.read_sql(
    "SELECT * FROM processing_metrics WHERE date >= %s",
    conn,
    params=[datetime.now() - timedelta(days=30)]
)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Processed", metrics_df['count'].sum())

with col2:
    success_rate = (metrics_df['success'].sum() / 
                   metrics_df['count'].sum() * 100)
    st.metric("Success Rate", f"{success_rate:.1f}%")

with col3:
    avg_time = metrics_df['processing_time'].mean()
    st.metric("Avg Processing", f"{avg_time:.1f}s")

with col4:
    api_cost = metrics_df['api_cost'].sum()
    st.metric("API Cost", f"${api_cost:.2f}")

# Charts
st.line_chart(metrics_df.set_index('date')[['count', 'success']])
```

## Troubleshooting Production Issues

### High Latency

```bash
# Check API response times
curl -w "@curl-format.txt" https://api.anthropic.com/...

# Monitor network
netstat -i
iftop

# Check logs
tail -f logs/invoice_processor.log | grep "processing_time"
```

### Memory Leaks

```bash
# Monitor memory usage
ps aux | grep python

# Use memory profiler
pip install memory-profiler
python -m memory_profiler invoice_agent.py sample_invoices/invoice_clean.pdf
```

### API Rate Limits

```python
# Implement exponential backoff
import time

def call_with_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = 2 ** attempt
            logging.warning(f"Rate limited, waiting {wait_time}s")
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

## Support & Maintenance

- **Monitoring**: Set up 24/7 monitoring with alerting
- **Updates**: Plan monthly updates for security patches
- **Testing**: Regular testing with production-like data
- **Documentation**: Keep runbooks for common issues
- **SLA**: Define SLA targets (uptime, processing time, etc.)

---

**Ready for production?** Contact Zillion Technologies for full deployment support.
