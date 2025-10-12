# Deployment Guide - Long-Term Financial Market Simulation API

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8+ (recommended: 3.11)
- **Memory**: Minimum 2GB RAM (recommended: 4GB+)
- **Storage**: 500MB+ free space
- **Docker**: Optional but recommended for production

### Data Requirements
- `final_path_statistics_library.csv` (~5,000 simulation paths)
- `param_library.csv` (parameter mappings)
- Both files must be in `Long Term Model/Long Term Model/` directory

## 🚀 Deployment Options

### Option 1: Local Development Setup

#### Windows
```powershell
# Run setup script
powershell -ExecutionPolicy Bypass -File setup.ps1

# Or manual setup:
pip install -r requirements.txt
.\start.bat
```

#### Linux/Mac
```bash
# Make script executable
chmod +x start.sh

# Install and run
pip install -r requirements.txt
./start.sh
```

### Option 2: Docker Deployment (Recommended)

#### Single Container
```bash
# Build the image
docker build -t longterm-financial-api:latest .

# Run the container
docker run -d \
  --name longterm-api \
  -p 8000:8000 \
  -v $(pwd)/Long Term Model:/app/Long Term Model:ro \
  longterm-financial-api:latest
```

#### Docker Compose (Easiest)
```bash
# Start with compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Option 3: Production Deployment

#### Using Docker in Production
```bash
# Build production image
docker build -t longterm-api:prod \
  --build-arg ENV=production .

# Run with restart policy
docker run -d \
  --name longterm-api-prod \
  --restart unless-stopped \
  -p 8000:8000 \
  -v /path/to/data:/app/Long Term Model:ro \
  -e ENV=production \
  -e LOG_LEVEL=warning \
  longterm-api:prod
```

#### Using systemd (Linux)
```bash
# Create service file: /etc/systemd/system/longterm-api.service
[Unit]
Description=Long-Term Financial API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/longterm-api
Environment=PATH=/opt/longterm-api/venv/bin
ExecStart=/opt/longterm-api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target

# Enable and start
sudo systemctl enable longterm-api
sudo systemctl start longterm-api
```

## 🌐 Reverse Proxy Setup

### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Apache Configuration
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/
</VirtualHost>
```

## ☁️ Cloud Deployment

### AWS ECS
```json
{
  "family": "longterm-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "longterm-api",
      "image": "your-registry/longterm-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/longterm-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run
```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: longterm-api
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '10'
    spec:
      containers:
      - image: gcr.io/your-project/longterm-api:latest
        ports:
        - containerPort: 8000
        resources:
          limits:
            memory: 1Gi
            cpu: 1000m
```

### Azure Container Instances
```bash
az container create \
  --resource-group myResourceGroup \
  --name longterm-api \
  --image your-registry/longterm-api:latest \
  --dns-name-label longterm-api \
  --ports 8000 \
  --memory 1 \
  --cpu 1
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Core settings
export ENV=production
export LOG_LEVEL=info
export PORT=8000

# Security (production)
export SECRET_KEY="your-super-secret-key"
export CORS_ORIGINS='["https://your-frontend.com"]'

# Performance
export MAX_PATH_DETAILS=100
export CACHE_SIZE=256
```

### Configuration Files
```bash
# Copy example config
cp .env.example .env

# Edit as needed
vim .env
```

## 📊 Monitoring & Logging

### Health Checks
```bash
# Manual health check
curl http://localhost:8000/health

# Automated monitoring
*/5 * * * * curl -f http://localhost:8000/health || alert_script.sh
```

### Log Management
```bash
# View logs (Docker)
docker logs -f longterm-api

# View logs (systemd)
journalctl -u longterm-api -f

# Log rotation
/var/log/longterm-api/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
}
```

## 🛡️ Security Checklist

- [ ] Use HTTPS in production
- [ ] Set proper CORS origins
- [ ] Use non-root user in containers
- [ ] Keep dependencies updated
- [ ] Monitor for vulnerabilities
- [ ] Use secrets management for sensitive data
- [ ] Enable rate limiting if needed
- [ ] Regular security audits

## 🚨 Troubleshooting

### Common Issues

**Data files not found**
```bash
# Check file structure
ls -la "Long Term Model/Long Term Model/"
# Should show both CSV files
```

**Port already in use**
```bash
# Find process using port 8000
lsof -i :8000
# Kill process or use different port
```

**Permission denied (Docker)**
```bash
# Fix file permissions
sudo chown -R 1000:1000 "Long Term Model/"
```

**Memory issues**
```bash
# Monitor memory usage
docker stats longterm-api
# Increase container memory if needed
```

### Performance Optimization

```bash
# Use production WSGI server
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Optimize Docker build
docker build --no-cache -t longterm-api:optimized .

# Enable compression
# Add nginx gzip compression for API responses
```

## 📞 Support

### Health Monitoring
- Health endpoint: `GET /health`
- API docs: `GET /docs`
- Metrics: Custom implementation needed

### Backup Strategy
```bash
# Backup data files
tar -czf backup-$(date +%Y%m%d).tar.gz "Long Term Model/"

# Automated backup
0 2 * * * /opt/backup-script.sh
```

### Update Procedure
```bash
# Pull new image
docker pull your-registry/longterm-api:latest

# Rolling update
docker-compose up -d

# Verify deployment
curl http://localhost:8000/health
```

---

**For additional support or customization, contact the development team.**
