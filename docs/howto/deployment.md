# Deployment

Deploy QuickDev applications to VPS nodes with confidence.

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing (`pytest`)
- [ ] Configuration reviewed (`conf/site.yaml`)
- [ ] Secrets prepared (production `.env`)
- [ ] Database backups tested
- [ ] SSL certificates obtained
- [ ] Apache configuration tested locally

### Deployment

- [ ] Server provisioned and secured
- [ ] Python and Apache installed
- [ ] QuickDev site created (`qdstart`)
- [ ] Dependencies installed
- [ ] Application code deployed
- [ ] Database initialized/migrated
- [ ] Apache configuration generated
- [ ] Site enabled and tested

### Post-Deployment

- [ ] Health check passing
- [ ] Logs monitored
- [ ] Backup cron jobs configured
- [ ] Monitoring configured
- [ ] Documentation updated

## Quick Deployment Guide

### 1. Provision Server

```bash
# Example: Digital Ocean Ubuntu 22.04 LTS droplet
# - 2GB RAM minimum
# - 1 CPU
# - 50GB storage

# Connect via SSH
ssh root@your-server-ip
```

### 2. Install Dependencies

```bash
# Update system
apt update && apt upgrade -y

# Install Python and Apache
apt install -y python3 python3-pip python3-venv
apt install -y apache2 libapache2-mod-wsgi-py3

# Enable required Apache modules
a2enmod wsgi
a2enmod ssl
a2enmod headers
a2enmod rewrite

# Install system utilities
apt install -y git curl
```

### 3. Create QuickDev Site

```bash
# Create site directory
python3 -m pip install qdbase
python3 -m qdutils.qdstart /var/www/mysite --acronym mysite

cd /var/www/mysite
source venv/bin/activate
```

### 4. Install Application Dependencies

```bash
# Install QuickDev packages
pip install qdflask qdimages qdcomments

# Install your application requirements
pip install -r requirements.txt
```

### 5. Configure Site

```bash
# Create production .env
cat > conf/.env << EOF
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
ADMIN_PASSWORD=your-secure-admin-password
SENDGRID_API_KEY=your-sendgrid-api-key
DATABASE_URL=postgresql://user:pass@localhost/mysite
EOF

chmod 600 conf/.env
```

Edit `conf/site.yaml`:

```yaml
site_name: mysite
acronym: mysite
features:
  - authentication
  - image_upload
  - comments
apache:
  server_name: mysite.example.com
  ssl_enabled: true
```

### 6. Deploy Application Code

```bash
# Option 1: Git clone
git clone https://github.com/yourusername/mysite-app.git app
cd app

# Option 2: SCP/rsync
rsync -avz local/app/ root@server:/var/www/mysite/app/
```

### 7. Initialize Database

```bash
cd /var/www/mysite
source venv/bin/activate
python app/init_db.py
```

### 8. Generate Apache Configuration

```bash
python -m qdutils.qdapache /var/www/mysite
```

Review generated config:

```bash
cat /etc/apache2/sites-available/mysite.conf
```

### 9. Enable Site

```bash
# Enable site
a2ensite mysite

# Disable default site (optional)
a2dissite 000-default

# Test configuration
apache2ctl configtest

# Reload Apache
systemctl reload apache2
```

### 10. Verify Deployment

```bash
# Check Apache status
systemctl status apache2

# Test site
curl https://mysite.example.com/

# Check logs
tail -f /var/log/apache2/mysite-error.log
```

## Environment-Specific Configuration

### Development

```yaml
# Local development
DEBUG=True
FLASK_ENV=development
DATABASE_URL=sqlite:///dev.db
```

### Staging

```yaml
# Staging server
DEBUG=False
FLASK_ENV=staging
DATABASE_URL=postgresql://...staging-db
LOG_LEVEL=DEBUG
```

### Production

```yaml
# Production server
DEBUG=False
FLASK_ENV=production
DATABASE_URL=postgresql://...prod-db
LOG_LEVEL=WARNING
REQUIRE_HTTPS=True
```

## Database Migration

### SQLite to PostgreSQL

```bash
# Install PostgreSQL
apt install -y postgresql postgresql-contrib

# Create database
sudo -u postgres createdb mysite
sudo -u postgres createuser mysite_user

# Update .env
DATABASE_URL=postgresql://mysite_user:password@localhost/mysite

# Migrate data (if needed)
# Use pg_dump, custom migration scripts, or tools like pgloader
```

## SSL/HTTPS with Let's Encrypt

```bash
# Install Certbot
apt install -y certbot python3-certbot-apache

# Obtain certificate
certbot --apache -d mysite.example.com -d www.mysite.example.com

# Certbot automatically:
# - Obtains certificate
# - Modifies Apache config
# - Sets up auto-renewal

# Test auto-renewal
certbot renew --dry-run
```

Update `site.yaml`:

```yaml
apache:
  ssl_enabled: true
  ssl_certificate: /etc/letsencrypt/live/mysite.example.com/fullchain.pem
  ssl_certificate_key: /etc/letsencrypt/live/mysite.example.com/privkey.pem
  require_https: true
```

## Security Hardening

### Firewall (UFW)

```bash
# Enable UFW
ufw default deny incoming
ufw default allow outgoing

# Allow SSH, HTTP, HTTPS
ufw allow ssh
ufw allow http
ufw allow https

ufw enable
```

### File Permissions

```bash
# Set ownership
chown -R www-data:www-data /var/www/mysite

# Secure permissions
chmod 755 /var/www/mysite
chmod 600 /var/www/mysite/conf/.env
chmod 644 /var/www/mysite/conf/site.yaml
```

### SSH Hardening

```bash
# Disable root login
sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Disable password authentication (use SSH keys)
sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config

systemctl restart sshd
```

## Monitoring and Logs

### Log Locations

```bash
# Apache logs
/var/log/apache2/mysite-error.log
/var/log/apache2/mysite-access.log

# Application logs (if configured)
/var/www/mysite/logs/mysite.log
```

### Log Rotation

```bash
# Create logrotate config
cat > /etc/logrotate.d/mysite << EOF
/var/www/mysite/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
}
EOF
```

### Basic Monitoring

```bash
# Monitor Apache
systemctl status apache2

# Monitor disk space
df -h

# Monitor memory
free -h

# Monitor processes
htop
```

## Backup Strategy

### Database Backup

```bash
# Create backup script
cat > /usr/local/bin/backup-mysite-db << 'EOF'
#!/bin/bash
BACKUP_DIR=/var/backups/mysite
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
pg_dump mysite > $BACKUP_DIR/mysite_$DATE.sql
find $BACKUP_DIR -name "*.sql" -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup-mysite-db

# Add to cron (daily at 2am)
echo "0 2 * * * /usr/local/bin/backup-mysite-db" | crontab -
```

### Configuration Backup

```bash
# Backup conf/ directory
tar czf /var/backups/mysite-conf-$(date +%Y%m%d).tar.gz /var/www/mysite/conf/

# Exclude .env (store securely elsewhere)
tar czf backup.tar.gz --exclude='.env' conf/
```

## Troubleshooting

### "503 Service Unavailable"

Check Apache error log:

```bash
tail -f /var/log/apache2/mysite-error.log
```

Common causes:

- WSGI application crashed
- Python import errors
- Database connection failed

### "Permission Denied"

Fix ownership:

```bash
chown -R www-data:www-data /var/www/mysite
```

### "Internal Server Error"

Enable detailed error pages (development only):

```python
# app.py
app.config['DEBUG'] = True
```

Check logs for stack traces.

### Database Connection Failed

Verify database credentials:

```bash
# Test PostgreSQL connection
psql -U mysite_user -d mysite -h localhost

# Check .env file
cat /var/www/mysite/conf/.env | grep DATABASE
```

## Rollback Procedure

If deployment fails:

```bash
# 1. Disable new site
a2dissite mysite

# 2. Restore previous code
cd /var/www/mysite/app
git checkout previous-version

# 3. Restore database (if needed)
psql mysite < /var/backups/mysite/backup.sql

# 4. Reload Apache
systemctl reload apache2

# 5. Verify
curl https://mysite.example.com/
```

## Continuous Deployment

### Simple Git Pull

```bash
# On server
cd /var/www/mysite/app
git pull origin main
systemctl reload apache2
```

### Automated with GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to server
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.HOST }}
          username: deploy
          key: ${{ secrets.SSH_KEY }}
          script: |
            cd /var/www/mysite/app
            git pull
            source ../venv/bin/activate
            pip install -r requirements.txt
            sudo systemctl reload apache2
```

## Performance Optimization

### Apache Configuration

```apache
# Enable compression
<IfModule mod_deflate.c>
    AddOutputFilterByType DEFLATE text/html text/plain text/xml text/css text/javascript application/javascript
</IfModule>

# Browser caching
<IfModule mod_expires.c>
    ExpiresActive On
    ExpiresByType image/jpg "access plus 1 year"
    ExpiresByType image/jpeg "access plus 1 year"
    ExpiresByType image/png "access plus 1 year"
    ExpiresByType text/css "access plus 1 month"
    ExpiresByType application/javascript "access plus 1 month"
</IfModule>
```

### WSGI Configuration

```apache
# Increase processes/threads
WSGIDaemonProcess mysite processes=2 threads=15 python-home=/var/www/mysite/mysite.venv
```

## Next Steps

- **[Apache Configuration](apache-config.md)** - Advanced Apache configuration
- **[Secrets Management](secrets.md)** - Secure credential management
- **[Site Setup](site-setup.md)** - Understanding site structure

## Reference

- [Digital Ocean - Deploy Flask Apps](https://www.digitalocean.com/community/tutorials/how-to-deploy-a-flask-application-on-an-ubuntu-vps)
- [Apache mod_wsgi Documentation](https://modwsgi.readthedocs.io/)
- [Let's Encrypt](https://letsencrypt.org/)
