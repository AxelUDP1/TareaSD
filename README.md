# TareaSD - Plataforma de análisis de preguntas y respuestas en Internet

El sistema implementa lo siguiente:

- Generador de tráfico
- Caché con Redis
- Procesador de consultas Q1-Q5
- Recolector de métricas

Se evalúan distintas configuraciones de:
- distribución de tráfico: uniforme y Zipf
- política de caché: LRU y LFU
- tamaño de caché
- TTL
---

## Requisitos

- Docker Desktop
- Git

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/AxelUDP1/TareaSD.git
cd TareaSD
```

---

## Despliegue con Docker Compose (recomendado)

```bash
docker compose up --build
```

Los resultados quedan en la carpeta `results/results_summary.csv`.

Para detener:

```bash
docker compose down
```

---

