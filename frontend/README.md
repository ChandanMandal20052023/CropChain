# CropChain Frontend

The **CropChain** frontend is a lightweight, responsive web interface built using modern semantic HTML5, CSS3 design tokens, and vanilla ES6 JavaScript modules. It provides role-based operation dashboards and a public consumer product passport.

---

## 📁 Directory Structure

```
frontend/
├── assets/
│   ├── css/
│   │   └── styles.css          # Design system, CSS custom properties, and responsive layout
│   └── js/
│       ├── api.js              # Centralized API client & demo mode simulator
│       ├── app.js              # Global app controller and demo mode banner
│       ├── dashboard.js        # Operations dashboard controller (stats & batch management)
│       ├── login.js            # JWT authentication and session persistence
│       └── track.js            # Public product passport verification logic
├── pages/
│   ├── dashboard.html          # Operations dashboard for farmers and logistics actors
│   ├── login.html              # Authenticated user sign-in portal
│   └── track.html              # Public QR-accessible product passport page
├── index.html                  # Landing page and platform overview
└── README.md                   # Frontend documentation (this file)
```

---

## 🚀 Running the Frontend Locally

Because ES6 JavaScript modules require HTTP/HTTPS origin security (and cannot run directly over `file://`), run a simple static web server:

```bash
cd frontend

# Using Python's built-in HTTP server:
python -m http.server 8080
```

Open **`http://localhost:8080`** in your browser.

---

## ⚙️ Configuration & Backend Integration

In [`assets/js/api.js`](assets/js/api.js), configure the connection parameters:

```javascript
export const CONFIG = {
  // Target URL for Django REST API
  API_BASE: 'http://127.0.0.1:8000/api/v1',
  
  // Set to false to connect directly to the running Django backend:
  DEMO_MODE: false
};
```

- **Demo Mode (`DEMO_MODE = true`)**: Runs with simulated supply-chain data, preloaded sample batches, and mock authentication without needing Django or MySQL running.
- **Live Mode (`DEMO_MODE = false`)**: Communicates with the live Django REST Framework API at `/api/v1/`, sending JWT `Bearer` tokens in the `Authorization` header.

### Sample Demo Track Code
- **`CC-2026-00123`**: Preloaded sample Basmati Rice batch with complete verified timeline from Punjab farm to retail supermarket.
