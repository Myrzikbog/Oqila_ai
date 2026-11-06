import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Scale,
  Send,
  ExternalLink,
  Bot,
  User,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  KeyRound,
  Building2,
  UserCheck,
  Award,
  Receipt,
  ShoppingBag,
  FileText,
  BookOpen,
  Sparkles,
  Clock,
  Banknote,
  AlertTriangle,
  CheckCircle2,
  RotateCcw
} from 'lucide-react';
import { hapticImpact, hapticNotify } from '../utils/telegram';

// ---------------------------------------------------------------------------
// Static FAQ Data (Official Uzbekistan Procedures 2025-2026)
// ---------------------------------------------------------------------------

const FAQ_RU = [
  {
    id: 'ecert',
    icon: KeyRound,
    color: 'violet',
    title: 'Как получить ЭЦП (электронную цифровую подпись / E-IMZO)?',
    badge: '7% БРВ • Необходима для ЯТТ',
    timeline: '10–15 минут онлайн',
    fee: '≈7% БРВ = ~30 800 сум (для физлиц, точная сумма — при оплате)',
    steps: [
      'Зайдите на официальный портал e-imzo.uz и скачайте программный модуль E-IMZO для вашей системы (Windows/macOS/Android/iOS).',
      'Установите и запустите модуль E-IMZO. Нажмите «Получить сертификат ключа ЭЦП».',
      'Введите серию и номер паспорта / ID-карты и дату рождения.',
      'Пройдите биометрическую идентификацию Face ID со смартфона или обратитесь лично в Центр государственных услуг (ЦГУ).',
      'После подтверждения личности система сформирует счёт на оплату (около 7% БРВ, ~30 800 сум; точная сумма показывается при оплате). Оплатите через Click, Payme или Apelsin.',
      'Сертификат ключа ЭЦП генерируется онлайн и сохраняется в виде защищённого файла .pfx с вашим паролем на срок 2 года.',
      'ЭЦП физлица используется для авторизации на fo.birdarcha.uz (открытие ЯТТ), my.gov.uz, my.soliq.uz и подписания оферты Uzum Market.',
    ],
    links: [
      { label: 'e-imzo.uz — Портал E-IMZO', url: 'https://e-imzo.uz' },
      { label: 'my.gov.uz — Госуслуги', url: 'https://my.gov.uz' },
    ],
    law: 'Закон Республики Узбекистан «Об электронной цифровой подписи» (№ ЗРУ-793 от 12.10.2022)',
    tip: '💡 ЭЦП платная: около 7% БРВ (~30 800 сум) для физических лиц и около 10% БРВ для юрлиц и ЯТТ. С 2026 года при первичном получении ID-карты ЭЦП создаётся бесплатно. Ключ действует 2 года.',
  },
  {
    id: 'yatt',
    icon: Building2,
    color: 'amber',
    title: 'Как открыть ЯТТ (Индивидуальный предприниматель)?',
    badge: 'Обязательно для торговли и перепродажи',
    timeline: '15–30 минут онлайн',
    fee: '0.9 БРВ = ~396 000 сум (со скидкой онлайн 10%)',
    steps: [
      'Убедитесь в наличии действующего ключа ЭЦП (E-IMZO).',
      'Перейдите на автоматизированную систему регистрации бизнеса fo.birdarcha.uz или на my.gov.uz.',
      'Авторизуйтесь с помощью ЭЦП, выберите пункт «Государственная регистрация индивидуального предпринимателя».',
      'Заполните анкету: укажите домашний адрес (место жительства), телефон и e-mail.',
      'Выберите код вида экономической деятельности (ОКЭД): для интернет-торговли и Uzum — 47.91 («Розничная торговля по почте или через Интернет»), для розничного магазина/рынка — 47.11 или 47.19.',
      'Оплатите государственную пошлину через Click, Payme или банковскую карту: онлайн — 0,9 БРВ (396 000 сум), в Центре госуслуг — 1 БРВ.',
      'Свидетельство о государственной регистрации ЯТТ с уникальным QR-кодом формируется моментально в личном кабинете.',
    ],
    links: [
      { label: 'fo.birdarcha.uz — Единый портал регистрации бизнеса', url: 'https://fo.birdarcha.uz' },
      { label: 'my.gov.uz — Регистрация через Госуслуги', url: 'https://my.gov.uz' },
    ],
    law: 'Порядок государственной регистрации субъектов предпринимательства (ПКМ № 66 от 09.02.2017; Закон «О гарантиях свободы предпринимательской деятельности» в ред. ЗРУ-328)',
    tip: '⚠️ Если вы закупаете товары (Китай, 1688, Taobao, оптовые рынки) для перепродажи — открывайте ЯТТ. С 2026 года обычная розничная торговля исключена из перечня самозанятых (УП-50), а Uzum принимает самозанятых только с товарами собственного производства.',
  },
  {
    id: 'self_employed',
    icon: UserCheck,
    color: 'emerald',
    title: 'Как оформить самозанятость (O\'z-o\'zini band qilish)?',
    badge: 'Только для хэндмейда, пошива и услуг',
    timeline: '5 минут через мобильное приложение',
    fee: 'Бесплатно (0 сум)',
    steps: [
      'Скачайте мобильное приложение «Soliq» из App Store или Google Play.',
      'Авторизуйтесь по номеру телефона, пройдите биометрическую идентификацию Face ID.',
      'В меню выберите «O\'z-o\'zini band qilish» (Регистрация самозанятых).',
      'Выберите вид деятельности из перечня: с 1 января 2026 года в нём 72 пункта (Указ № УП-50). Например, пошив, ремёсла, домашняя выпечка, репетиторство. Парикмахерские и косметологические услуги, фото- и видеосъёмка и обычная розничная торговля из перечня исключены.',
      'Подтвердите данные — электронная справка с QR-кодом формируется моментально.',
      'Скачайте справку самозанятого: она является официальным документом для открытия бизнес-карт, работы с клиентами и выхода на Uzum Market со своей продукцией.',
    ],
    links: [
      { label: 'my.soliq.uz — Портал налоговых услуг', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Мобильное приложение Soliq', url: 'https://soliq.uz/mobile' },
    ],
    law: 'Постановление Президента РУз № ПП-4742 от 08.06.2020; Указ Президента № УП-50 от 19.03.2025 (перечень видов деятельности с 01.01.2026)',
    tip: '💡 Главные правила самозанятости: 1) С 1 января 2026 года налог с оборота — 1% с первого сума (Закон № ЗРУ-1108); 2) Соцналог — добровольно не менее 1 БРВ (440 000 сум) в год для стажа; 3) Нанимать сотрудников по трудовому договору нельзя; 4) Обычная розничная торговля исключена из перечня; продажа на электронных площадках разрешена (п. 33), но Uzum требует товары собственного производства.',
  },
  {
    id: 'uzum',
    icon: ShoppingBag,
    color: 'purple',
    title: 'Как стать продавцом на Uzum Market? (ЯТТ vs Самозанятый)',
    badge: 'Электронная коммерция',
    timeline: '2–4 рабочих дня',
    fee: 'Регистрация бесплатная (комиссия по тарифам Uzum, примерно 8–15%)',
    steps: [
      'ОПРЕДЕЛИТЕСЬ С ВАШИМ СТАТУСОМ:',
      '• Если вы производите товар сами (хэндмейд, пошив, ремесло) — можно продавать на Uzum как самозанятый. Документы: паспорт, QR-справка из Soliq, личная сумовая карта.',
      '• Если вы перепродаёте товары (Китай, оптовые закупки, электроника, одежда чужих фабрик) — по правилам Uzum нужен ЯТТ или ООО. Документы: свидетельство ЯТТ, паспорт, расчётный счёт в банке.',
      'Зайдите на seller.uzum.uz и подайте заявку на открытие магазина.',
      'Загрузите подтверждающие документы и подпишите электронный договор оферты.',
      'Uzum работает по договору комиссии (продавец — комитент, Uzum — комиссионер): выручку и налог с оборота учитывайте со всей суммы продажи, а комиссию — как свой расход.',
      'Создайте карточки товаров, упакуйте партию по регламенту Uzum и передайте на склад маркетплейса.',
    ],
    links: [
      { label: 'seller.uzum.uz — Портал для продавцов Uzum', url: 'https://seller.uzum.uz' },
      { label: 'partner.uzum.uz — База знаний Uzum', url: 'https://partner.uzum.uz' },
    ],
    law: 'Закон Республики Узбекистан «Об электронной коммерции» (№ ЗРУ-792 от 29.09.2022); Налоговый кодекс РУз (ст. 467 в ред. ЗРУ-1108)',
    tip: '⚡ Ставка налога с оборота для ЯТТ и самозанятых — 1%. Uzum налог за вас не удерживает: вы платите его сами со всей суммы продажи ежемесячно до 15 числа. Выплаты от Uzum поступают на расчётный счёт (ЯТТ) или банковскую карту (самозанятые).',
  },
  {
    id: 'bank_account',
    icon: Building2,
    color: 'sky',
    title: 'Как открыть банковский счёт для бизнеса в Узбекистане?',
    badge: 'Онлайн за 1–3 дня',
    timeline: '1–3 рабочих дня онлайн',
    fee: 'Открытие: 0 сум; обслуживание: 0–50 000 сум/мес',
    steps: [
      'РАЗНИЦА МЕЖДУ ЯТТ И САМОЗАНЯТЫМИ:',
      '• ДЛЯ САМОЗАНЯТЫХ: отдельный расчетный счет юрлица НЕ ТРЕБУЕТСЯ! Вы можете принимать оплату на любую личную сумовую карту (Uzcard/Humo) или открыть удобную «бизнес-карту самозанятого» в Kapitalbank, Anorbank, TBC, Agrobank.',
      '• ДЛЯ ЯТТ: отдельный расчётный счёт (20208...) обычно нужен для оптовых закупок, эквайринга Click/Payme и торговли на маркетплейсах — уточните требования банка и площадки.',
      'Как открыть счёт ЯТТ онлайн: скачайте бизнес-приложение выбранного банка (например, Kapitalbank Business, Anor Business, Ipoteka-Retail).',
      'Загрузите скан паспорта / ID-карты и свидетельство о регистрации ЯТТ из fo.birdarcha.uz (ИНН подтягивается автоматически).',
      'Пройдите видеоидентификацию в приложении банка — счёт активируется за 1–3 рабочих дня.',
      'Получите выписку с реквизитами (20-значный счёт 20208..., МФО банка, ИНН) — эти данные указываются в договоре с Uzum Market и эквайрингом.',
    ],
    links: [
      { label: 'kapitalbank.uz — Kapitalbank Business', url: 'https://kapitalbank.uz' },
      { label: 'anorbank.uz — Anorbank Business', url: 'https://anorbank.uz' },
    ],
    law: 'Инструкция Центрального банка РУз о порядке открытия, ведения и закрытия банковских счетов (рег. МЮ № 3420 от 08.02.2023)',
    tip: '💡 Деньги от продаж на маркетплейсах и через эквайринг Click/Payme зачисляются на ваш банковский счёт. Доход ЯТТ облагается налогом с оборота; порядок вывода средств на личную карту уточните в своём банке.',
  },
  {
    id: 'hunarmand',
    icon: Award,
    color: 'rose',
    title: 'Как получить сертификат Хунарманд (мастера-ремесленника)?',
    badge: 'Льготы для ремесленников',
    timeline: '7–14 рабочих дней',
    fee: 'Вступительный и членский взнос в ассоциацию',
    steps: [
      'Проверьте, входит ли ваше направление в официальный перечень видов ремесленнической деятельности (керамика, резьба по дереву, чеканка, вышивка сюзане, национальный текстиль, ювелирное дело).',
      'Подготовьте портфолио: качественные фотографии ваших изделий, описание техники изготовления, сертификаты об участии в выставках (при наличии).',
      'Подайте онлайн-заявление на членство через сайт hunarmand.uz или обратитесь в районное отделение ассоциации «Хунарманд».',
      'Экспертный совет оценит художественную и ремесленную ценность ваших работ.',
      'После одобрения и оплаты членского взноса вам выдаётся официальное свидетельство члена ассоциации «Хунарманд».',
      'Членство даёт доступ к льготам для ремесленников (льготные кредиты, участие в ярмарках и др.). Действующие налоговые льготы уточните в ассоциации и на soliq.uz.',
    ],
    links: [
      { label: 'hunarmand.uz — Сайт «Хунарманд»', url: 'https://hunarmand.uz' },
    ],
    law: 'Указ Президента РУз № УП-5242 от 17.11.2017 «О мерах по дальнейшему развитию ремесленничества и всемерной поддержке ремесленников»',
    tip: '✨ С 2026 года налоги для ЯТТ и самозанятых изменились (ЗРУ-1108), поэтому прежние льготы ремесленников могли измениться — перед расчётами уточните их в ассоциации «Хунарманд» и на soliq.uz.',
  },
  {
    id: 'kkm',
    icon: Receipt,
    color: 'teal',
    title: 'Нужна ли онлайн-касса (Онлайн-ККМ) и чек покупателю?',
    badge: 'Фискальные чеки',
    timeline: '1–2 дня',
    fee: 'Бесплатно со смартфона (Soliq QR) или аренда кассы',
    steps: [
      'По правилам каждый расчет с покупателем (наличными или картой) обязан сопровождаться выдачей фискального чека.',
      'САМЫЙ ПРОСТОЙ СПОСОБ ДЛЯ ЯТТ: используйте бесплатную функцию «Виртуальная касса / Soliq QR» в мобильном приложении «Soliq». Вы вбиваете сумму продажи со смартфона — формируется электронный фискальный чек с QR-кодом.',
      'ДЛЯ ТОРГОВЛИ В INSTAGRAM/TELEGRAM: при подключении Click Merchant или Payme Business фискальные чеки формируются АВТОМАТИЧЕСКИ через интеграцию с ОФД при каждой онлайн-оплате.',
      'ДЛЯ СТАЦИОНАРНОГО МАГАЗИНА: приобретите или возьмите в аренду онлайн-ККМ у аккредитованного ЦТО, зарегистрируйте её через my.soliq.uz.',
      'САМОЗАНЯТЫЕ: чек можно сформировать в приложении Soliq; требования к кассе для своего вида деятельности уточните на soliq.uz.',
    ],
    links: [
      { label: 'my.soliq.uz — Регистрация онлайн-ККМ', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Приложение Soliq', url: 'https://soliq.uz/mobile' },
    ],
    law: 'Порядок применения онлайн-ККМ и системы виртуальной кассы (ПКМ № 943 от 23.11.2019)',
    tip: '💡 За невыдачу чека или неприменение кассовой техники предусмотрены штрафы. Работайте открыто: используйте бесплатный QR-чек в приложении Soliq или Click/Payme.',
  },
  {
    id: 'taxes_overview',
    icon: Banknote,
    color: 'indigo',
    title: 'Сколько и когда платить налоги? Налоговый календарь ЯТТ и самозанятых',
    badge: 'Налоговый кодекс РУз (1%)',
    timeline: 'Ежемесячно до 15-го числа',
    fee: '1 БРВ соцналог + 1% от выручки',
    steps: [
      '📌 1. ЕЖЕМЕСЯЧНО ДО 15 ЧИСЛА СЛЕДУЮЩЕГО МЕСЯЦА — налог с оборота 1%:',
      '   • С 1 января 2026 года (Закон № ЗРУ-1108, ст. 467 НК) ставка для ЯТТ и самозанятых — 1%; закон установил её для дохода до 1 млрд сум в год;',
      '   • Налог считается со всей выручки; отчёт и уплата — до 15 числа месяца, следующего за отчётным (ст. 470 НК);',
      '   • При продажах через Uzum налог тоже платите вы сами, со всей суммы продажи.',
      '📌 2. ЕЖЕМЕСЯЧНО ДО 15 ЧИСЛА — социальный налог ЯТТ:',
      '   • Не менее 1 БРВ (440 000 сум) за текущий месяц, обязательно для ЯТТ (ст. 408 ч. 1 НК).',
      '📌 3. ДО 15 ФЕВРАЛЯ — годовой расчёт по налогу с оборота.',
      '⚠️ ПОРОГ 12 000 БРВ (≈5,28 МЛРД СУМ): с 1 июня 2026 года при доходе свыше 12 000 БРВ в год — обязательный переход на НДС и налог на прибыль (Указ № УП-100). Прежний порог 1 млрд сум больше не применяется.',
      '💡 САМОЗАНЯТЫЕ: налог с оборота — 1% с первого сума (освобождение до 100 млн сум отменено с 01.01.2026). Соцналог — добровольно не менее 1 БРВ в год для стажа.',
    ],
    links: [
      { label: 'my.soliq.uz — Оплата налогов онлайн', url: 'https://my.soliq.uz' },
    ],
    law: 'Налоговый кодекс Республики Узбекистан (ст. 467, 470, 408, ред. ЗРУ-1108); Указ № УП-100 от 26.05.2026',
    tip: '📱 Оплачивать налоги удобнее всего онлайн: в приложении Soliq или через мобильный банкинг (Click, Payme, Apelsin) по ИНН за 1 минуту.',
  },
  {
    id: 'click_payme',
    icon: FileText,
    color: 'sky',
    title: 'Как подключить Click и Payme для приёма оплат онлайн?',
    badge: 'Эквайринг 1.5%',
    timeline: '1–3 рабочих дня',
    fee: 'Комиссия 1.5% с успешного платежа',
    steps: [
      'CLICK MERCHANT: зайдите на click.uz → «Для бизнеса» → «Подключить Click Merchant». Заполните электронную заявку (потребуются: свидетельство ЯТТ / справка самозанятого, паспорт, банковские реквизиты).',
      'PAYME BUSINESS: перейдите на business.payme.uz, создайте личный кабинет мерчанта и загрузите документы.',
      'СПОСОБЫ ПРИЁМА ОПЛАТ:',
      '• Платежная ссылка (Инвойс): создавайте ссылку на оплату прямо в кабинете Click/Payme и отправляйте клиенту в Telegram/Instagram;',
      '• QR-код на кассе: распечатайте статичный QR-код мерчанта для оффлайн-точки;',
      '• Интеграция в Telegram-бот: подключите платежный API Click/Payme для автоматической оплаты в боте.',
      'Деньги зачисляются на ваш банковский счёт на следующий рабочий день.',
      'Каждая операция через Click/Payme автоматически фискализируется в налоговых органах — чек выбивается автоматически.',
    ],
    links: [
      { label: 'click.uz — Подключение Click Merchant', url: 'https://click.uz' },
      { label: 'business.payme.uz — Личный кабинет Payme', url: 'https://business.payme.uz' },
    ],
    law: 'Закон Республики Узбекистан «О платежах и платежных системах»',
    tip: '💡 Для продаж через Telegram или Instagram проще всего использовать платежные ссылки Click Merchant: покупатель нажимает на ссылку, оплачивает картой Uzcard/Humo/Visa, а вам и клиенту мгновенно приходит электронный чек.',
  },
];

const FAQ_UZ = [
  {
    id: 'ecert',
    icon: KeyRound,
    color: 'violet',
    title: 'ERI (Elektron raqamli imzo / E-IMZO) kalitini qanday olish mumkin?',
    badge: '7% BHM • YaTT uchun majburiy',
    timeline: '10–15 daqiqa onlayn',
    fee: '≈7% BHM = ~30 800 so\'m (jismoniy shaxslar uchun, aniq summa to\'lovda ko\'rinadi)',
    steps: [
      'Rasmiy e-imzo.uz portaliga kiring va operatsion tizimingiz (Windows/macOS/Android/iOS) uchun E-IMZO modulini yuklab oling.',
      'Modulni o\'rnating va «ERI kalitini olish» bo\'limini tanlang.',
      'Pasport yoki ID-karta seriyasi, raqami hamda tug\'ilgan sanangizni kiriting.',
      'Smartfoningiz orqali Face ID (biometrik qiyofani aniqlash)dan o\'ting yoki Davlat xizmatlari markaziga (DXM) shaxsan murojaat qiling.',
      'Ma\'lumotlar tasdiqlangach, tizim to\'lov hisobini shakllantiradi (taxminan 7% BHM, ~30 800 so\'m; aniq summa to\'lovda ko\'rinadi). Click, Payme yoki Apelsin orqali onlayn to\'lanadi.',
      'ERI sertifikati parolingiz bilan himoyalangan .pfx fayli ko\'rinishida 2 yil muddatga beriladi.',
      'Jismoniy shaxs ERIsi fo.birdarcha.uz, my.gov.uz, my.soliq.uz portallariga kirish va YaTT ochish uchun xizmat qiladi.',
    ],
    links: [
      { label: 'e-imzo.uz — Rasmiy E-IMZO portali', url: 'https://e-imzo.uz' },
      { label: 'my.gov.uz — Davlat xizmatlari portali', url: 'https://my.gov.uz' },
    ],
    law: 'O‘zbekiston Respublikasining «Elektron raqamli imzo to‘g‘risida»gi Qonuni (O‘RQ-793, 12.10.2022)',
    tip: '💡 ERI pullik: jismoniy shaxslar uchun taxminan 7% BHM (~30 800 so\'m), yuridik shaxslar va YaTT uchun taxminan 10% BHM. 2026-yildan ID-karta birinchi marta olinganda ERI bepul yaratiladi. Kalit 2 yil amal qiladi.',
  },
  {
    id: 'yatt',
    icon: Building2,
    color: 'amber',
    title: 'YaTT (Yakka tartibdagi tadbirkor) qanday ochiladi?',
    badge: 'Savdo va qayta sotish uchun majburiy',
    timeline: '15–30 daqiqa onlayn',
    fee: '0.9 BHM = ~396 000 so\'m (onlayn 10% chegirma)',
    steps: [
      'Amaldagi ERI (E-IMZO) kalitingiz borligiga ishonch hosil qiling.',
      'fo.birdarcha.uz yagona biznesni ro\'yxatdan o\'tkazish portaliga yoki my.gov.uz saytiga kiring.',
      'ERI orqali tizimga kirib, «Yakka tartibdagi tadbirkorni davlat ro\'yxatidan o\'tkazish» xizmatini tanlang.',
      'Yashash manzilingiz, telefon raqamingiz va elektron pochtangizni kiriting.',
      'Faoliyat turi (IFUT/OKED) kodini tanlang: internet orqali savdo va Uzum uchun — 47.91 («Pochta yoki Internet orqali chakana savdo»), bozor yoki do\'konda savdo uchun — 47.11 yoki 47.19.',
      'Davlat bojini Click, Payme yoki bank kartasi orqali to\'lang: onlayn — 0,9 BHM (396 000 so\'m), Davlat xizmatlari markazida — 1 BHM.',
      'To\'lov amalga oshirilishi bilanoq QR-kodli elektron YaTT guvohnomasi shaxsiy kabinetingizda tayyor bo\'ladi.',
    ],
    links: [
      { label: 'fo.birdarcha.uz — Biznesni ro\'yxatdan o\'tkazish portali', url: 'https://fo.birdarcha.uz' },
      { label: 'my.gov.uz — Yagona interaktiv davlat xizmatlari', url: 'https://my.gov.uz' },
    ],
    law: 'Tadbirkorlik subyektlarini davlat ro‘yxatidan o‘tkazish tartibi (VMQ № 66, 09.02.2017; O‘RQ-328 tahriridagi «Tadbirkorlik faoliyati erkinligining kafolatlari to‘g‘risida»gi Qonun)',
    tip: '⚠️ Tovarlarni qayta sotish uchun olsangiz (Xitoy, 1688, Taobao, ulgurji bozorlar) — YaTT oching. 2026-yildan oddiy chakana savdo o\'z-o\'zini band qilganlar ro\'yxatidan chiqarilgan (PF-50), Uzum esa o\'z-o\'zini band qilganlarni faqat o\'zi ishlab chiqargan mahsulot bilan qabul qiladi.',
  },
  {
    id: 'self_employed',
    icon: UserCheck,
    color: 'emerald',
    title: 'O\'z-o\'zini band qilish qanday rasmiylashtiriladi?',
    badge: 'Faqat handmade, tikuvchilik va xizmatlar uchun',
    timeline: '5 daqiqa (mobil ilovada)',
    fee: 'Mutlaqo bepul (0 so\'m)',
    steps: [
      'App Store yoki Google Play orqali rasmiy «Soliq» mobil ilovasini yuklab oling.',
      'Telefon raqamingiz orqali kiring va Face ID biometrik tekshiruvidan o\'ting.',
      'Menyudan «O\'z-o\'zini band qilish» xizmatini tanlang.',
      'Ro\'yxatdan faoliyat turini tanlang: 2026-yil 1-yanvardan unda 72 ta band bor (PF-50-son Farmon). Masalan, tikuvchilik, hunarmandchilik, uyda pishiriqlar, repetitorlik. Sartaroshlik va kosmetologiya xizmatlari, foto va videosuratga olish hamda oddiy chakana savdo ro\'yxatdan chiqarilgan.',
      'Ma\'lumotlarni tasdiqlang — QR-kodli elektron ma\'lumotnoma darhol shakllanadi.',
      'Ma\'lumotnomani yuklab oling: u bankda biznes-karta ochish, mijozlar va Uzum Market bilan ishlash uchun rasmiy hujjat hisoblanadi.',
    ],
    links: [
      { label: 'my.soliq.uz — Elektron soliq xizmatlari', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Soliq mobil ilovasi', url: 'https://soliq.uz/mobile' },
    ],
    law: 'O‘zbekiston Respublikasi Prezidentining PQ-4742-son qarori (08.06.2020); PF-50-son Farmoni (19.03.2025, 2026-yil 1-yanvardan faoliyat turlari ro‘yxati)',
    tip: '💡 Asosiy qoidalar: 1) 2026-yil 1-yanvardan aylanmadan soliq — birinchi so\'mdan 1% (O\'RQ-1108); 2) Ijtimoiy soliq: staj uchun ixtiyoriy, yiliga kamida 1 BHM; 3) Mehnat shartnomasi bilan ishchi yollash mumkin emas; 4) Oddiy chakana savdo ro\'yxatdan chiqarilgan; elektron maydonchalarda sotish mumkin (33-band), ammo Uzum o\'zi ishlab chiqargan mahsulotni talab qiladi.',
  },
  {
    id: 'uzum',
    icon: ShoppingBag,
    color: 'purple',
    title: 'Uzum Market\'da sotuvchi qanday bo\'lish mumkin? (YaTT vs O\'z-o\'zini band qilgan)',
    badge: 'Elektron tijorat',
    timeline: '2–4 ish kuni',
    fee: 'Ro\'yxatdan o\'tish bepul (komissiya Uzum tariflari bo\'yicha, taxminan 8–15%)',
    steps: [
      'MAQOMINGIZNI ANQLANG:',
      '• Agar mahsulotni o\'zingiz ishlab chiqarsangiz (handmade, tikuvchilik, kiyim, shirinliklar) — Uzum Market\'da o\'z-o\'zini band qilgan shaxs sifatida sotishingiz mumkin. Hujjatlar: pasport, Soliq QR-ma\'lumotnomasi, shaxsiy so\'m kartasi.',
      '• Agar tovarlarni qayta sotsangiz (Xitoy, fabrika, ulgurji bozor tovarlari) — Uzum qoidalariga ko\'ra YaTT yoki MChJ kerak. Hujjatlar: YaTT guvohnomasi, pasport, bankdagi hisobvaraq.',
      'seller.uzum.uz saytiga o\'ting va sotuvchi hisobini ochish uchun ariza topshiring.',
      'Kerakli hujjatlarni yuklab, oferta shartnomasini imzolang.',
      'Uzum komissiya shartnomasi asosida ishlaydi (sotuvchi — komitent, Uzum — komissioner): tushum va aylanmadan soliqni sotuvning to\'liq summasidan hisoblang, komissiyani esa xarajat sifatida.',
      'Mahsulot kartochkalarini to\'ldirib, Uzum qoidalariga ko\'ra qadoqlang va omborga topshiring.',
    ],
    links: [
      { label: 'seller.uzum.uz — Uzum sotuvchilar portali', url: 'https://seller.uzum.uz' },
      { label: 'partner.uzum.uz — Sotuvchilar uchun qo\'llanma', url: 'https://partner.uzum.uz' },
    ],
    law: 'O‘zbekiston Respublikasining «Elektron tijorat to‘g‘risida»gi Qonuni (O‘RQ-792, 29.09.2022); Soliq kodeksi (467-modda, O\'RQ-1108)',
    tip: '⚡ YaTT va o\'z-o\'zini band qilganlar uchun aylanmadan soliq stavkasi — 1%. Uzum soliqni siz uchun ushlab qolmaydi: uni sotuvning to\'liq summasidan har oy 15-sanagacha o\'zingiz to\'laysiz. Tushumlar YaTT hisobvarag\'iga yoki o\'z-o\'zini band qilgan shaxsning kartasiga tushadi.',
  },
  {
    id: 'bank_account',
    icon: Building2,
    color: 'sky',
    title: 'Biznes uchun bankda hisobvaraq qanday ochiladi?',
    badge: '1–3 kunda onlayn',
    timeline: '1–3 ish kuni onlayn',
    fee: 'Ochish: 0 so\'m; xizmat ko\'rsatish: 0–50 000 so\'m/oy',
    steps: [
      'YaTT VA O\'Z-O\'ZINI BAND QILGANLAR O\'RTASIDAGI FARQ:',
      '• O\'Z-O\'ZINI BAND QILGANLAR: alohida yuridik hisobvaraq ochish SHART EMAS! Har qanday shaxsiy so\'m kartangizdan (Uzcard/Humo) yoki banklarda o\'z-o\'zini band qiluvchilar uchun maxsus biznes-kartadan foydalanishingiz mumkin.',
      '• YaTT UCHUN: alohida 20208... hisobvarag\'i odatda ulgurji xaridlar, Click/Payme ekvayring va marketpleyslar uchun kerak bo\'ladi — bank va maydoncha talablarini aniqlang.',
      'YaTT hisobvarag\'ini onlayn ochish: tanlangan bankning biznes ilovasini yuklab oling (masalan, Kapitalbank Business, Anor Business, Ipoteka-Retail).',
      'Pasport/ID-karta va fo.birdarcha.uz\'dan olingan YaTT guvohnomasini yuklang (STIR avtomatik ravishda tekshiriladi).',
      'Ilovada video-identifikatsiyadan o\'ting — hisobvaraq 1–3 ish kunida faollashadi.',
      '20 xonali hisob raqami (20208...), MFO va STIR rekvizitlarini oling — bu ma\'lumotlar Uzum Market va ekvayring shartnomalariga kiritiladi.',
    ],
    links: [
      { label: 'kapitalbank.uz — Kapitalbank biznes hisob', url: 'https://kapitalbank.uz' },
      { label: 'anorbank.uz — Anorbank onlayn biznes', url: 'https://anorbank.uz' },
    ],
    law: 'O‘zbekiston Respublikasi Markaziy bankining Bank hisobvaraqlarini ochish, yuritish va yopish tartibi to‘g‘risidagi yo‘riqnomasi (AV ro‘yxat № 3420, 08.02.2023)',
    tip: '💡 YaTT daromadi aylanmadan soliqqa tortiladi; mablag\'ni shaxsiy kartangizga o\'tkazish tartibini bankingizdan aniqlang.',
  },
  {
    id: 'hunarmand',
    icon: Award,
    color: 'rose',
    title: 'Hunarmand sertifikati qanday olinadi?',
    badge: 'Hunarmandlar uchun imtiyozlar',
    timeline: '7–14 ish kuni',
    fee: 'Assotsiatsiyaga kirish va a\'zolik badali',
    steps: [
      'Faoliyatingiz xalq hunarmandchiligining rasmiy ro\'yxatiga (kulolchilik, yog\'och o\'ymakorligi, zardo\'zlik, milliy liboslar, so\'zana, zargarlik) kirishini tekshiring.',
      'Portfolio tayyorlang: buyumlaringizning sifatli fotosuratlari, tayyorlash uslubi va ko\'rgazmalardagi ishtirok sertifikatlari (mavjud bo\'lsa).',
      'hunarmand.uz veb-sayti orqali arizani onlayn yuboring yoki tuman «Hunarmand» uyushmasiga shaxsan boring.',
      'Ekspertlar kengashi buyumlaringizning badiiy va amaliy qimmatini baholaydi.',
      'A\'zolik tasdiqlanib, badal to\'langandan so\'ng «Hunarmand» uyushmasi a\'zolik guvohnomasi beriladi.',
      'A\'zolik hunarmandlar uchun imtiyozlardan (imtiyozli kreditlar, yarmarkalarda ishtirok va boshqalar) foydalanish imkonini beradi. Amaldagi soliq imtiyozlarini uyushma va soliq.uz orqali aniqlang.',
    ],
    links: [
      { label: 'hunarmand.uz — «Hunarmand» uyushmasi', url: 'https://hunarmand.uz' },
    ],
    law: 'O‘zbekiston Respublikasi Prezidentining PF-5242-son Farmoni (17.11.2017) — hunarmandchilikni yanada rivojlantirish va hunarmandlarni har tomonlama qo‘llab-quvvatlash chora-tadbirlari to‘g‘risida',
    tip: '✨ 2026-yildan YaTT va o\'z-o\'zini band qilganlar soliqlari o\'zgardi (O\'RQ-1108), shuning uchun hunarmandlarning avvalgi imtiyozlari o\'zgargan bo\'lishi mumkin — hisob-kitobdan oldin «Hunarmand» uyushmasi va soliq.uz orqali aniqlang.',
  },
  {
    id: 'kkm',
    icon: Receipt,
    color: 'teal',
    title: 'Onlayn-kassa (Onlayn-NKM) va xaridorga chek berish shartmi?',
    badge: 'Fiskal cheklar',
    timeline: '1–2 kun',
    fee: 'Smartfonda bepul (Soliq QR) yoki kassa apparati',
    steps: [
      'Qonunchilikka ko\'ra, aholi bilan har bir naqd yoki plastik kartadagi hisob-kitobda xaridorga fiskal chek berilishi shart.',
      'YaTT UCHUN ENG OSON YO\'L: «Soliq» ilovasida bepul «Virtual kassa / Soliq QR» xizmatidan foydalaning. Savdo summasini telefonga kiritasiz — QR-kodli elektron fiskal chek avtomatik shakllanadi.',
      'TELEGRAM VA INSTAGRAMDA SAVDO UCHUN: Click Merchant yoki Payme Business ulanganda, onlayn to\'lov o\'tishi bilan fiskal chek OFD tizimi orqali avtomatik tarzda yaratiladi.',
      'STATSIONAR DO\'KON UCHUN: akkreditatsiyadan o\'tgan markazlardan onlayn-NKM apparati xarid qiling yoki ijaraga olib, my.soliq.uz orqali ro\'yxatdan o\'tkazing.',
      'O\'Z-O\'ZINI BAND QILGANLAR: chekni Soliq ilovasida chiqarish mumkin; faoliyat turingiz bo\'yicha kassa talablarini soliq.uz saytida aniqlang.',
    ],
    links: [
      { label: 'my.soliq.uz — Onlayn-NKM ro\'yxatdan o\'tkazish', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Soliq mobil ilovasi', url: 'https://soliq.uz/mobile' },
    ],
    law: 'Onlayn nazorat-kassa mashinalari va virtual kassa tizimini qo‘llash tartibi (VMQ № 943, 23.11.2019)',
    tip: '💡 Chek bermaslik yoki kassa texnikasini qo\'llamaslik uchun qonunda jarima belgilangan. Biznesingizni xavf ostiga qo\'ymang: «Soliq» ilovasidagi bepul QR-chekdan yoki Click/Payme integratsiyasidan foydalaning.',
  },
  {
    id: 'taxes_overview',
    icon: Banknote,
    color: 'indigo',
    title: 'Qancha va qachon soliq to\'lash kerak? YaTT va o\'z-o\'zini band qilganlar soliq kalendari',
    badge: 'Soliq kodeksi (1%)',
    timeline: 'Har oyning 15-sanasigacha',
    fee: '1 BHM ijtimoiy soliq + 1% aylanmadan soliq',
    steps: [
      '📌 1. HAR OY KEYINGI OYNING 15-SANASIGACHA — 1% aylanmadan soliq:',
      '   • 2026-yil 1-yanvardan (O\'RQ-1108-son qonun, SK 467-modda) YaTT va o\'z-o\'zini band qilganlar uchun stavka — 1%; qonun uni yiliga 1 mlrd so\'mgacha daromad uchun belgilagan;',
      '   • Soliq butun tushumdan hisoblanadi; hisobot va to\'lov — hisobot oyidan keyingi oyning 15-sanasigacha (SK 470-modda);',
      '   • Uzum orqali sotganda ham soliqni sotuvning to\'liq summasidan o\'zingiz to\'laysiz.',
      '📌 2. HAR OYNING 15-SANASIGACHA — YaTT ijtimoiy solig\'i:',
      '   • Joriy oy uchun kamida 1 BHM (440 000 so\'m), YaTT uchun majburiy (SK 408-modda 1-qism).',
      '📌 3. 15-FEVRALGACHA — aylanmadan soliq bo\'yicha yillik hisob-kitob.',
      '⚠️ 12 000 BHM CHEGARASI (≈5,28 MLRD SO\'M): 2026-yil 1-iyundan yillik daromad 12 000 BHMdan oshsa — QQS va foyda solig\'iga majburiy o\'tiladi (PF-100-son Farmon). Avvalgi 1 mlrd so\'m chegarasi endi qo\'llanilmaydi.',
      '💡 O\'Z-O\'ZINI BAND QILGANLAR: aylanmadan soliq — birinchi so\'mdan 1% (100 mln so\'mgacha imtiyoz 2026-yildan bekor qilingan). Ijtimoiy soliq — staj uchun ixtiyoriy, yiliga kamida 1 BHM.',
    ],
    links: [
      { label: 'my.soliq.uz — Soliqlarni onlayn to\'lash', url: 'https://my.soliq.uz' },
    ],
    law: 'O‘zbekiston Respublikasi Soliq kodeksi (467, 470, 408-moddalar, O\'RQ-1108); PF-100-son Farmon (26.05.2026)',
    tip: '📱 Soliqlarni to\'lash juda oson: Soliq mobil ilovasida yoki Click/Payme ilovalarida STIR (INN) kiritilsa, hisoblangan soliqlar 1 daqiqada to\'lanadi.',
  },
  {
    id: 'click_payme',
    icon: FileText,
    color: 'sky',
    title: 'Click va Payme orqali to\'lov qabul qilishni qanday ulash mumkin?',
    badge: 'Ekvayring 1.5%',
    timeline: '1–3 ish kuni',
    fee: 'Har muvaffaqiyatli to\'lovdan 1.5% komissiya',
    steps: [
      'CLICK MERCHANT: click.uz → «Biznes uchun» → «Click Merchant ulash» bo\'limiga o\'ting. Ariza to\'ldiring (YaTT guvohnomasi / o\'z-o\'zini band qilish ma\'lumotnomasi, pasport va bank rekvizitlari kerak bo\'ladi).',
      'PAYME BUSINESS: business.payme.uz saytida ro\'yxatdan o\'tib, hujjatlarni yuklang.',
      'TO\'LOV QABUL QILISH USULLARI:',
      '• To\'lov havolasi (Invoys): shaxsiy kabinetda to\'lov linki yarating va Telegram/Instagram orqali xaridorga yuboring;',
      '• QR-kod: do\'kon peshtaxtasiga chiqarib qo\'yish uchun statik QR-kod;',
      '• Telegram-bot integratsiyasi: to\'lov API kalitlarini ulab, bot ichida to\'lovlarni avtomatlashtiring.',
      'Mablag\'lar keyingi ish kunida to\'g\'ridan-to\'g\'ri bank hisobvarag\'ingizga tushadi.',
      'Click va Payme har bir to\'lov bo\'yicha fiskal chekni OFDga avtomatik tarzda yuboradi — qo\'lda kassa urish shart emas.',
    ],
    links: [
      { label: 'click.uz — Click Merchant ulash', url: 'https://click.uz' },
      { label: 'business.payme.uz — Payme Business kabineti', url: 'https://business.payme.uz' },
    ],
    law: 'O‘zbekiston Respublikasining «To‘lovlar va to‘lov tizimlari to‘g‘risida»gi Qonuni',
    tip: '💡 Telegram va Instagram do\'konlar uchun Click Merchant eng qulay: xaridorga to\'lov linki yuboriladi, u o\'z kartasi orqali to\'laydi va sizga ham, xaridorga ham avtomatik chek keladi.',
  },
];

const BRAND_COLORS = {
  bg: 'bg-brand-50 dark:bg-teal-950',
  text: 'text-brand-700 dark:text-teal-300',
  badge: 'bg-brand-50 dark:bg-teal-950 text-brand-700 dark:text-teal-300 border-brand-200 dark:border-teal-800',
  border: 'border-brand-200 dark:border-teal-800',
};

// One brand colour for every topic: the icons identify the topic, so a rainbow adds nothing.
// (item.color is kept in the data but intentionally ignored.)
const COLOR_MAP = new Proxy({}, { get: () => BRAND_COLORS });

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------
export default function TabLegal({ lang, t, profile, onOpenProfile }) {
  const faqData = lang === 'uz' ? FAQ_UZ : FAQ_RU;
  const [openId, setOpenId] = useState(null);

  // Chat state — stored in component (persisted because App.jsx keeps this mounted)
  const initMessage = {
    role: 'assistant',
    text: lang === 'uz'
      ? `Assalomu alaykum${profile?.name ? `, ${profile.name.split(' ')[0]}` : ''}! 👋 Men OqilaLegal — O'zbekiston qonunchiligi bo'yicha sun'iy intellekt maslahatchisiman.\n\n**Menga quyidagi mavzularda savol berishingiz mumkin:**\n• YaTT va o'z-o'zini band qilishni ochish\n• Soliqlar: stavkalar, miqdorlar, muddatlar\n• ERI (elektron imzo) olish\n• Click/Payme ulash\n• Uzum Market'da sotuvchi bo'lish\n• Hunarmand sertifikati\n\nSavolingizni yozing! ✍️`
      : `Здравствуйте${profile?.name ? `, ${profile.name.split(' ')[0]}` : ''}! 👋 Я OqilaLegal — AI-консультант по законодательству Узбекистана.\n\n**Задайте вопрос о:**\n• Открытии ЯТТ или самозанятости\n• Налогах: ставки, суммы, сроки\n• Получении ЭЦП (E-IMZO)\n• Подключении Click/Payme\n• Регистрации продавца на Uzum Market\n• Сертификате Хунарманд\n\nПишите — разберёмся вместе! ✍️`,
  };

  const [messages, setMessages] = useState([initMessage]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  const handleSend = useCallback(async (questionText) => {
    const q = (questionText || inputValue).trim();
    if (!q || isSending) return;

    hapticImpact('medium');
    setInputValue('');
    setMessages((prev) => [...prev, { role: 'user', text: q }]);
    setIsSending(true);

    try {
      const res = await fetch('/api/legal-qa', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          question: q, 
          lang, 
          user_profile: profile 
        }),
      });
      const data = await res.json().catch(() => ({}));
      // A 429 carries a localized "too many requests" message in `detail`
      const fallback = lang === 'uz' ? "Kechirasiz, javob olishda xatolik." : "Ошибка при получении ответа.";
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.answer || (typeof data.detail === 'string' ? `⏳ ${data.detail}` : fallback) }
      ]);
      hapticNotify('success');
    } catch (err) {
      console.error(err);
      hapticNotify('error');
    } finally {
      setIsSending(false);
    }
  }, [inputValue, isSending, lang, profile]);

  const clearChat = () => {
    hapticImpact('medium');
    setMessages([initMessage]);
  };

  const QUICK_QUESTIONS_RU = [
    'Как открыть ЯТТ онлайн?',
    'Сколько налогов платит ЯТТ?',
    'Можно ли продавать китайские товары как самозанятый?',
    'Как получить ЭЦП?',
    'Нужна ли касса для Telegram-магазина?',
  ];

  const QUICK_QUESTIONS_UZ = [
    'YaTT qanday ochiladi?',
    'YaTT qancha soliq to\'laydi?',
    'O\'z-o\'zini band qilgan Xitoy tovarini sota oladimi?',
    'ERI qanday olinadi?',
    'Telegram-do\'kon uchun kassa kerakmi?',
  ];

  const quickQuestions = lang === 'uz' ? QUICK_QUESTIONS_UZ : QUICK_QUESTIONS_RU;

  return (
    <div className="space-y-4">
      {/* Header Banner */}
      <div className="glass-card rounded-2xl p-4 border-l-4 border-l-brand-600 dark:border-l-brand-400 bg-gradient-to-r from-teal-50/70 via-white to-white dark:from-teal-950/30 dark:via-slate-900 dark:to-slate-900">
        <div className="flex items-center space-x-2 text-brand-800 dark:text-teal-300">
          <Scale className="w-5 h-5 flex-shrink-0" />
          <h2 className="font-bold text-sm tracking-tight">{t.legal_title}</h2>
        </div>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
          {t.legal_subtitle}
        </p>
      </div>

      {/* User Profile Context Badge */}
      {profile && (
        <div className="flex items-center justify-between p-2.5 px-3.5 rounded-2xl bg-brand-50/80 dark:bg-teal-950/30 border border-brand-200/80 dark:border-teal-800/60 shadow-xs text-xs">
          <div className="flex items-center space-x-2 truncate">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse flex-shrink-0" />
            <span className="font-bold text-slate-800 dark:text-slate-200 truncate">
              {profile.name} • {profile.status === 'self_employed' 
                ? (lang === 'uz' ? "O'z-o'zini band qilish" : "Самозанятая") 
                : profile.status === 'yatt'
                ? (lang === 'uz' ? "YaTT" : "ЯТТ")
                : (lang === 'uz' ? "Rejalashtirish" : "Выбор статуса")}
            </span>
          </div>
          <button
            type="button"
            onClick={onOpenProfile}
            className="text-[11px] font-bold text-brand-700 dark:text-teal-300 hover:text-brand-900 dark:hover:text-teal-100 underline decoration-dotted flex-shrink-0 ml-2"
          >
            {lang === 'uz' ? "O'zgartirish" : "Настроить"}
          </button>
        </div>
      )}

      {/* Section: FAQ Accordion */}
      <div className="space-y-2">
        <div className="flex items-center space-x-2 px-1">
          <BookOpen className="w-4 h-4 text-brand-600 dark:text-teal-400" />
          <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200">
            {lang === 'uz' ? 'Poshagoma qo\'llanma — rasmiy tartiblar' : 'Пошаговые инструкции — официальные процедуры'}
          </h3>
        </div>

        {faqData.map((item) => {
          const Icon = item.icon;
          const colors = COLOR_MAP[item.color] || COLOR_MAP.teal;
          const isOpen = openId === item.id;

          return (
            <div
              key={item.id}
              className={`glass-card rounded-2xl transition-all border ${
                isOpen ? `${colors.border} shadow-soft` : 'border-slate-200/70 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700'
              }`}
            >
              {/* Accordion Header */}
              <button
                type="button"
                onClick={() => {
                  hapticImpact('light');
                  setOpenId(isOpen ? null : item.id);
                }}
                className="w-full p-3.5 flex items-center justify-between text-left"
              >
                <div className="flex items-center space-x-3 flex-1 min-w-0">
                  <div className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 ${colors.bg} ${colors.text}`}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-bold text-xs text-slate-900 dark:text-white leading-snug">{item.title}</h4>
                    <div className="flex items-center space-x-1.5 mt-0.5 flex-wrap gap-y-0.5">
                      <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-md border ${colors.badge}`}>
                        {item.badge}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-1.5 flex-shrink-0 ml-2">
                  {isOpen ? (
                    <ChevronUp className="w-4 h-4 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-4 h-4 text-slate-400" />
                  )}
                </div>
              </button>

              {/* Accordion Body */}
              {isOpen && (
                <div className="px-3.5 pb-4 pt-1 border-t border-slate-100 dark:border-slate-800 space-y-3">
                  {/* Meta: Timeline & Fee */}
                  <div className="flex items-center space-x-3 flex-wrap gap-y-1.5">
                    <div className="flex items-center space-x-1 text-[11px] text-slate-500 dark:text-slate-400">
                      <Clock className="w-3.5 h-3.5" />
                      <span><span className="font-bold text-slate-700 dark:text-slate-300">{lang === 'uz' ? 'Muddat:' : 'Срок:'}</span> {item.timeline}</span>
                    </div>
                    <div className="flex items-center space-x-1 text-[11px] text-slate-500 dark:text-slate-400">
                      <Banknote className="w-3.5 h-3.5" />
                      <span><span className="font-bold text-slate-700 dark:text-slate-300">{lang === 'uz' ? 'Narxi:' : 'Стоимость:'}</span> {item.fee}</span>
                    </div>
                  </div>

                  {/* Step-by-Step */}
                  <ol className="space-y-2">
                    {item.steps.map((step, idx) => (
                      <li key={idx} className="flex items-start space-x-2.5 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                        <span className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-black ${colors.bg} ${colors.text} mt-0.5`}>
                          {idx + 1}
                        </span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>

                  {/* Tip / Warning */}
                  {item.tip && (
                    <div className={`p-2.5 rounded-xl flex items-start space-x-2 text-[11px] leading-relaxed ${
                      item.tip.startsWith('⚠️')
                        ? 'bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200'
                        : item.tip.startsWith('⚡')
                        ? 'bg-teal-50 dark:bg-teal-950/30 border border-teal-200 dark:border-teal-800 text-teal-800 dark:text-teal-200'
                        : 'bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-800 text-blue-800 dark:text-blue-200'
                    }`}>
                      <Sparkles className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                      <span>{item.tip}</span>
                    </div>
                  )}

                  {/* Legal Reference Note */}
                  {item.law && (
                    <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200/80 dark:border-slate-800 flex items-start space-x-2 text-[11px] text-slate-600 dark:text-slate-300 leading-relaxed">
                      <Scale className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-slate-500 dark:text-slate-400" />
                      <div>
                        <span className="font-bold text-slate-700 dark:text-slate-200">{lang === 'uz' ? 'Huquqiy asos:' : 'Правовое основание:'} </span>
                        <span>{item.law}</span>
                      </div>
                    </div>
                  )}

                  {/* Official Links */}
                  {item.links?.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <span className="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        {lang === 'uz' ? 'Rasmiy manbalar' : 'Официальные источники'}
                      </span>
                      <div className="flex flex-wrap gap-2">
                        {item.links.map((link, idx) => (
                          <a
                            key={idx}
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center space-x-1.5 text-[11px] font-bold text-brand-700 dark:text-teal-400 hover:text-brand-800 dark:hover:text-teal-300 bg-brand-50 dark:bg-teal-950/40 hover:bg-brand-100 dark:hover:bg-teal-950/70 px-2.5 py-1 rounded-lg border border-brand-200 dark:border-teal-800 transition-all"
                          >
                            <ExternalLink className="w-3 h-3" />
                            <span>{link.label}</span>
                          </a>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* AI Legal Chat */}
      <div className="glass-card rounded-2xl overflow-hidden border border-slate-200/90 dark:border-slate-800 shadow-soft">
        {/* Chat Header */}
        <div className="p-3 bg-gradient-to-r from-slate-900 via-slate-800 to-brand-950 text-white flex items-center justify-between border-b border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="w-7 h-7 rounded-lg bg-teal-500/20 text-teal-300 flex items-center justify-center border border-teal-400/30">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-bold leading-none">{t.chat_title}</p>
              <p className="text-[10px] text-slate-400 mt-0.5">{t.chat_subtitle}</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <button
              type="button"
              onClick={clearChat}
              title={lang === 'uz' ? 'Suhbatni tozalash' : 'Очистить чат'}
              className="text-slate-400 hover:text-slate-200 transition-colors p-1 rounded-lg hover:bg-white/10"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Chat Messages */}
        <div className="p-3 space-y-3 max-h-80 overflow-y-auto bg-slate-50/40 dark:bg-slate-950/40">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex items-start space-x-2 ${m.role === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}
            >
              <div className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold ${
                m.role === 'user'
                  ? 'bg-slate-800 dark:bg-slate-700 text-white'
                  : 'bg-brand-100 dark:bg-brand-950 text-brand-800 dark:text-teal-300 border border-brand-200 dark:border-brand-800'
              }`}>
                {m.role === 'user' ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>

              <div className={`p-3 rounded-2xl max-w-[87%] text-xs leading-relaxed ${
                m.role === 'user'
                  ? 'bg-brand-700 text-white font-medium rounded-tr-sm shadow-sm'
                  : 'bg-white dark:bg-slate-800 text-slate-800 dark:text-slate-100 border border-slate-200/80 dark:border-slate-700 rounded-tl-sm shadow-sm'
              }`}>
                <div
                  className="whitespace-pre-line"
                  dangerouslySetInnerHTML={{
                    __html: m.text.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>')
                  }}
                />
              </div>
            </div>
          ))}

          {isSending && (
            <div className="flex items-center space-x-2 text-slate-400 text-xs py-1">
              <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce" />
              <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce [animation-delay:0.2s]" />
              <div className="w-2 h-2 rounded-full bg-brand-500 animate-bounce [animation-delay:0.4s]" />
              <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
                OqilaLegal {lang === 'uz' ? 'javob tayyorlamoqda...' : 'формулирует ответ...'}
              </span>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {/* Quick Question Chips */}
        <div className="p-2 border-t border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900 flex overflow-x-auto space-x-1.5 scrollbar-none pb-2">
          {quickQuestions.map((chip, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleSend(chip)}
              className="text-[11px] font-medium px-2.5 py-1.5 bg-slate-50 dark:bg-slate-800 hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg whitespace-nowrap border border-slate-200/60 dark:border-slate-700 transition-all flex items-center space-x-1 flex-shrink-0"
            >
              <HelpCircle className="w-3 h-3 text-brand-500 dark:text-teal-400 flex-shrink-0" />
              <span>{chip}</span>
            </button>
          ))}
        </div>

        {/* Chat Input */}
        <div className="p-2.5 bg-white dark:bg-slate-900 border-t border-slate-200/60 dark:border-slate-800 flex items-center space-x-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
            placeholder={t.chat_placeholder}
            className="flex-1 text-xs px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500"
          />
          <button
            type="button"
            disabled={isSending || !inputValue.trim()}
            onClick={() => handleSend()}
            className="p-2 rounded-xl bg-brand-700 hover:bg-brand-800 text-white transition-all disabled:opacity-40 active:scale-95"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>

        {/* AI Disclaimer Footer */}
        <div className="px-3 py-2 bg-amber-50/70 dark:bg-amber-950/30 border-t border-amber-200/50 dark:border-amber-900/30 flex items-start space-x-2 text-[10px] text-amber-900/90 dark:text-amber-200/80 leading-normal">
          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="flex-1">
            {t.legal_disclaimer_chat}
          </p>
        </div>
      </div>
    </div>
  );
}
