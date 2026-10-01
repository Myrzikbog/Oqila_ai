import React, { useState, useEffect } from 'react';
import AdminNavbar from './components/AdminNavbar';
import AdminDashboard from './components/AdminDashboard';
import AdminUsers from './components/AdminUsers';
import AdminCards from './components/AdminCards';
import AdminEvents from './components/AdminEvents';
import AdminLogin from './components/AdminLogin';
import AdminUserDetailModal from './components/AdminUserDetailModal';
import { getAdminKey, setAdminKey, clearAdminKey, testAdminKey } from './utils/adminApi';

export default function AdminApp() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => {
    return Boolean(getAdminKey());
  });
  const [activeTab, setActiveTab] = useState('dashboard'); // 'dashboard' | 'users' | 'cards' | 'events'
  const [selectedUserId, setSelectedUserId] = useState(null);

  useEffect(() => {
    const key = getAdminKey();
    if (key) {
      testAdminKey(key).then((ok) => {
        if (ok) {
          setIsAuthenticated(true);
        } else {
          clearAdminKey();
          setIsAuthenticated(false);
        }
      });
    }
  }, []);

  const handleLogout = () => {
    clearAdminKey();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return <AdminLogin onLoginSuccess={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-brand-500 selection:text-white">
      {/* Top Navbar */}
      <AdminNavbar
        activeTab={activeTab}
        onSelectTab={(tab) => {
          setActiveTab(tab);
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        onLogout={handleLogout}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        {activeTab === 'dashboard' && (
          <AdminDashboard
            onSelectTab={(tab) => {
              setActiveTab(tab);
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
          />
        )}

        {activeTab === 'users' && (
          <AdminUsers onSelectUser={(id) => setSelectedUserId(id)} />
        )}

        {activeTab === 'cards' && (
          <AdminCards onSelectUser={(id) => setSelectedUserId(id)} />
        )}

        {activeTab === 'events' && (
          <AdminEvents onSelectUser={(id) => setSelectedUserId(id)} />
        )}
      </main>

      {/* User Details Modal */}
      {selectedUserId && (
        <AdminUserDetailModal
          userId={selectedUserId}
          onClose={() => setSelectedUserId(null)}
        />
      )}
    </div>
  );
}
