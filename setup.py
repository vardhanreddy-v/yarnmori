"""One-time configuration: python setup.py (never overwrites an existing .env)."""
from pathlib import Path
import secrets
from getpass import getpass
path=Path(__file__).resolve().parent/'.env'
if path.exists():
    raise SystemExit('.env already exists. Edit it to change your settings.')
password=getpass('Choose an owner password (at least 12 characters): ')
if len(password)<12 or any(c in password for c in '\n\r\"\''):
    raise SystemExit('Use at least 12 characters without quotes or newlines.')
path.write_text('ADMIN_USER=owner\nADMIN_PASSWORD='+password+'\nSECRET_KEY='+secrets.token_urlsafe(48)+'\nPRODUCTION=false\n',encoding='utf-8')
path.chmod(0o600)
print('Configured. Start with: python -m uvicorn app:app --host 127.0.0.1 --port 8000')
