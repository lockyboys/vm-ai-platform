# SPS Runtime v1.1 (2026-07-08)

## Major Features

### DOCUMENT Object Runtime

- PDF Runtime
- Text Extraction
- Document Object

### IMAGE Object Runtime

- EasyOCR
- Image Metadata
- Image Object

### VIDEO Object Runtime

- Video Metadata
- Frame Extraction
- Frame OCR
- Video Object

### Runtime Engine

- Object Runtime Engine
- Execution Plan
- Repository Generator
- MongoDB Generator
- Execution History

## Architecture

```text
File
    ↓
Object
    ↓
Analyzer
    ↓
Runtime
    ↓
Repository
    ↓
MongoDB

