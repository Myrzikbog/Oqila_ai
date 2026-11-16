import { lazy } from 'react';

// The admin panel is loaded only on the admin route, keeping it out of the main bundle
export const AdminApp = lazy(() => import('./admin/AdminApp.jsx'));
// The /stage presentation screen is public and loaded only on that route
export const StageApp = lazy(() => import('./stage/StageApp.jsx'));
