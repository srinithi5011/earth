# Darukaa.Earth

AI-powered biodiversity and environmental intelligence system that combines structured environmental data, retrieval-augmented generation, scientific evidence, and multi-metric reasoning to generate actionable ecological recommendations.

Live Demo:
https://earth-1-g0v1.onrender.com/

Backend API:
https://earth-jtl9.onrender.com/

API Documentation:
https://earth-jtl9.onrender.com/docs

GitHub:
https://github.com/srinithi5011/earth


## Overview

Darukaa.Earth is designed as an AI environmental scientist rather than a generic chatbot.

The system takes environmental conditions such as soil health, rainfall, land use, biodiversity, water availability, temperature, and human impact, then reasons across relationships between these variables.

Instead of generating recommendations only from an LLM, the system:

1. Extracts environmental conditions from the user's query.
2. Identifies missing information when the query is incomplete.
3. Expands the query into related environmental concepts.
4. Retrieves relevant knowledge from the environmental knowledge base.
5. Builds relationships between environmental variables.
6. Generates recommendations using deterministic scientific reasoning.
7. Grounds recommendations using retrieved evidence.
8. Returns structured environmental assessment and recommendation data.

The goal is to provide recommendations that are specific, explainable, and connected to measurable environmental outcomes.


## Why Darukaa.Earth

Environmental problems are interconnected.

For example:

Low soil organic carbon + low rainfall + monoculture

can affect:

- Soil health
- Water retention
- Vegetation diversity
- Habitat quality
- Biodiversity

A useful environmental system therefore needs to reason across multiple variables instead of treating each metric independently.

Darukaa.Earth uses a relationship-based reasoning layer to connect these environmental factors and generate interventions such as:

- Cover crops
- Crop rotation
- Residue retention
- Intercropping
- Agroforestry
- Native vegetation strips
- Water retention practices


## Core Features

### Environmental conversation

Users can describe an ecosystem or environmental situation using natural language.

Example:

"My farm is in a semi-arid region. Soil organic carbon is 0.3%, rainfall is low, and I have been growing wheat as a monoculture for several years. What should I do to improve soil health and biodiversity?"

The system extracts the relevant environmental conditions and reasons over them.

### Multi-metric reasoning

The system connects multiple environmental variables instead of providing isolated recommendations.

Examples include:

- Soil organic carbon → soil health → vegetation growth
- Rainfall → water availability → ecological stress
- Monoculture → vegetation diversity → habitat quality
- Land fragmentation → habitat connectivity → biodiversity
- Temperature → climate stress → water demand

### Evidence-grounded recommendations

Recommendations are linked to retrieved knowledge from the system's environmental knowledge base.

Each recommendation can include:

- Recommendation
- Scientific reasoning
- Affected environmental metrics
- Expected effect
- Time horizon
- Confidence
- Supporting evidence

### Missing information detection

The system does not automatically assume that missing environmental measurements are known.

For example, if biodiversity is not directly measured, the system can report:

"Insufficient Data"

and identify useful measurements such as:

- Species richness
- Habitat diversity
- Pollinator diversity
- Vegetation diversity

This helps distinguish between measured environmental conditions and inferred ecological risk.

### Structured output

The backend returns structured JSON containing:

- Environmental assessment
- Recommendations
- Evidence
- Reasoning
- Affected metrics
- Time horizons
- Confidence
- Uncertainty information

This allows the frontend to present the same reasoning in different visual formats.


## System Architecture

The system follows this pipeline:

User Query
    |
    v
Environmental Information Extraction
    |
    v
Missing Information Detection
    |
    v
Query Expansion
    |
    v
Knowledge Retrieval
    |
    v
Environmental Reasoning
    |
    v
Recommendation Generation
    |
    v
Evidence Verification
    |
    v
Structured API Response
    |
    v
React Frontend


## Technology Stack

Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Mapbox GL
- Leaflet

Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic

AI and Retrieval

- Retrieval-Augmented Generation
- TF-IDF based retrieval
- Structured environmental knowledge base
- Deterministic environmental reasoning
- Optional LLM-based response phrasing

Database

- SQLite for local development
- PostgreSQL for production-style deployment
- pgvector support for vector-based retrieval

Deployment

- Render
- Docker
- GitHub


## Knowledge System

The knowledge system stores environmental information as structured chunks.

Each knowledge chunk can contain:

- Title
- Organization
- Source URL
- Publication year
- Document type
- Environmental metrics
- Text content
- Metadata

The current seeded dataset is the Darukaa Earth Curated Knowledge Base.

The architecture supports ingesting additional scientific reports, research papers, environmental datasets, and institutional publications.


## Retrieval

The current local retrieval implementation uses TF-IDF.

The retrieval process is:

1. User query is received.
2. Environmental concepts are extracted.
3. Related terms are added through query expansion.
4. Knowledge chunks are compared against the expanded query.
5. Relevant chunks are selected.
6. Retrieved evidence is passed into the reasoning and recommendation pipeline.

The system is designed so that the retrieval layer can be replaced or extended with embedding-based vector search.


## Environmental Reasoning

The reasoning layer evaluates environmental conditions and identifies relevant intervention categories.

Examples:

Soil organic carbon

Low SOC can trigger:

- Cover crops
- Crop rotation
- Residue retention

Monoculture

Monoculture can trigger:

- Intercropping
- Crop rotation
- Agroforestry
- Native vegetation strips

Low rainfall

Low rainfall can trigger:

- Water retention
- Agroforestry
- Drought-tolerant cover crops

The reasoning layer also creates relationships between environmental variables.

Example:

Soil organic carbon
    |
    v
Soil health
    |
    v
Vegetation growth
    |
    v
Habitat quality
    |
    v
Biodiversity


## Recommendation Structure

A recommendation returned by the system contains information such as:
{
  "recommendation": "Introduce cover crops",
  "scientific_reasoning": "Cover crops can increase organic matter inputs and improve soil structure.",
  "affected_metrics": [
    "soil.organic_carbon",
    "soil.health",
    "water.retention"
  ],
  "time_horizon": "1-3 years",
  "expected_effect": "Improved soil organic matter and water retention",
  "confidence": 0.8,
  "evidence": []
}
