
import os


CERTPATH = os.getenv('SF_CERT_PATH', None)
VERIFY_CERTS = os.getenv('SF_VERIFY_CERTS', 'True').lower() in ['true', '1', 'yes']
CONNECT_TIMEOUT = int(os.getenv('SF_CONNECT_TIMEOUT', '10'))
READ_TIMEOUT = int(os.getenv('SF_READ_TIMEOUT', '60'))
RETRIES = int(os.getenv('SF_RETRIES', '3'))