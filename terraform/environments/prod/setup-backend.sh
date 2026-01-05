#!/bin/bash
# ============================================
# Script para configurar Remote State Backend
# ============================================
# Este script crea los recursos necesarios para usar
# Terraform Remote State en S3 con DynamoDB locking

set -e

REGION="${AWS_REGION:-us-west-2}"
PROFILE="${AWS_PROFILE:-default}"
BUCKET_NAME="landa-terraform-state-prod"
DYNAMODB_TABLE="landa-terraform-locks"

echo "🚀 Configurando Remote State Backend para Terraform"
echo "Region: $REGION"
echo "Profile: $PROFILE"
echo ""

# Verificar que AWS CLI está configurado
if ! aws --profile "$PROFILE" sts get-caller-identity &>/dev/null; then
    echo "❌ Error: AWS CLI no está configurado o el profile '$PROFILE' no existe"
    echo "   Ejecuta: aws configure --profile $PROFILE"
    exit 1
fi

# Crear bucket S3
echo "📦 Creando bucket S3: $BUCKET_NAME"
if aws s3 ls "s3://$BUCKET_NAME" --profile "$PROFILE" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://$BUCKET_NAME" --region "$REGION" --profile "$PROFILE"
    echo "✅ Bucket creado"
else
    echo "ℹ️  Bucket ya existe"
fi

# Habilitar versionado
echo "🔄 Habilitando versionado en bucket..."
aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled \
    --profile "$PROFILE"
echo "✅ Versionado habilitado"

# Habilitar encriptación
echo "🔐 Habilitando encriptación en bucket..."
aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
        "Rules": [{
            "ApplyServerSideEncryptionByDefault": {
                "SSEAlgorithm": "AES256"
            }
        }]
    }' \
    --profile "$PROFILE"
echo "✅ Encriptación habilitada"

# Bloquear acceso público
echo "🔒 Bloqueando acceso público..."
aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
    --profile "$PROFILE"
echo "✅ Acceso público bloqueado"

# Crear tabla DynamoDB para state locking
echo "🔐 Creando tabla DynamoDB: $DYNAMODB_TABLE"
if ! aws dynamodb describe-table --table-name "$DYNAMODB_TABLE" --profile "$PROFILE" &>/dev/null; then
    aws dynamodb create-table \
        --table-name "$DYNAMODB_TABLE" \
        --attribute-definitions AttributeName=LockID,AttributeType=S \
        --key-schema AttributeName=LockID,KeyType=HASH \
        --billing-mode PAY_PER_REQUEST \
        --region "$REGION" \
        --profile "$PROFILE" \
        --tags Key=Project,Value=landa-beauty-supply Key=ManagedBy,Value=terraform Key=Environment,Value=production
    
    echo "⏳ Esperando que la tabla esté activa..."
    aws dynamodb wait table-exists \
        --table-name "$DYNAMODB_TABLE" \
        --profile "$PROFILE"
    echo "✅ Tabla creada y activa"
else
    echo "ℹ️  Tabla ya existe"
fi

echo ""
echo "✅ Configuración completada!"
echo ""
echo "📝 Próximos pasos:"
echo "1. Edita terraform/environments/prod/main.tf"
echo "2. Descomenta el bloque 'backend \"s3\"'"
echo "3. Ejecuta: terraform init -migrate-state"
echo ""
echo "Bucket S3: s3://$BUCKET_NAME"
echo "Tabla DynamoDB: $DYNAMODB_TABLE"

