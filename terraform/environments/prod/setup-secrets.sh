#!/bin/bash
# ============================================
# Script para configurar Secrets en Secrets Manager
# ============================================
# Este script ayuda a configurar los secrets después de crear la infraestructura

set -e

PROFILE="${AWS_PROFILE:-default}"
PROJECT_NAME="${PROJECT_NAME:-landa-beauty-api}"

echo "🔐 Configurando Secrets en AWS Secrets Manager"
echo "Profile: $PROFILE"
echo "Project: $PROJECT_NAME"
echo ""

# Verificar que AWS CLI está configurado
if ! aws --profile "$PROFILE" sts get-caller-identity &>/dev/null; then
    echo "❌ Error: AWS CLI no está configurado o el profile '$PROFILE' no existe"
    exit 1
fi

SECRET_NAME="$PROJECT_NAME/app-secrets"

echo "📝 Configurando secret: $SECRET_NAME"
echo ""
echo "Por favor, ingresa los siguientes valores:"
echo ""

read -sp "SECRET_KEY (JWT secret, 32+ caracteres): " SECRET_KEY
echo ""
read -sp "STRIPE_SECRET_KEY: " STRIPE_SECRET_KEY
echo ""
read -sp "STRIPE_WEBHOOK_SECRET: " STRIPE_WEBHOOK_SECRET
echo ""

# Crear JSON con los secrets
SECRET_JSON=$(cat <<EOF
{
  "SECRET_KEY": "$SECRET_KEY",
  "STRIPE_SECRET_KEY": "$STRIPE_SECRET_KEY",
  "STRIPE_WEBHOOK_SECRET": "$STRIPE_WEBHOOK_SECRET"
}
EOF
)

# Guardar en un archivo temporal
TEMP_FILE=$(mktemp)
echo "$SECRET_JSON" > "$TEMP_FILE"

# Verificar si el secret existe
if aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --profile "$PROFILE" &>/dev/null; then
    echo "ℹ️  Secret ya existe, actualizando..."
    aws secretsmanager put-secret-value \
        --secret-id "$SECRET_NAME" \
        --secret-string file://"$TEMP_FILE" \
        --profile "$PROFILE"
    echo "✅ Secret actualizado"
else
    echo "❌ Error: El secret '$SECRET_NAME' no existe."
    echo "   Asegúrate de ejecutar 'terraform apply' primero para crear el secret."
    rm "$TEMP_FILE"
    exit 1
fi

# Limpiar archivo temporal
rm "$TEMP_FILE"

echo ""
echo "✅ Secrets configurados correctamente!"
echo ""
echo "📝 Nota: Para usar estos secrets en App Runner,"
echo "   agrega 'runtime_environment_secrets' en el módulo apprunner:"
echo ""
echo "   runtime_environment_secrets = {"
echo "     SECRET_KEY           = aws_secretsmanager_secret.app_secrets.arn"
echo "     STRIPE_SECRET_KEY     = aws_secretsmanager_secret.app_secrets.arn"
echo "     STRIPE_WEBHOOK_SECRET = aws_secretsmanager_secret.app_secrets.arn"
echo "   }"
echo ""
echo "   O usa el mismo ARN para todos si están en el mismo secret JSON."

