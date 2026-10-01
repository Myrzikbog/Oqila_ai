import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import AdminApp from './admin/AdminApp.jsx'

const searchParams = new URLSearchParams(window.location.search);
const tgStartParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
const isAdminRoute = 
  window.location.pathname.startsWith('/admin') || 
  searchParams.get('view') === 'admin' ||
  searchParams.get('admin') === '1' ||
  searchParams.get('startapp') === 'admin' ||
  tgStartParam === 'admin';

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {isAdminRoute ? <AdminApp /> : <App />}
  </StrictMode>,
)

