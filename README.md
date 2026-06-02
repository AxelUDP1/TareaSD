# TareaSD - Plataforma de Benchmarking de Caché con Kafka

Sistema de evaluación de caché Redis sobre datos geoespaciales de edificaciones de Santiago, con procesamiento asíncrono mediante Apache Kafka.

## Componentes

- **Tarea 1** – Sistema síncrono: generador de tráfico, caché Redis, queries Q1–Q5, métricas
- **Tarea 2** – Sistema asíncrono: producer/consumer Kafka, reintentos, Dead Letter Queue (DLQ), 7 escenarios de evaluación

---

## Requisitos

- Docker Desktop
- Git

---

## Instalación

```bash
git clone https://github.com/AxelUDP1/TareaSD.git
cd TareaSD
```

---

## Ejecución

### Tarea 1 – Sistema síncrono base

Corre 60 combinaciones de configuración (2 distribuciones × 2 políticas × 5 tamaños × 3 TTLs):

```bash
docker compose --profile tarea1 up --build
```

Resultados en `results/results_summary.csv` y 9 gráficos PNG.

---

### Tarea 2 – Sistema con Kafka

#### Modo orquestado (recomendado) — corre los 7 escenarios automáticamente

```bash
docker compose --profile tarea2-full up --build
```

Resultados en `results/kafka_results_summary.csv` y 6 gráficos PNG.

#### Modo manual — producer y consumer independientes

```bash
# Levantar infraestructura + 1 consumer
docker compose --profile tarea2 up --build

# Escalar a N consumers (en otra terminal)
docker compose --profile tarea2 up --scale consumer=4
```

---

## Escenarios evaluados (Tarea 2)

| # | Escenario | Descripción |
|---|-----------|-------------|
| 1 | Base síncrono | Sistema original Tarea 1 como referencia |
| 2 | Kafka 1 consumer | Procesamiento asíncrono básico |
| 3 | Kafka múltiples consumers | Escalamiento horizontal (1 → 2 → 4) |
| 4 | Falla temporal | 100% de fallos por 20s, mide recuperación |
| 5 | Reintentos | 50% de fallos con hasta 3 reintentos por mensaje |
| 6 | Spike de tráfico | Ráfaga de tráfico al 33% del stream |
| 7 | Recuperación | 40% de fallos continuos, cuantifica pérdida vs recuperación |

---

## Detener servicios

```bash
docker compose down
```
