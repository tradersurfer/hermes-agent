# Full-Stack Deployment Guide for Website Clone & Rebrand

## Vercel Deployment Steps

1. Install Vercel CLI: `npm install -g vercel`
2. In project root: `vercel`
3. Select project name, framework preset: `Node`
4. `vercel deploy --prod` for production

### vercel.json Configuration
```json
{
    "builds": [{"src": "server/index.js", "use": "@vercel/node"}],
    "routes": [
        {"src": "/api/(.*)", "dest": "/server/index.js"},
        {"src": "/images/(.*)", "dest": "/public/images/$1"},
        {"src": "/(.*)", "dest": "/public/index.html"}
    ]
}
```

## Railway Deployment Steps

1. Create `Dockerfile`:
```dockerfile
FROM node:24-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install --production
COPY . .
EXPOSE 3000
CMD ["node", "server/index.js"]
```
2. Create `railway.json`:
```json
{"build": {"dockerfile": "Dockerfile"}, "start": "node server/index.js", "port": 3000}
```
3. Connect repo on Railway → auto-deploys

## Common Deployment Issues

### Port Binding
- Express must use `process.env.PORT || 3000`
- Vercel sets PORT automatically; Railway sets it too
- Local dev can hardcode 3000

### Static File Serving
- `express.static(path.join(__dirname, '..', 'public'))` serves frontend
- Images at `/public/images/` accessible at `/images/*`
- CSS/JS at `/public/css/` and `/public/js/`

### API Routes
- All API routes prefixed with `/api/`
- `GET /api/health` → health check
- `GET /api/products` → product catalog with filtering
- `GET /api/business` → business config
- `GET /api/cart` → cart contents
- `POST /api/cart` → add to cart
- `PATCH /api/cart/:id` → update quantity
- `DELETE /api/cart/:id` → remove item
- `DELETE /api/cart` → clear cart

### CORS
- `app.use(cors())` allows cross-origin requests
- For production, restrict origins: `cors({origin: 'https://yourdomain.com'})`

## In-Memory Cart Limitation
- Cart resets on server restart
- For production: add MongoDB/PostgreSQL
- Alternative: `localStorage` on frontend synced to server via API
