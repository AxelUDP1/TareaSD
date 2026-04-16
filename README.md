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

- Python 3.10 o superior
- Docker Desktop
- Git

---

## Instalación
### 1. Clonar el repositorio

- git clone https://github.com/AxelUDP1/TareaSD.git
- cd TareaSD    

### 2. Instalar dependencias

- pip install -r requirements.txt

---

## Despliegue del sistema

### Levantar Redis (caché)
- docker run -d --name redis_cache -p 6379:6379 redis:7
- Verificar: docker ps

---

## Ejecución del sistema

- Entrar a la carpeta `src`:
- cd src
- python main.py

---