#!/bin/bash

# GrantRadar SSL Setup Script
# This script helps generate SSL certificates for development and production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SSL_DIR="./nginx/ssl"
DOMAIN="${DOMAIN:-localhost}"
COUNTRY="${COUNTRY:-US}"
STATE="${STATE:-California}"
CITY="${CITY:-San Francisco}"
ORG="${ORG:-GrantRadar}"
DAYS="${DAYS:-365}"

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}  GrantRadar SSL Certificate Setup${NC}"
    echo -e "${BLUE}============================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if OpenSSL is installed
check_openssl() {
    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL is not installed. Please install it first."
        exit 1
    fi
    print_success "OpenSSL found: $(openssl version)"
}

# Create SSL directory
create_ssl_dir() {
    if [ ! -d "$SSL_DIR" ]; then
        mkdir -p "$SSL_DIR"
        print_success "Created SSL directory: $SSL_DIR"
    else
        print_info "SSL directory already exists: $SSL_DIR"
    fi
}

# Generate Diffie-Hellman parameters
generate_dhparam() {
    local dhparam_file="$SSL_DIR/dhparam.pem"

    if [ -f "$dhparam_file" ]; then
        print_warning "dhparam.pem already exists. Skipping generation."
        return 0
    fi

    print_info "Generating Diffie-Hellman parameters (this may take a while)..."
    openssl dhparam -out "$dhparam_file" 2048
    print_success "Generated dhparam.pem"
}

# Generate self-signed certificate for development
generate_self_signed() {
    local key_file="$SSL_DIR/privkey.pem"
    local cert_file="$SSL_DIR/fullchain.pem"

    if [ -f "$key_file" ] && [ -f "$cert_file" ]; then
        print_warning "Certificates already exist. Use --force to regenerate."
        return 0
    fi

    print_info "Generating self-signed certificate for: $DOMAIN"

    # Generate private key and certificate
    openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
        -keyout "$key_file" \
        -out "$cert_file" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/CN=$DOMAIN" \
        -addext "subjectAltName=DNS:$DOMAIN,DNS:*.$DOMAIN,DNS:localhost,IP:127.0.0.1"

    # Set appropriate permissions
    chmod 600 "$key_file"
    chmod 644 "$cert_file"

    print_success "Generated self-signed certificate"
    print_info "  Private key: $key_file"
    print_info "  Certificate: $cert_file"
    print_warning "This certificate is for development only!"
}

# Generate Certificate Signing Request (CSR) for production
generate_csr() {
    local key_file="$SSL_DIR/privkey.pem"
    local csr_file="$SSL_DIR/request.csr"

    print_info "Generating CSR for production certificate..."

    # Generate private key if it doesn't exist
    if [ ! -f "$key_file" ]; then
        openssl genrsa -out "$key_file" 4096
        chmod 600 "$key_file"
        print_success "Generated private key"
    fi

    # Generate CSR
    openssl req -new -key "$key_file" -out "$csr_file" \
        -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/CN=$DOMAIN"

    print_success "Generated CSR: $csr_file"
    print_info "Submit this CSR to your Certificate Authority"
}

# Setup Let's Encrypt with certbot
setup_letsencrypt() {
    local email="${1:-admin@$DOMAIN}"

    print_info "Setting up Let's Encrypt certificate for: $DOMAIN"
    print_info "Email: $email"

    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        print_error "Certbot is not installed."
        print_info "Install with:"
        print_info "  Ubuntu/Debian: sudo apt-get install certbot"
        print_info "  macOS: brew install certbot"
        print_info "  Or use the certbot Docker container (see docker-compose.prod.yml)"
        exit 1
    fi

    # Request certificate using webroot method
    print_info "Requesting certificate..."
    sudo certbot certonly --webroot \
        -w /var/www/certbot \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --email "$email" \
        --agree-tos \
        --non-interactive

    # Create symlinks to the Let's Encrypt certificates
    print_info "Creating symlinks to certificates..."
    ln -sf "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$SSL_DIR/fullchain.pem"
    ln -sf "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$SSL_DIR/privkey.pem"

    print_success "Let's Encrypt certificate installed!"
    print_info "Certificates are at: /etc/letsencrypt/live/$DOMAIN/"
    print_info "Auto-renewal is handled by certbot's cron job"
}

# Verify certificate
verify_certificate() {
    local cert_file="$SSL_DIR/fullchain.pem"

    if [ ! -f "$cert_file" ]; then
        print_error "Certificate not found: $cert_file"
        exit 1
    fi

    print_info "Certificate Information:"
    echo ""
    openssl x509 -in "$cert_file" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After :)"
    echo ""

    # Check expiration
    local expiry=$(openssl x509 -in "$cert_file" -enddate -noout | cut -d= -f2)
    local expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$expiry" +%s 2>/dev/null)
    local now_epoch=$(date +%s)
    local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

    if [ $days_left -lt 0 ]; then
        print_error "Certificate has EXPIRED!"
    elif [ $days_left -lt 30 ]; then
        print_warning "Certificate expires in $days_left days"
    else
        print_success "Certificate valid for $days_left more days"
    fi
}

# Show usage
usage() {
    echo "Usage: $0 [command] [options]"
    echo ""
    echo "Commands:"
    echo "  self-signed    Generate self-signed certificate (development)"
    echo "  csr            Generate Certificate Signing Request (production)"
    echo "  letsencrypt    Setup Let's Encrypt certificate (production)"
    echo "  verify         Verify existing certificate"
    echo "  dhparam        Generate Diffie-Hellman parameters"
    echo "  all            Generate self-signed cert and dhparam (development)"
    echo ""
    echo "Options:"
    echo "  --domain       Domain name (default: localhost)"
    echo "  --email        Email for Let's Encrypt (default: admin@domain)"
    echo "  --force        Force regenerate existing certificates"
    echo "  --help         Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  DOMAIN         Domain name"
    echo "  COUNTRY        Country code (default: US)"
    echo "  STATE          State/Province (default: California)"
    echo "  CITY           City (default: San Francisco)"
    echo "  ORG            Organization name (default: GrantRadar)"
    echo "  DAYS           Certificate validity in days (default: 365)"
    echo ""
    echo "Examples:"
    echo "  $0 self-signed                          # Development setup"
    echo "  $0 self-signed --domain=myapp.local     # Custom domain"
    echo "  $0 letsencrypt --domain=grantradar.com  # Production with Let's Encrypt"
    echo "  $0 all                                  # Full development setup"
}

# Parse command line arguments
FORCE=false
EMAIL=""

parse_args() {
    for arg in "$@"; do
        case $arg in
            --domain=*)
                DOMAIN="${arg#*=}"
                ;;
            --email=*)
                EMAIL="${arg#*=}"
                ;;
            --force)
                FORCE=true
                ;;
            --help)
                usage
                exit 0
                ;;
        esac
    done
}

# Main script
main() {
    print_header
    check_openssl
    create_ssl_dir

    parse_args "$@"

    if [ "$FORCE" = true ] && [ -d "$SSL_DIR" ]; then
        print_warning "Force mode: removing existing certificates..."
        rm -f "$SSL_DIR"/*.pem "$SSL_DIR"/*.csr
    fi

    case "${1:-all}" in
        self-signed)
            generate_self_signed
            ;;
        csr)
            generate_csr
            ;;
        letsencrypt)
            setup_letsencrypt "$EMAIL"
            ;;
        verify)
            verify_certificate
            ;;
        dhparam)
            generate_dhparam
            ;;
        all)
            generate_self_signed
            generate_dhparam
            print_success "Development SSL setup complete!"
            ;;
        --*)
            # Handle case where only options are passed
            generate_self_signed
            generate_dhparam
            print_success "Development SSL setup complete!"
            ;;
        *)
            usage
            exit 1
            ;;
    esac

    echo ""
    print_info "Next steps:"
    echo "  1. Update docker-compose.prod.yml with SSL volumes"
    echo "  2. Uncomment HTTPS redirect in nginx/nginx.conf"
    echo "  3. Run: docker-compose -f docker-compose.prod.yml up -d"
    echo ""
}

# Run main function
main "$@"
