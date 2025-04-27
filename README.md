# Smart Invoice Validator

A modern web application for validating invoices against contracts using AI-powered document analysis.

## Features

- Upload and manage contracts
- Upload and validate invoices
- AI-powered document analysis and data extraction
- Smart contract comparison
- Detailed validation reports
- Modern, responsive UI

## Tech Stack

### Backend
- FastAPI (Python)
- SQLAlchemy (ORM)
- Google Gemini AI (Document Analysis)
- SQLite (Database)

### Frontend
- React with TypeScript
- Tailwind CSS
- React Router
- Axios

## Prerequisites

- Python 3.8+
- Node.js 16+
- Google Gemini API Key

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/smart-invoice-validator.git
   cd smart-invoice-validator
   ```

2. Set up the backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create a `.env` file in the backend directory:
   ```
   DATABASE_URL=sqlite:///./invoice_validator.db
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-2.0-flash
   ```

4. Set up the frontend:
   ```bash
   cd ../frontend
   npm install
   ```

## Running the Application

1. Start the backend server:
   ```bash
   cd backend
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   uvicorn app.main:app --reload
   ```

2. Start the frontend development server:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open your browser and navigate to `http://localhost:3000`

## API Documentation

Once the backend server is running, you can access the API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Contributing

1. Fork the repository
2. Create a new branch for your feature
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
