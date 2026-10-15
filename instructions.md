# Instrucciones del laboratorio: API serverless observable en GCP

## Guía de preparación del repositorio (añadida)

Esta sección es una guía complementaria. La sección **Contenido del PDF** conserva las instrucciones, ejemplos de código y fuentes del documento entregado por el usuario. Se han unido los saltos entre páginas y las líneas de las URL en HCL para que los ejemplos puedan copiarse. Las instrucciones del laboratorio se documentan aquí; no se han ejecutado ni se ha desplegado infraestructura.

### Qué necesitas instalar o tener disponible

- **Terraform >= 1.5**: se instala en tu equipo; los archivos `.tf` sí pertenecen al repositorio. `terraform init` descarga los proveedores Google >= 6.0 y Archive >= 2.4 especificados en el PDF.
- **Google Cloud CLI (`gcloud`)**: para autenticar Terraform mediante `gcloud auth application-default login`.
- **Python**: el runtime configurado por el PDF es `python313` (Python 3.13). Usar Python 3.13 localmente ayuda a mantener compatibilidad con el backend desplegado.
- **Dependencias Python**: el backend necesita Functions Framework y las librerías que utilice tu implementación, declaradas en `backend/requirements.txt`. El PDF remite a HTTPX y NumPy para el simulador; conviene declarar sus dependencias en un `simulator/requirements.txt` adicional.
- **Un proyecto GCP** con facturación habilitada y permisos suficientes para habilitar APIs, crear los recursos y modificar IAM que aparecen en el Terraform del PDF. Los roles de `student_members` del ejemplo son para observabilidad y consulta; por sí solos no cubren todo el despliegue.
- **Git**, para versionar el trabajo. No necesitas instalar un servidor local de Terraform ni incluir sus binarios en el repositorio.

### Qué debe contener el repositorio

La base del repositorio ya incluye los archivos Terraform, una API inicial de pedidos y la configuración del simulador. El estado actual y los comandos de prueba están en [README.md](README.md). Falta implementar el almacenamiento compartido, el simulador y la observabilidad. Esta tabla describe los componentes requeridos:

| Ubicación | Contenido y propósito |
| --- | --- |
| `lab/infra/versions.tf` | Versión de Terraform y proveedores. |
| `lab/infra/variables.tf` | Parámetros del proyecto, función y observabilidad. |
| `lab/infra/main.tf` | APIs, IAM, bucket, empaquetado y función de segunda generación. |
| `lab/infra/outputs.tf` | URL de la función y enlaces de observabilidad. |
| `lab/infra/terraform.tfvars` | Valores locales reales del proyecto. El PDF incluye un ejemplo. |
| `lab/backend/main.py` | API HTTP con entrada `handle`, operaciones, errores y logs JSON. El PDF describe requisitos, pero no proporciona esta implementación. |
| `lab/backend/requirements.txt` | Dependencias del backend. |
| `lab/simulator/simulator.py` | Generador concurrente de tráfico durante una hora. El PDF describe requisitos, pero no proporciona esta implementación. |
| `lab/simulator/config.json` | URL, volumen de solicitudes, distribución y escenarios. |
| `lab/simulator/requests.csv` | Resultado generado por el simulador; no es un archivo de entrada. |

Archivos adicionales recomendados, no exigidos por el PDF:

- `.gitignore`: excluir `.terraform/`, `*.tfstate`, `*.tfstate.*`, `.build/`, `.venv/`, `__pycache__/`, credenciales y valores locales sensibles. No subir claves de cuentas de servicio.
- `lab/infra/terraform.tfvars.example`: plantilla para compartir parámetros sin valores privados; conservar el archivo real localmente.
- `lab/simulator/requirements.txt`: dependencias del simulador, por ejemplo HTTPX y NumPy si se usan las bibliotecas sugeridas.
- `.terraform.lock.hcl`: se genera con `terraform init`; conviene versionarlo para fijar los proveedores seleccionados.
- Una carpeta de evidencias o configuración exportada del dashboard, métricas y consultas, para poder reproducir el análisis.

### Orden de trabajo

1. Crear la estructura `lab/` e implementar el backend y el simulador conforme al PDF. Definir el dominio y cómo se conservan los recursos entre solicitudes; la memoria de una instancia no se comparte con otras instancias.
2. Copiar los ejemplos Terraform de abajo a `lab/infra/` y completar los parámetros del proyecto.
3. Desde `lab/infra/`, autenticar con `gcloud auth application-default login`, ejecutar `terraform init` y revisar el despliegue con `terraform plan` antes de `terraform apply`. `plan` es una recomendación adicional.
4. Colocar la salida `function_url` en `lab/simulator/config.json`.
5. Crear las métricas basadas en logs **antes de ejecutar el simulador**. Preparar el dashboard con las cuatro fuentes requeridas; el Terraform proporcionado no crea el dashboard ni esas métricas.
6. Ejecutar el simulador durante una hora y guardar `requests.csv`. El PDF no define los argumentos de línea de comandos del script: dependerán de tu implementación.
7. Analizar métricas, errores, latencias y atributos de negocio en el dashboard.
8. Al terminar, ejecutar `terraform destroy` desde `lab/infra/`. Como indica el código del PDF, habilitar Log Analytics es permanente; destruir este recurso no revierte esa habilitación. Las APIs también se configuran con `disable_on_destroy = false`.

## Contenido del PDF

Fuente: `Laboratorio_API_observable_GCP.pdf`, 10 páginas, 9 de octubre de 2026, @Josh Merida.

# Laboratorio: API serverless observable en GCP

Oct 9, 2026 · @Josh Merida

Práctica en clase: desplegar una API en Cloud Run functions, generar una hora de tráfico
con eventos correctos y errores, y analizar sus métricas y logs en un solo dashboard de
Cloud Monitoring.

## Archivos

```text
lab/
  infra/
    versions.tf
    variables.tf
    main.tf
    outputs.tf
    terraform.tfvars
  backend/
    main.py
    requirements.txt
  simulator/
    simulator.py
    config.json
    requests.csv      # lo genera el simulador
```

## Backend (`backend/main.py`)

API HTTP en Python con un dominio pequeño a elección (pedidos, pagos, reservaciones) y
al menos tres operaciones, por ejemplo crear, consultar y cancelar. La función de entrada
se llama handle.
Responde las solicitudes válidas y rechaza las inválidas con 400 (payload inválido), 404
(recurso inexistente) o 409 (cambio de estado imposible).
Simula fallas propias con dos variables de entorno: FAILURE_RATE (probabilidad de
responder 500) y EXTRA_LATENCY_MS (latencia adicional).
Escribe una línea JSON en stdout al terminar cada solicitud, con estos campos:
severity, message ( request_completed), request_id (del header X-Request-ID),
endpoint, status_code, outcome ( success, client_error, server_error),
error_type, latency_ms y al menos dos atributos de negocio (por ejemplo
customer_tier, category, amount).

## Simulador (`simulator/simulator.py`)

Script que corre una hora desde una laptop o VM y hace el papel de los usuarios.
Genera n_requests instantes de envío con distribución normal N( μ , σ ) en minutos,
truncada a 0 y 60, y dispara cada solicitud en su instante sin esperar a la anterior.
Mezcla operaciones válidas con una proporción invalid_share de errores
intencionales (payloads inválidos, IDs inexistentes, secuencias imposibles), y aplica los
scenarios de la configuración.
Envía un ID único en X-Request-ID y escribe requests.csv con una fila por solicitud:
request_id, instante programado, instante de envío, operación, evento intencionado,
código de respuesta y latencia del cliente.

### `simulator/config.json`

```json
{
  "target_url": "https://<salida function_url de terraform>",
  "n_requests": 6000,
  "mu_min": 30,
  "sigma_min": 10,
  "invalid_share": 0.08,
  "seed": 42,
  "scenarios": [
    { "start_min": 35, "end_min": 45, "effect": "double_errors", "category": "electronics" }
  ]
}
```

## Infraestructura (`infra/`)

Desde infra/: gcloud auth application-default login, completar
terraform.tfvars, luego terraform init y terraform apply. La salida function_url
va en config.json. Si el primer apply falla en el build, esperar un minuto y repetirlo. Al
terminar: terraform destroy.

### `versions.tf`

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.4"
    }
  }
}
provider "google" {
  project = var.project_id
  region  = var.region
}
```

### `variables.tf`

```hcl
variable "project_id" {
  description = "GCP project ID for this team"
  type        = string
}
variable "region" {
  description = "Region for the function and the source bucket"
  type        = string
  default     = "us-central1"
}
variable "function_name" {
  description = "Function name (lowercase letters, digits and hyphens)"
  type        = string
  default     = "orders-api"
}
variable "runtime" {
  description = "Cloud Run functions runtime"
  type        = string
  default     = "python313"
}
variable "entry_point" {
  description = "Name of the Python function that handles requests"
  type        = string
  default     = "handle"
}
variable "source_dir" {
  description = "Folder with main.py and requirements.txt"
  type        = string
  default     = "../backend"
}
variable "failure_rate" {
  description = "Probability of a simulated internal failure (0 to 1)"
  type        = number
  default     = 0.02
}
variable "extra_latency_ms" {
  description = "Extra latency added by the backend, in milliseconds"
  type        = number
  default     = 0
}
variable "extra_env" {
  description = "Additional environment variables for the backend"
  type        = map(string)
  default     = {}
}
variable "max_instances" {
  description = "Upper limit for autoscaling"
  type        = number
  default     = 10
}
variable "concurrency" {
  description = "Concurrent requests per instance"
  type        = number
  default     = 1
}
variable "allow_unauthenticated" {
  description = "Allow public calls so the simulator needs no token"
  type        = bool
  default     = true
}
variable "log_retention_days" {
  description = "Retention for the _Default log bucket"
  type        = number
  default     = 30
}
variable "student_members" {
  description = "IAM members who need access, e.g. user:name@uvg.edu.gt"
  type        = list(string)
  default     = []
}
```

### `main.tf`

```hcl
locals {
  services = [
    "cloudfunctions.googleapis.com",
    "run.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "storage.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "iam.googleapis.com",
  ]
  student_roles = [
    "roles/monitoring.editor",
    "roles/logging.viewer",
    "roles/logging.configWriter",
    "roles/cloudfunctions.viewer",
  ]
  student_grants = {
    for pair in setproduct(var.student_members, local.student_roles) :
    "${pair[0]}|${pair[1]}" => { member = pair[0], role = pair[1] }
  }
}
# APIs
resource "google_project_service" "apis" {
  for_each           = toset(local.services)
  service            = each.value
  disable_on_destroy = false
}
# Log Analytics on the _Default bucket.
# The upgrade is permanent; destroying this resource does not undo it.
resource "google_logging_project_bucket_config" "default" {
  project          = var.project_id
  location         = "global"
  bucket_id        = "_Default"
  retention_days   = var.log_retention_days
  enable_analytics = true
  depends_on = [google_project_service.apis]
}
# Identities
resource "google_service_account" "runtime" {
  account_id   = "${var.function_name}-run"
  display_name = "Runtime identity for ${var.function_name}"
  depends_on = [google_project_service.apis]
}
resource "google_service_account" "build" {
  account_id   = "${var.function_name}-build"
  display_name = "Build identity for ${var.function_name}"
  depends_on = [google_project_service.apis]
}
resource "google_project_iam_member" "runtime_roles" {
  for_each = toset(["roles/logging.logWriter",
"roles/monitoring.metricWriter"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.runtime.email}"
}
resource "google_project_iam_member" "build_roles" {
  for_each = toset(["roles/cloudbuild.builds.builder",
"roles/logging.logWriter"])
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.build.email}"
}
resource "google_project_iam_member" "students" {
  for_each = local.student_grants
  project  = var.project_id
  role     = each.value.role
  member   = each.value.member
}
# Source code
resource "google_storage_bucket" "source" {
  name                        = "${var.project_id}-${var.function_name}-src"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
  depends_on = [google_project_service.apis]
}
data "archive_file" "source" {
  type        = "zip"
  source_dir  = var.source_dir
  output_path = "${path.module}/.build/function-source.zip"
}
# The hash in the name forces a redeploy whenever the code changes
resource "google_storage_bucket_object" "source" {
  name   = "function-source-${data.archive_file.source.output_md5}.zip"
  bucket = google_storage_bucket.source.name
  source = data.archive_file.source.output_path
}
# Function
resource "google_cloudfunctions2_function" "api" {
  name     = var.function_name
  location = var.region
  build_config {
    runtime         = var.runtime
    entry_point     = var.entry_point
    service_account = google_service_account.build.id
    source {
      storage_source {
        bucket = google_storage_bucket.source.name
        object = google_storage_bucket_object.source.name
      }
    }
  }
  service_config {
    available_memory                 = "512Mi"
    available_cpu                    = "1"
    timeout_seconds                  = 60
    min_instance_count               = 0
    max_instance_count               = var.max_instances
    max_instance_request_concurrency = var.concurrency
    service_account_email            = google_service_account.runtime.email
    ingress_settings                 = "ALLOW_ALL"
    environment_variables = merge(var.extra_env, {
      FAILURE_RATE     = tostring(var.failure_rate)
      EXTRA_LATENCY_MS = tostring(var.extra_latency_ms)
    })
  }
  depends_on = [
    google_project_iam_member.build_roles,
    google_project_iam_member.runtime_roles,
  ]
}
# Public access for the simulator
resource "google_cloud_run_v2_service_iam_member" "public" {
  count    = var.allow_unauthenticated ? 1 : 0
  project  = var.project_id
  location = var.region
  name     = google_cloudfunctions2_function.api.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
```

### `outputs.tf`

```hcl
output "function_url" {
  description = "URL for the simulator"
  value       = google_cloudfunctions2_function.api.url
}
output "log_analytics_view" {
  description = "Table name for SQL queries in Log Analytics"
  value       = "`${var.project_id}.global._Default._Default`"
}
output "dashboards_console" {
  value = "https://console.cloud.google.com/monitoring/dashboards?project=${var.project_id}"
}
output "log_analytics_console" {
  value = "https://console.cloud.google.com/logs/analytics?project=${var.project_id}"
}
```

### `terraform.tfvars`

```hcl
project_id      = "my-team-project"
region          = "us-central1"
function_name   = "orders-api"
failure_rate    = 0.02
student_members = []
```

## Dashboard

Cada equipo define qué preguntas quiere responder y arma un solo dashboard de Cloud
Monitoring con métricas nativas de la función, métricas basadas en logs, gráficas SQL de
Log Analytics y un panel de logs. Las métricas basadas en logs se crean antes de correr el
simulador, porque no cuentan logs anteriores.

## Fuentes

- [Functions Framework for Python](https://github.com/GoogleCloudPlatform/functions-framework-python)
- [Structured logging](https://docs.cloud.google.com/logging/docs/structured-logging)
- [HTTPX: Async Support](https://www.python-httpx.org/async/)
- [numpy Generator.normal](https://numpy.org/doc/stable/reference/random/generated/numpy.random.Generator.normal.html)
- [Terraform: Get Started on Google Cloud](https://developer.hashicorp.com/terraform/tutorials/gcp-get-started)
- [Log-based metrics overview](https://docs.cloud.google.com/logging/docs/logs-based-metrics)
- [Query and analyze logs with Log Analytics](https://docs.cloud.google.com/logging/docs/analyze/query-and-view)
- [Chart SQL query results](https://docs.cloud.google.com/logging/docs/analyze/charts)
- [Create and manage custom dashboards](https://docs.cloud.google.com/monitoring/charts/dashboards)
- [Display logs on a dashboard](https://docs.cloud.google.com/monitoring/charts/view-logs)
