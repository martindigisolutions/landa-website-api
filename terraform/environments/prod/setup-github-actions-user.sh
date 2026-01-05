#!/bin/bash
# ============================================
# Script para configurar usuario IAM para GitHub Actions
# ============================================
# Este script crea un usuario IAM con permisos para hacer push a ECR
# para que GitHub Actions pueda desplegar a producción

set -e

REGION="${AWS_REGION:-us-west-2}"
PROFILE="${AWS_PROFILE:-default}"
USER_NAME="github-actions-ecr"
POLICY_NAME="GitHubActionsECRPush"

echo "🔐 Configurando usuario IAM para GitHub Actions"
echo "Region: $REGION"
echo "Profile: $PROFILE"
echo ""

# Verificar que AWS CLI está configurado
if ! aws --profile "$PROFILE" sts get-caller-identity &>/dev/null; then
    echo "❌ Error: AWS CLI no está configurado o el profile '$PROFILE' no existe"
    exit 1
fi

# Crear política IAM
echo "📝 Creando política IAM: $POLICY_NAME"
POLICY_JSON=$(cat <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ECRAuth",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "ECRPush",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:PutImage",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload"
      ],
      "Resource": "arn:aws:ecr:us-west-2:*:repository/landa-beauty-api*"
    }
  ]
}
EOF
)

# Verificar si la política ya existe
if aws iam get-policy --policy-arn "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text --profile "$PROFILE"):policy/$POLICY_NAME" --profile "$PROFILE" &>/dev/null; then
    echo "ℹ️  Política ya existe, actualizando..."
    POLICY_ARN=$(aws iam get-policy --policy-arn "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text --profile "$PROFILE"):policy/$POLICY_NAME" --profile "$PROFILE" --query 'Policy.Arn' --output text)
    
    # Crear nueva versión de la política
    aws iam create-policy-version \
        --policy-arn "$POLICY_ARN" \
        --policy-document "$POLICY_JSON" \
        --set-as-default \
        --profile "$PROFILE" > /dev/null
    echo "✅ Política actualizada"
else
    # Crear nueva política
    POLICY_ARN=$(aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document "$POLICY_JSON" \
        --description "Policy for GitHub Actions to push images to ECR" \
        --profile "$PROFILE" \
        --query 'Policy.Arn' --output text)
    echo "✅ Política creada: $POLICY_ARN"
fi

# Crear usuario IAM
echo ""
echo "👤 Creando usuario IAM: $USER_NAME"
if aws iam get-user --user-name "$USER_NAME" --profile "$PROFILE" &>/dev/null; then
    echo "ℹ️  Usuario ya existe"
else
    aws iam create-user \
        --user-name "$USER_NAME" \
        --tags Key=Project,Value=landa-beauty-supply Key=ManagedBy,Value=terraform Key=Environment,Value=production Key=Purpose,Value=github-actions \
        --profile "$PROFILE" > /dev/null
    echo "✅ Usuario creado"
fi

# Adjuntar política al usuario
echo ""
echo "🔗 Adjuntando política al usuario..."
USER_POLICIES=$(aws iam list-attached-user-policies --user-name "$USER_NAME" --profile "$PROFILE" --query 'AttachedPolicies[?PolicyArn==`'"$POLICY_ARN"`]' --output text)

if [ -z "$USER_POLICIES" ]; then
    aws iam attach-user-policy \
        --user-name "$USER_NAME" \
        --policy-arn "$POLICY_ARN" \
        --profile "$PROFILE"
    echo "✅ Política adjuntada"
else
    echo "ℹ️  Política ya está adjuntada"
fi

# Crear access keys
echo ""
echo "🔑 Creando Access Keys..."
echo ""
echo "⚠️  IMPORTANTE: Si el usuario ya tiene 2 access keys, necesitarás eliminar una primero."
echo "   Verifica con: aws iam list-access-keys --user-name $USER_NAME --profile $PROFILE"
echo ""

read -p "¿Crear nuevas access keys? (s/n): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[SsYy]$ ]]; then
    ACCESS_KEY_OUTPUT=$(aws iam create-access-key \
        --user-name "$USER_NAME" \
        --profile "$PROFILE")
    
    ACCESS_KEY_ID=$(echo "$ACCESS_KEY_OUTPUT" | grep -oP '"AccessKeyId":\s*"\K[^"]+')
    SECRET_ACCESS_KEY=$(echo "$ACCESS_KEY_OUTPUT" | grep -oP '"SecretAccessKey":\s*"\K[^"]+')
    
    echo ""
    echo "✅ Access Keys creadas!"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  🔐 CREDENCIALES PARA GITHUB SECRETS"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "PROD_AWS_ACCOUNT_ID = 553938786984"
    echo "PROD_AWS_ACCESS_KEY_ID = $ACCESS_KEY_ID"
    echo "PROD_AWS_SECRET_ACCESS_KEY = $SECRET_ACCESS_KEY"
    echo "PROD_ECR_REPOSITORY = landa-beauty-api-api"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "📝 Próximos pasos:"
    echo "1. Ve a GitHub → Settings → Secrets → Actions"
    echo "2. Agrega los siguientes secrets:"
    echo "   - PROD_AWS_ACCOUNT_ID = 553938786984"
    echo "   - PROD_AWS_ACCESS_KEY_ID = $ACCESS_KEY_ID"
    echo "   - PROD_AWS_SECRET_ACCESS_KEY = $SECRET_ACCESS_KEY"
    echo "   - PROD_ECR_REPOSITORY = landa-beauty-api-api"
    echo ""
    echo "⚠️  GUARDA ESTAS CREDENCIALES EN UN LUGAR SEGURO!"
    echo "   No podrás ver el Secret Access Key de nuevo."
    echo ""
else
    echo "ℹ️  Saltando creación de access keys"
    echo ""
    echo "Para crear access keys manualmente:"
    echo "  aws iam create-access-key --user-name $USER_NAME --profile $PROFILE"
fi

echo ""
echo "✅ Configuración completada!"

