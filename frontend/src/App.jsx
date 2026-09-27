import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import BottomNav from './components/BottomNav';
import TabStudio from './components/TabStudio';
import TabFinance from './components/TabFinance';
import TabLegal from './components/TabLegal';
import TabAbout from './components/TabAbout';
import HistoryModal from './components/HistoryModal';
import ProfileModal from './components/ProfileModal';
import OnboardingModal from './components/OnboardingModal';
import { translations } from './utils/i18n';
import { 
  initTelegram, 
  getInitialTheme, 
  applyTheme, 
  subscribeToThemeChanges, 
  hapticImpact 
} from './utils/telegram';

export default function App() {
  const [lang, setLang] = useState(() => {
    return localStorage.getItem('oqila_lang') || 'ru';
  });
  const [theme, setTheme] = useState(getInitialTheme);
  const [activeTab, setActiveTab] = useState('studio');
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [selectedHistoryCard, setSelectedHistoryCard] = useState(null);

  // User Business Profile state & Onboarding
  const [profile, setProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('oqila_profile');
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [isOnboardingTourOpen, setIsOnboardingTourOpen] = useState(() => {
    return !localStorage.getItem('oqila_onboarded');
  });

  // Check if first-time onboarding is needed (runs once on first bot launch)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has('reset') || params.has('fresh')) {
      localStorage.clear();
      window.location.replace(window.location.pathname);
      return;
    }

    const saved = localStorage.getItem('oqila_profile');
    if (!saved) {
      setIsOnboarding(true);
    }
  }, []);

  const handleSaveProfile = (newProfile) => {
    setProfile(newProfile);
    localStorage.setItem('oqila_profile', JSON.stringify(newProfile));
    setIsOnboarding(false);
  };

  // Initialize Telegram WebApp & Listen to dynamic theme changes
  useEffect(() => {
    initTelegram();
    applyTheme(theme);

    // Subscribe to Telegram's dynamic themeChanged event
    subscribeToThemeChanges((newTheme) => {
      setTheme(newTheme);
      applyTheme(newTheme);
    });
  }, []);

  const handleSetLang = (newLang) => {
    setLang(newLang);
    localStorage.setItem('oqila_lang', newLang);
  };

  const handleToggleTheme = () => {
    hapticImpact('light');
    let nextTheme = 'light';
    if (theme === 'light') nextTheme = 'eastern';
    else if (theme === 'eastern') nextTheme = 'dark';
    else nextTheme = 'light';

    setTheme(nextTheme);
    applyTheme(nextTheme);
    localStorage.setItem('oqila_theme', nextTheme);
  };

  const t = translations[lang] || translations.ru;

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#090d16] selection:bg-brand-500 selection:text-white transition-colors duration-200">
      {/* Top Header with Theme Switch & Lang Switch & History & Profile */}
      <Header 
        lang={lang} 
        setLang={handleSetLang} 
        theme={theme} 
        toggleTheme={handleToggleTheme} 
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenProfile={() => {
          setIsOnboarding(false);
          setIsProfileOpen(true);
        }}
        profile={profile}
        t={t} 
      />

      {/* Main Content Area — all tabs are always mounted to preserve state (chat sessions, etc.) */}
      <main className="flex-1 max-w-md w-full mx-auto p-4 pb-nav">
        <div style={{ display: activeTab === 'studio' ? 'block' : 'none' }}>
          <TabStudio 
            lang={lang} 
            t={t} 
            profile={profile}
            onOpenHistory={() => setIsHistoryOpen(true)}
            externalCardToLoad={selectedHistoryCard}
          />
        </div>
        <div style={{ display: activeTab === 'finance' ? 'block' : 'none' }}>
          <TabFinance 
            lang={lang} 
            t={t} 
            profile={profile}
            onOpenProfile={() => {
              setIsOnboarding(false);
              setIsProfileOpen(true);
            }}
          />
        </div>
        <div style={{ display: activeTab === 'legal' ? 'block' : 'none' }}>
          <TabLegal 
            lang={lang} 
            t={t} 
            profile={profile}
            onOpenProfile={() => {
              setIsOnboarding(false);
              setIsProfileOpen(true);
            }}
          />
        </div>
        <div style={{ display: activeTab === 'about' ? 'block' : 'none' }}>
          <TabAbout 
            lang={lang} 
            t={t} 
            onOpenOnboardingTour={() => setIsOnboardingTourOpen(true)}
          />
        </div>
      </main>

      {/* Floating Bottom Navigation */}
      <BottomNav activeTab={activeTab} setActiveTab={setActiveTab} t={t} />

      {/* History Modal (Мои товары & Каталог) */}
      <HistoryModal
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectCard={(card) => {
          setSelectedHistoryCard(card);
          setActiveTab('studio');
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        t={t}
        lang={lang}
      />

      {/* Interactive Onboarding Tour Modal (Item 6) */}
      <OnboardingModal
        isOpen={isOnboardingTourOpen}
        onClose={() => setIsOnboardingTourOpen(false)}
        t={t}
        lang={lang}
      />

      {/* Profile Modal */}
      <ProfileModal
        isOpen={isProfileOpen}
        onClose={() => setIsProfileOpen(false)}
        isOnboarding={isOnboarding}
        profile={profile}
        onSave={handleSaveProfile}
        lang={lang}
        t={t}
      />
    </div>
  );
}
