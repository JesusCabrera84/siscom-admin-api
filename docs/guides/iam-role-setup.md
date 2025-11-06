# Configuración de IAM Role para EC2

Esta guía te ayudará a configurar un IAM Role para tu instancia EC2 para que pueda acceder a AWS Cognito sin necesidad de credenciales hardcodeadas.

## 🎯 ¿Por qué usar IAM Roles?

**Ventajas:**
- ✅ **Más seguro**: No necesitas almacenar credenciales en variables de entorno
- ✅ **Automático**: Las credenciales se rotan automáticamente
- ✅ **Mejor práctica**: Recomendado por AWS
- ✅ **Menos configuración**: No necesitas `AWS_ACCESS_KEY_ID` ni `AWS_SECRET_ACCESS_KEY`

## 📋 Pasos para Configurar

### 1. Crear una Política IAM para Cognito

1. Ve a la **Consola de AWS**
2. Navega a **IAM → Policies → Create policy**
3. Selecciona la tab **JSON**
4. Pega esta política:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:AdminInitiateAuth",
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminSetUserPassword",
                "cognito-idp:AdminGetUser",
                "cognito-idp:AdminUpdateUserAttributes",
                "cognito-idp:AdminDeleteUser",
                "cognito-idp:ListUsers",
                "cognito-idp:AdminResetUserPassword",
                "cognito-idp:AdminConfirmSignUp",
                "cognito-idp:AdminDisableUser",
                "cognito-idp:AdminEnableUser",
                "cognito-idp:AdminUserGlobalSignOut",
                "cognito-idp:GlobalSignOut",
                "cognito-idp:ChangePassword"
            ],
            "Resource": "arn:aws:cognito-idp:*:*:userpool/*"
        }
    ]
}
```

5. Click en **Next**
6. **Policy name**: `siscom-cognito-access`
7. **Description**: `Permite al API de SISCOM acceder a Cognito`
8. Click en **Create policy**

### 2. Crear un IAM Role

1. En la consola de AWS, ve a **IAM → Roles → Create role**
2. **Trusted entity type**: Selecciona **AWS service**
3. **Use case**: Selecciona **EC2**
4. Click en **Next**

### 3. Adjuntar la Política al Role

1. En **Permissions policies**, busca `siscom-cognito-access`
2. Marca el checkbox de la política que creaste
3. Click en **Next**
4. **Role name**: `siscom-ec2-cognito-role`
5. **Description**: `Rol para EC2 que permite acceso a Cognito`
6. Click en **Create role**

### 4. Asignar el Role a tu Instancia EC2

#### Si ya tienes una instancia corriendo:

1. Ve a **EC2 → Instances**
2. Selecciona tu instancia
3. **Actions → Security → Modify IAM role**
4. En **IAM role**, selecciona `siscom-ec2-cognito-role`
5. Click en **Update IAM role**

#### Si vas a crear una nueva instancia:

1. Al crear la instancia EC2, en la sección **Advanced details**
2. En **IAM instance profile**, selecciona `siscom-ec2-cognito-role`

### 5. Verificar la Configuración

SSH a tu instancia EC2 y verifica que puede acceder a AWS:

```bash
# Conectarse al EC2
ssh -i tu-clave.pem ubuntu@tu-ip-ec2

# Verificar que tiene acceso a Cognito
aws cognito-idp list-user-pools --max-results 10

# Si funciona, verás una lista de user pools (o un error de permisos pero no de credenciales)
```

## 🔄 Reiniciar el Contenedor (Importante)

Después de asignar el IAM Role, **debes reiniciar tu contenedor** para que tome las nuevas credenciales:

```bash
cd ~/siscom-admin-api
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## ✅ Verificar que Funciona

1. Verifica los logs del contenedor:
```bash
docker logs -f siscom-admin-api
```

2. No deberías ver errores relacionados con credenciales de AWS

3. Prueba el health endpoint:
```bash
curl http://localhost:8100/health
```

## 🚫 Eliminar Secrets Innecesarios de GitHub

Una vez que el IAM Role esté configurado, **ya no necesitas** estos secrets en GitHub:
- ❌ `AWS_ACCESS_KEY_ID` - Puedes eliminarlo
- ❌ `AWS_SECRET_ACCESS_KEY` - Puedes eliminarlo

Boto3 usará automáticamente las credenciales del IAM Role.

## 🔍 Troubleshooting

### Error: "Unable to locate credentials"

**Causa**: El IAM Role no está asignado correctamente o el contenedor no tiene acceso.

**Solución**:
1. Verifica que el role esté asignado: **EC2 → Instances → Security → IAM role**
2. Reinicia el contenedor después de asignar el role
3. Verifica desde dentro del contenedor:
```bash
docker exec -it siscom-admin-api /bin/bash
curl http://169.254.169.254/latest/meta-data/iam/security-credentials/
```

### Error: "Access Denied" al llamar a Cognito

**Causa**: El IAM Role no tiene los permisos necesarios.

**Solución**:
1. Verifica que la política `siscom-cognito-access` esté adjunta al role
2. Revisa los permisos de la política
3. Asegúrate de que el User Pool está en la misma región

### El contenedor sigue pidiendo AWS_ACCESS_KEY_ID

**Causa**: Las variables de entorno están configuradas como vacías.

**Solución**:
Elimina completamente las variables de entorno del `.env`:
```bash
# NO incluir estas líneas en .env:
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
```

## 📚 Recursos Adicionales

- [AWS IAM Roles for EC2](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html)
- [AWS Cognito API Reference](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/Welcome.html)
- [Boto3 Credentials Configuration](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html)

## 🎯 Resumen

1. ✅ Crea una política IAM con permisos para Cognito
2. ✅ Crea un IAM Role para EC2
3. ✅ Adjunta la política al role
4. ✅ Asigna el role a tu instancia EC2
5. ✅ Reinicia el contenedor Docker
6. ✅ Elimina `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` de GitHub Secrets (opcional)

---

**Última actualización:** Noviembre 2025

