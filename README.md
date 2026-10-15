# Laboratorio de API observable en GCP

Proyecto: `lab-api-observable-sergio`. Requisitos completos en [instructions.md](instructions.md).

## Estado inicial

- `lab/infra/`: Terraform transcrito del PDF, con el ID del proyecto configurado.
- `lab/backend/`: API inicial de pedidos con crear, consultar y cancelar, errores 400/404/409/500, latencia artificial y logs JSON.
- `lab/simulator/`: configuración del PDF y dependencias; falta implementar `simulator.py`.

La API usa memoria local y pierde pedidos al reiniciar. Cada instancia tiene sus propios pedidos: **antes de la prueba en GCP hay que implementar almacenamiento compartido** para que las consultas y cancelaciones funcionen con escalado. Esta base no representa todavía el laboratorio completo.

## Probar la API localmente en PowerShell

Desde la raíz del repositorio (Python 3.13 recomendado; código inicial compatible con 3.12):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r lab/backend/requirements.txt
$env:FAILURE_RATE = '0'
.\.venv\Scripts\functions-framework.exe --source lab/backend/main.py --target handle --port 8080
```

En otra terminal, crear, consultar y cancelar un pedido:

```powershell
$body = @{ amount = 99.5; category = 'electronics'; customer_tier = 'premium' } | ConvertTo-Json
$order = Invoke-RestMethod -Method Post -Uri http://localhost:8080/orders -ContentType 'application/json' -Body $body -Headers @{ 'X-Request-ID' = 'local-create-1' }
Invoke-RestMethod -Uri "http://localhost:8080/orders/$($order.id)"
Invoke-RestMethod -Method Post -Uri "http://localhost:8080/orders/$($order.id)/cancel"
```

Repetir la cancelación devuelve 409; consultar un ID inexistente devuelve 404; crear un pedido sin los campos válidos devuelve 400. `FAILURE_RATE=1` fuerza errores 500 y `EXTRA_LATENCY_MS` agrega demora en milisegundos.

## Preparar Terraform

`terraform.tfvars` contiene la configuración local y está ignorado por Git. Para otra copia del repositorio, copiar `terraform.tfvars.example` a `terraform.tfvars` y revisar el ID del proyecto.

```powershell
Set-Location lab/infra
terraform init
terraform validate
terraform plan
```

El despliegue se realiza posteriormente con `terraform apply`, una vez resuelto el almacenamiento. La infraestructura del PDF permite invocaciones públicas, habilita Log Analytics permanentemente y conserva las APIs habilitadas después de `terraform destroy`.

## Pendiente para completar el laboratorio

1. Almacenamiento compartido para pedidos y los recursos/permisos correspondientes.
2. Simulador concurrente de una hora, distribución normal truncada, escenarios, errores intencionales y salida CSV.
3. Métricas basadas en logs, creadas antes de ejecutar el simulador.
4. Un dashboard con métricas nativas, métricas de logs, gráficas SQL y panel de logs.
5. Desplegar, poner `function_url` en `lab/simulator/config.json`, ejecutar el tráfico y analizar resultados.
6. Conservar evidencias y ejecutar `terraform destroy` al terminar.

El valor `target_url` del ejemplo es un marcador: reemplazarlo por la URL completa de Terraform, sin agregar otro `https://`.
