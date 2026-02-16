# Pharmacy & Lab Management System

A comprehensive web-based system for managing pharmacy operations, lab production, and e-commerce.

## Features

### Phase 1 - Internal Operations
- ✅ Inventory Management with automated reordering
- ✅ Point of Sale (POS) system
- ✅ Purchase Order management
- ✅ Lab production and batch tracking
- ✅ Reports and analytics

### Phase 2 - E-commerce
- 🔄 Online storefront for lab-formulated topicals
- 🔄 Customer portal
- 🔄 Order fulfillment and shipping

## Tech Stack

**Frontend:**
- React 18 + Vite
- Tailwind CSS
- shadcn/ui components
- React Router
- Axios

**Backend:**
- Python 3.12
- Flask 3.x
- SQLAlchemy 2.x
- PostgreSQL 15+
- JWT Authentication

**Hosting:**
- Render (Backend + Database)
- Vercel/Render (Frontend)

## Project Structure

```
pharmacy-lab-system/
├── backend/           # Flask API
│   ├── app/
│   │   ├── models/    # Database models
│   │   ├── routes/    # API endpoints
│   │   ├── services/  # Business logic
│   │   └── utils/     # Helper functions
│   ├── migrations/    # Database migrations
│   ├── config.py      # Configuration
│   └── run.py         # Application entry point
│
├── frontend/          # React application
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/  # API calls
│   │   └── utils/
│   └── package.json
│
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
flask run
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

### Backend (.env)
```
DATABASE_URL=postgresql://user:password@localhost:5432/pharmacy_db
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-here
FLASK_ENV=development
```

### Frontend (.env)
```
VITE_API_URL=http://localhost:5000
```

## Development

- Backend runs on `http://localhost:5000`
- Frontend runs on `http://localhost:5173`

## Deployment

### Render Deployment
1. Push code to GitHub
2. Connect Render to repository
3. Configure environment variables
4. Deploy!

## License

Proprietary - All rights reserved

## Contact

For support or questions, contact the development team.
