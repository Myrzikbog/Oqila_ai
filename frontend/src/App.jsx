import React, { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import Header from './components/Header';
import BottomNav from './components/BottomNav';
import { translations } from './utils/i18n';
import { loginWithBackend, saveLangToBackend } from './utils/auth';
import { clearStorage, readJson, readStorage, writeStorage } from './utils/storage';
import {
  initTelegram,
  getInitialTheme,
  applyTheme,
  subscribeToThemeChanges,
  hapticImpact,
} from './utils/telegram';

// Every tab is loaded when it is first opened, so the main chunk holds only the shell (header, navigation, auth).
const TabStudio = lazy(() => import('./components/TabStudio'));
const TabFinance = lazy(() => import('./components/TabFinance'));
const TabUzum = lazy(() => import('./components/TabUzum'));
const TabLegal = lazy(() => import('./components/TabLegal'));
const TabAbout = lazy(() => import('./components/TabAbout'));
const HistoryModal = lazy(() => import('./components/HistoryModal'));
const ProfileModal = lazy(() => import('./components/ProfileModal'));
const OnboardingModal = lazy(() => import('./components/OnboardingModal'));

const TABS = ['studio', 'finance', 'uzum', 'legal', 'about'];

function TabFallback() {
  return <div className="py-10 text-center text-xs text-slate-500 dark:text-slate-400" role="status" aria-busy="true">…</div>;
}

export default function App() {
  const [lang, setLang] = useState(() => {
    try {
      const urlLang = new URLSearchParams(window.location.search).get('lang');
      if (urlLang && ['ru', 'uz'].includes(urlLang)) {
        writeStorage('oqila_lang', urlLang);
        return urlLang;
      }
    } catch { /* no window.location.search */ }
    return readStorage('oqila_lang') || 'uz';
  });
  const [theme, setTheme] = useState(getInitialTheme);
  const [activeTab, setActiveTab] = useState(() => {
    try {
      const tab = new URLSearchParams(window.location.search).get('tab');
      if (tab && TABS.includes(tab)) return tab;
    } catch { /* no window.location.search */ }
    return 'studio';
  });
  // A tab is mounted the first time it is opened and then stays mounted, so its state (a chat, a form) survives
  const [visited, setVisited] = useState(() => new Set([activeTab]));
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [selectedHistoryCard, setSelectedHistoryCard] = useState(null);
  const [userId, setUserId] = useState(null);

  const [profile, setProfile] = useState(() => readJson('oqila_profile', null));
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isOnboarding, setIsOnboarding] = useState(false);
  const [isOnboardingTourOpen, setIsOnboardingTourOpen] = useState(() => !readStorage('oqila_onboarded'));

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  // Authenticate user with database upon launch
  useEffect(() => {
    loginWithBackend(profile).then((authRes) => {
      if (authRes && authRes.profile) {
        setUserId(authRes.user_id);
        const serverProfile = authRes.profile;
        setProfile((prev) => {
          const merged = { ...(prev || {}), ...serverProfile };
          writeStorage('oqila_profile', JSON.stringify(merged));
          return merged;
        });
        if (serverProfile.lang && ['ru', 'uz'].includes(serverProfile.lang)) {
          setLang(serverProfile.lang);
          writeStorage('oqila_lang', serverProfile.lang);
        }
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- once, with the profile cached at start
  }, []);

  // First launch: reset links, and the profile form (it opens after the intro tour)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.has('reset') || params.has('fresh')) {
      clearStorage();
      window.location.replace(window.location.pathname);
      return;
    }
    if (!readStorage('oqila_profile')) setIsOnboarding(true);
  }, []);

  const handleSaveProfile = (newProfile) => {
    setProfile(newProfile);
    writeStorage('oqila_profile', JSON.stringify(newProfile));
    setIsOnboarding(false);
  };

  // Telegram WebApp and the theme (Telegram's and the system's changes are followed until unmount)
  useEffect(() => {
    initTelegram();
    applyTheme(theme);
    return subscribeToThemeChanges((newTheme) => {
      setTheme(newTheme);
      applyTheme(newTheme);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps -- subscribe once; `theme` only seeds applyTheme
  }, []);

  const handleSetLang = (newLang) => {
    setLang(newLang);
    writeStorage('oqila_lang', newLang);
    saveLangToBackend(newLang); // the server keeps it: the next sign-in (and the bot) use the same language
  };

  const handleToggleTheme = () => {
    hapticImpact('light');
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    applyTheme(nextTheme);
    writeStorage('oqila_theme', nextTheme);
  };

  const handleSetTab = useCallback((tab) => {
    setActiveTab(tab);
    setVisited((prev) => (prev.has(tab) ? prev : new Set(prev).add(tab)));
  }, []);

  const openProfile = () => {
    setIsOnboarding(false);
    setIsProfileOpen(true);
  };

  const t = translations[lang] || translations.ru;
  const show = (tab) => ({ display: activeTab === tab ? 'block' : 'none' });

  return (
    <div className="min-h-[var(--tg-viewport-stable-height,100vh)] flex flex-col bg-slate-50 dark:bg-[#090d16] selection:bg-brand-500 selection:text-white transition-colors duration-200">
      <Header
        lang={lang}
        setLang={handleSetLang}
        theme={theme}
        toggleTheme={handleToggleTheme}
        onOpenHistory={() => setIsHistoryOpen(true)}
        onOpenProfile={openProfile}
        profile={profile}
        t={t}
      />

      <main className="flex-1 max-w-md w-full mx-auto p-4 pb-nav">
        <Suspense fallback={<TabFallback />}>
          {visited.has('studio') && (
            <div style={show('studio')}>
              <TabStudio
                lang={lang}
                t={t}
                profile={profile}
                onOpenHistory={() => setIsHistoryOpen(true)}
                externalCardToLoad={selectedHistoryCard}
              />
            </div>
          )}
          {visited.has('finance') && (
            <div style={show('finance')}>
              <TabFinance lang={lang} t={t} profile={profile} onOpenProfile={openProfile} />
            </div>
          )}
          {visited.has('uzum') && (
            <div style={show('uzum')}>
              <TabUzum lang={lang} t={t} profile={profile} />
            </div>
          )}
          {visited.has('legal') && (
            <div style={show('legal')}>
              <TabLegal lang={lang} t={t} profile={profile} onOpenProfile={openProfile} />
            </div>
          )}
          {visited.has('about') && (
            <div style={show('about')}>
              <TabAbout lang={lang} t={t} onOpenOnboardingTour={() => setIsOnboardingTourOpen(true)} />
            </div>
          )}
        </Suspense>
      </main>

      <BottomNav activeTab={activeTab} setActiveTab={handleSetTab} t={t} />

      <Suspense fallback={null}>
        {(isHistoryOpen || selectedHistoryCard) && (
          <HistoryModal
            isOpen={isHistoryOpen}
            onClose={() => setIsHistoryOpen(false)}
            onSelectCard={(card) => {
              setSelectedHistoryCard(card);
              handleSetTab('studio');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            t={t}
            lang={lang}
          />
        )}
        {isOnboardingTourOpen && (
          <OnboardingModal
            isOpen={isOnboardingTourOpen}
            onClose={() => setIsOnboardingTourOpen(false)}
            t={t}
            lang={lang}
          />
        )}
        {(isProfileOpen || (isOnboarding && !isOnboardingTourOpen)) && (
          <ProfileModal
            isOpen
            onClose={() => { setIsProfileOpen(false); setIsOnboarding(false); }}
            isOnboarding={isOnboarding}
            profile={profile}
            userId={userId}
            onSave={handleSaveProfile}
            lang={lang}
            t={t}
          />
        )}
      </Suspense>
    </div>
  );
}
