# ReddyFit - Body Scan Analysis API

A production-ready FastAPI application for analyzing body scans using AI-powered computer vision. This API processes multi-angle body images, performs comprehensive body composition analysis using Anthropic's Claude Vision, and provides detailed metrics with optional WHOOP integration.

## Features Implemented

### Core Functionality
- **Multi-Image Scan Processing**: Upload and analyze front, side, and back body images
- **AI-Powered Vision Analysis**: Integration with Anthropic Claude for detailed body composition insights
- **Image Quality Validation**: Automated checks for sharpness, lighting, and image quality
- **Angle Detection**: Basic heuristic validation for proper body positioning
- **Metrics Calculation**: Comprehensive body measurements and composition analysis
- **User Profile Management**: Height, gender, and WHOOP integration tracking

### Storage & Persistence
- **Local Storage**: Default filesystem-based storage in `.data/` directory
- **Azure Integration**:
  - Azure Blob Storage for image uploads with SAS token generation
  - Azure Cosmos DB for scan results and user data persistence
- **GCS/Firestore Support**: Optional Google Cloud Platform integration

### API Features
- **RESTful Endpoints**: Clean, intuitive API design
- **Mock Mode**: Test without API keys using `?mock=true`
- **Error Handling**: Comprehensive error responses with detailed logging
- **Request Validation**: Pydantic schemas for type safety
- **CORS Support**: Configurable cross-origin resource sharing

### DevOps & Quality
- **CI/CD Pipeline**: GitHub Actions workflow for automated testing
- **Testing**: Pytest-based test suite with mock support
- **Code Quality**: Black, isort, and ruff configuration
- **Environment Configuration**: Flexible `.env` based settings
- **Logging**: Structured logging with configurable levels

## API Endpoints

### Scan Management
- **POST** `/scans/` - Initialize a new scan
  ```json
  {
    "uid": "user-123",
    "height_cm": 180,
    "gender": "male",
    "whoop_linked": false
  }
  ```

- **POST** `/scans/{scanId}/images` - Upload body images
  - Multipart form fields: `front`, `side`, `back`
  - Automatic quality validation and preprocessing

- **POST** `/scans/{scanId}/finalize` - Complete analysis and persist results
  - Computes body metrics
  - Integrates vision analysis
  - Stores results to configured backend

- **GET** `/scans/{scanId}` - Retrieve scan results
  - Returns complete scan data with metrics

## Quick Start

### Installation
```bash
# Clone the repository
git clone https://github.com/DandaAkhilReddy/ReddyFitv0.0.1.git
cd ReddyFitv0.0.1

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### Configuration
Edit `.env` file with your settings:
```bash
# Required for vision analysis
ANTHROPIC_API_KEY=your_api_key_here

# Optional: Configure storage provider
storage_provider=local  # or azure, gcs

# Optional: Azure settings
azure_storage_connection_string=...
azure_storage_container=...
cosmos_enabled=true
cosmos_endpoint=...
cosmos_key=...
```

### Run Locally
```bash
# Start the API server
uvicorn app.main:app --reload

# API will be available at http://localhost:8000
# Interactive docs at http://localhost:8000/docs
```

### Run Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## Environment Variables

### Required
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude Vision

### Optional Configuration
- `ENVIRONMENT` - Environment name (default: `development`)
- `DATA_DIR` - Local data directory (default: `.data`)
- `storage_provider` - Storage backend: `local`, `azure`, or `gcs`

### Image Processing Thresholds
- `image_quality_min_score` - Minimum quality score (default: 50)
- `sharpness_threshold` - Minimum sharpness level (default: 50)
- `preprocess_max_dim` - Maximum image dimension (default: 1024)
- `jpeg_quality` - JPEG compression quality (default: 85)
- `confidence_threshold` - AI confidence threshold (default: 0.70)
- `angle_enforcement` - Enable strict angle validation (default: false)

### Azure Configuration
- `azure_storage_connection_string` - Azure Storage connection string
- `azure_storage_container` - Blob container name
- `azure_sas_expiry_minutes` - SAS token expiry (default: 60)
- `cosmos_enabled` - Enable Cosmos DB (default: false)
- `cosmos_endpoint` - Cosmos DB endpoint URL
- `cosmos_key` - Cosmos DB access key
- `cosmos_db` - Database name
- `cosmos_scans_container` - Scans container (default: `scans`)
- `cosmos_users_container` - Users container (default: `users`)

### GCP Configuration
- `firestore_enabled` - Enable Firestore (default: false)
- `gcp_project_id` - Google Cloud project ID
- `gcs_bucket_name` - GCS bucket name

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI app factory and lifespan hooks
│   ├── config.py            # Centralized settings and thresholds
│   ├── version.py           # Application version
│   ├── core/
│   │   ├── errors.py        # AppError class and error handlers
│   │   ├── logging.py       # Logging configuration
│   │   └── __init__.py
│   ├── routers/
│   │   ├── scans.py         # Scan endpoints
│   │   └── __init__.py
│   ├── schemas/
│   │   └── scan.py          # Pydantic models for I/O
│   ├── services/
│   │   ├── ai_vision.py     # Claude Vision integration
│   │   ├── image_pipeline.py # Image validation & preprocessing
│   │   ├── metrics_math.py  # Body metrics calculations
│   │   ├── persistence.py   # Storage abstraction layer
│   │   ├── pose.py          # MediaPipe pose estimation
│   │   ├── signature.py     # Signed URL generation
│   │   ├── storage.py       # Local file storage
│   │   ├── storage_cloud.py # Cloud storage (Azure/GCS)
│   │   └── whoop.py         # WHOOP API integration (stub)
│   └── __init__.py
├── tests/
│   └── test_scan_flow.py    # End-to-end scan tests
├── scripts/
│   └── live_claude_smoke.py # Manual testing script
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI pipeline
├── .env.example             # Environment template
├── requirements.txt         # Python dependencies
├── pyproject.toml          # Code formatting config
└── README.md               # This file
```

## Development

### Code Formatting
```bash
# Format code
python -m black .
python -m isort .

# Check linting
python -m ruff check .
```

### Testing Strategy
- All tests run without requiring cloud SDKs or API keys
- Mock mode enabled by default in CI/CD
- Local `.data/` directory used for test persistence

## Deployment

### CI/CD
- GitHub Actions workflow runs on push/PR to `main`
- Automated testing with Python 3.11
- Tests run in mock mode (no live API calls)

### Production Considerations
- Configure appropriate storage backend (Azure/GCS)
- Set up Cosmos DB or Firestore for scalability
- Enable HTTPS and configure CORS properly
- Set appropriate image quality thresholds
- Monitor API key usage and rate limits

## Roadmap

### Completed
- ✅ FastAPI scaffold with scan endpoints
- ✅ Image quality validation and preprocessing
- ✅ Claude Vision integration
- ✅ Azure Storage and Cosmos DB support
- ✅ GCS/Firestore optional integration
- ✅ Basic angle detection heuristics
- ✅ CI/CD pipeline setup
- ✅ Comprehensive test coverage

### Planned
- [ ] Enhanced pose estimation using MediaPipe
- [ ] Real WHOOP API integration
- [ ] Advanced body metrics algorithms
- [ ] User authentication and authorization
- [ ] Rate limiting and quota management
- [ ] Webhook notifications for scan completion
- [ ] Batch processing support
- [ ] Export to PDF/CSV formats

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is proprietary and confidential.

## Support

For issues, questions, or contributions, please open an issue on GitHub.
