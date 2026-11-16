import { StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { installAuthFetch, setReloginHandler } from './utils/session'
import { readJson } from './utils/storage';
import { AdminApp, StageApp } from './routes';
import { loginWithBackend } from './utils/auth'


installAuthFetch();
setReloginHandler(async () => Boolean(await loginWithBackend()));

const searchParams = new URLSearchParams(window.location.search);
const tgStartParam = window.Telegram?.WebApp?.initDataUnsafe?.start_param;
const isAdminRoute = 
  window.location.pathname.startsWith('/admin') || 
  searchParams.get('view') === 'admin' ||
  searchParams.get('admin') === '1' ||
  searchParams.get('startapp') === 'admin' ||
  tgStartParam === 'admin';
const isStageRoute = window.location.pathname.startsWith('/stage');

// Start signing in before the first render: child components fetch data in their effects,
// which run before App's own effect. The auth fetch wrapper waits for this login.
if (!isAdminRoute && !isStageRoute) {
  loginWithBackend(readJson('oqila_profile', null));
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {isStageRoute ? (
      <Suspense fallback={null}>
        <StageApp />
      </Suspense>
    ) : isAdminRoute ? (
      <Suspense fallback={null}>
        <AdminApp />
      </Suspense>
    ) : (
      <App />
    )}
  </StrictMode>,
)

