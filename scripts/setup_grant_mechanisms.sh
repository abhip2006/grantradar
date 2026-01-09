#!/bin/bash
# Setup Grant Mechanisms Feature
# Applies database migration and seeds mechanism data

set -e

echo "=========================================="
echo "GrantRadar Grant Mechanisms Setup"
echo "=========================================="

# Check if we're in the right directory
if [ ! -f "alembic.ini" ]; then
    echo "Error: alembic.ini not found. Are you in the project root?"
    exit 1
fi

echo ""
echo "Step 1: Applying database migration..."
echo "-----------------------------------------"

# Apply the migration
if alembic upgrade 031; then
    echo "✓ Migration 031_add_grant_mechanisms applied successfully"
else
    echo "✗ Migration failed"
    exit 1
fi

echo ""
echo "Step 2: Seeding mechanism data..."
echo "-----------------------------------------"

# Run the seed script
if python -m backend.scripts.seed_mechanisms; then
    echo "✓ Mechanism data seeded successfully"
else
    echo "✗ Seeding failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Grant mechanisms have been successfully configured."
echo ""
echo "Next steps:"
echo "1. Start the application: python main.py"
echo "2. Check mechanisms in database:"
echo "   - GET /mechanisms"
echo "   - GET /mechanisms/{code}"
echo ""
echo "For more information, see:"
echo "  - GRANT_MECHANISMS_SETUP.md (full documentation)"
echo "  - backend/scripts/README.md (script details)"
echo ""
