# 🔐 Configuración de GitHub Secrets para Producción

## ✅ Usuario IAM Configurado

Se ha creado exitosamente:
- **Usuario IAM**: `github-actions-ecr`
- **Política**: `GitHubActionsECRPush`
- **Access Keys**: Creadas

---

## 📝 Secrets para Configurar en GitHub

Ve a tu repositorio en GitHub y configura los siguientes secrets:

**URL**: `https://github.com/martindigisolutions/landa-website-api/settings/secrets/actions`

### Secrets Requeridos:

| Secret Name | Valor |
|-------------|-------|
| `PROD_AWS_ACCOUNT_ID` | `553938786984` |
| `PROD_AWS_ACCESS_KEY_ID` | `[OBTENER DEL COMANDO AWS CLI]` |
| `PROD_AWS_SECRET_ACCESS_KEY` | `[OBTENER DEL COMANDO AWS CLI]` |
| `PROD_ECR_REPOSITORY` | `landa-beauty-api` |

⚠️ **Las credenciales reales NO deben estar en este archivo por seguridad.**
Para obtenerlas, ejecuta: `aws iam list-access-keys --user-name github-actions-ecr`

---

## 🚀 Pasos para Configurar en GitHub

1. **Ve a tu repositorio en GitHub**
   - URL: https://github.com/martindigisolutions/landa-website-api

2. **Navega a Settings → Secrets and variables → Actions**
   - O directamente: https://github.com/martindigisolutions/landa-website-api/settings/secrets/actions

3. **Haz clic en "New repository secret"** para cada uno de los secrets:

   **Secret 1:**
   - Name: `PROD_AWS_ACCOUNT_ID`
   - Secret: `553938786984`

   **Secret 2:**
   - Name: `PROD_AWS_ACCESS_KEY_ID`
   - Secret: `[Obtener ejecutando: aws iam list-access-keys --user-name github-actions-ecr]`

   **Secret 3:**
   - Name: `PROD_AWS_SECRET_ACCESS_KEY`
   - Secret: `[Obtener ejecutando: aws iam create-access-key --user-name github-actions-ecr]`
   - ⚠️ **Nota**: Si el usuario ya tiene access keys, necesitarás crear una nueva o eliminar una existente primero.

   **Secret 4:**
   - Name: `PROD_ECR_REPOSITORY`
   - Secret: `landa-beauty-api`

4. **Verifica que todos los secrets estén configurados:**
   - Deberías ver 4 secrets con el prefijo `PROD_`

---

## ✅ Verificación

Una vez configurados los secrets, puedes verificar que funcionan:

1. **Haz un push a la rama `main`** (o merge un PR a main)
2. **Ve a Actions** en GitHub para ver el workflow ejecutándose
3. **El workflow debería:**
   - Buildear la imagen Docker
   - Hacer push a ECR de producción
   - App Runner detectará automáticamente la nueva imagen y desplegará

---

## 🔒 Seguridad

⚠️ **IMPORTANTE**: 
- **NO** compartas estas credenciales públicamente
- **NO** las commitees al repositorio
- Si las credenciales se comprometen, elimínalas inmediatamente y crea nuevas

Para obtener las credenciales:
```bash
# Listar access keys existentes
aws iam list-access-keys --user-name github-actions-ecr

# Si no hay access keys, crear una nueva
aws iam create-access-key --user-name github-actions-ecr
```

Para rotar las credenciales:
```bash
# Eliminar access key antigua (reemplaza ACCESS_KEY_ID con el ID real)
aws iam delete-access-key --user-name github-actions-ecr --access-key-id <ACCESS_KEY_ID>

# Crear nueva access key
aws iam create-access-key --user-name github-actions-ecr
```

---

## 📚 Referencias

- [GitHub Actions Secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
- [AWS IAM Best Practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html)
- Workflow: `.github/workflows/deploy.yml`

---

*Configurado el: 2026-01-05*
*Usuario IAM: github-actions-ecr*
*Cuenta AWS: 553938786984 (Producción)*

