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
    fee: '7% БРВ = ~30 800 сум (для физлиц)',
    steps: [
      'Зайдите на официальный портал e-imzo.uz и скачайте программный модуль E-IMZO для вашей системы (Windows/macOS/Android/iOS).',
      'Установите и запустите модуль E-IMZO. Нажмите «Получить сертификат ключа ЭЦП».',
      'Введите серию и номер паспорта / ID-карты и дату рождения.',
      'Пройдите биометрическую идентификацию Face ID со смартфона или обратитесь лично в Центр государственных услуг (ЦГУ).',
      'После подтверждения личности система автоматически сформирует инвойс на оплату госпошлины — 7% от БРВ (30 800 сум). Оплатите через Click, Payme или Apelsin.',
      'Сертификат ключа ЭЦП генерируется онлайн и сохраняется в виде защищённого файла .pfx с вашим паролем на срок 2 года.',
      'ЭЦП физлица используется для авторизации на fo.birdarcha.uz (открытие ЯТТ), my.gov.uz, my.soliq.uz и подписания оферты Uzum Market.',
    ],
    links: [
      { label: 'e-imzo.uz — Портал E-IMZO', url: 'https://e-imzo.uz' },
      { label: 'my.gov.uz — Госуслуги', url: 'https://my.gov.uz' },
    ],
    law: 'Закон Республики Узбекистан «Об электронной цифровой подписи»',
    tip: '💡 Получение ЭЦП платно: 7% от БРВ (~30 800 сум) для физических лиц и 10% от БРВ (~44 000 сум) для юридических лиц. Бесплатно она выдаётся только при первичном получении биометрической ID-карты в органах миграции или учащимся лицеев/колледжей.',
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
      'Оплатите государственную пошлину через Click, Payme или банковскую карту (при онлайн-оплате действует скидка 10% — 0.9 БРВ вместо 1 БРВ).',
      'Свидетельство о государственной регистрации ЯТТ с уникальным QR-кодом формируется моментально в личном кабинете.',
    ],
    links: [
      { label: 'fo.birdarcha.uz — Единый портал регистрации бизнеса', url: 'https://fo.birdarcha.uz' },
      { label: 'my.gov.uz — Регистрация через Госуслуги', url: 'https://my.gov.uz' },
    ],
    law: 'Порядок государственной регистрации субъектов предпринимательства (ПКМ № 66, Закон «О гарантиях свободы предпринимательской деятельности»)',
    tip: '⚠️ КРИТИЧЕСКИ ВАЖНО: Если вы заказываете товары в Китае (1688, Taobao, карго) или покупаете на оптовых рынках для перепродажи — статус ЯТТ ОБЯЗАТЕЛЕН! Использовать самозанятость при перепродаже покупных товаров строго запрещено законом.',
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
      'Выберите вид деятельности из официального перечня 104 видов: пошив одежды/текстиль (№36), ремёсла и народные промыслы (№39), домашняя кулинария и кондитерские изделия (№50), услуги парикмахера/визажиста, репетиторство, IT-фриланс и др.',
      'Подтвердите данные — электронная справка с QR-кодом формируется моментально.',
      'Скачайте справку самозанятого: она является официальным документом для открытия бизнес-карт, работы с клиентами и выхода на Uzum Market со своей продукцией.',
    ],
    links: [
      { label: 'my.soliq.uz — Портал налоговых услуг', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Мобильное приложение Soliq', url: 'https://soliq.uz/mobile' },
    ],
    law: 'Постановление Президента РУз № ПП-4742 «О мерах по упрощению государственного регулирования предпринимательской деятельности и самозанятости»',
    tip: '💡 Главные правила самозанятости: 1) С 1 января 2026 года действует ставка налога с оборота 1% (Закон № ЗРУ-1108); 2) Соцналог — 1 БРВ в год (440 000 сум, добровольно для стажа); 3) Нанимать сотрудников по трудовому договору ЗАПРЕЩЕНО; 4) ТОРГОВЛЯ ПОКУПНЫМИ ТОВАРАМИ ЗАПРЕЩЕНА — продавать можно только то, что создано своими руками.',
  },
  {
    id: 'uzum',
    icon: ShoppingBag,
    color: 'purple',
    title: 'Как стать продавцом на Uzum Market? (ЯТТ vs Самозанятый)',
    badge: 'Электронная коммерция',
    timeline: '2–4 рабочих дня',
    fee: 'Регистрация бесплатная (комиссия 8–15% с продаж)',
    steps: [
      'ОПРЕДЕЛИТЕСЬ С ВАШИМ СТАТУСОМ:',
      '• Если вы производите товар сами (хэндмейд, пошив, ремесло) — вы МОЖЕТЕ продавать на Uzum как САМОЗАНЯТЫЙ! Документы: паспорт, QR-справка из Soliq, личная сумовая карта.',
      '• Если вы перепродаёте товары (Китай, оптовые закупки, электроника, одежда чужих фабрик) — вы ОБЯЗАНЫ открыть ЯТТ или ООО! Документы: свидетельство ЯТТ, паспорт, расчётный счёт в банке.',
      'Зайдите на seller.uzum.uz и подайте заявку на открытие магазина.',
      'Загрузите подтверждающие документы и подпишите электронный договор оферты.',
      'В личном кабинете my.soliq.uz обязательно добавьте Uzum Market в перечень комиссионеров (стандартная процедура налоговой отчетности для маркетплейсов).',
      'Создайте карточки товаров, упакуйте партию по регламенту Uzum и передайте на склад маркетплейса.',
    ],
    links: [
      { label: 'seller.uzum.uz — Портал для продавцов Uzum', url: 'https://seller.uzum.uz' },
      { label: 'partner.uzum.uz — База знаний Uzum', url: 'https://partner.uzum.uz' },
    ],
    law: 'Закон Республики Узбекистан «Об электронной коммерции»; Налоговый кодекс РУз (ст. 467 в ред. ЗРУ-1108)',
    tip: '⚡ Налоговая ставка для торговли на Uzum Market составляет единый 1% налога с оборота (маркетплейс выступает налоговым агентом и удерживает налог при выплатах). Выплаты от Uzum поступают на ваш расчётный счёт (для ЯТТ) или банковскую карту (для самозанятых).',
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
      '• ДЛЯ ЯТТ: открытие отдельного банковского расчетного счета (20208...) ОБЯЗАТЕЛЬНО для оптовых закупок, эквайринга Click/Payme и торговли на маркетплейсах.',
      'Как открыть счёт ЯТТ онлайн: скачайте бизнес-приложение выбранного банка (например, Kapitalbank Business, Anor Business, Ipoteka-Retail).',
      'Загрузите скан паспорта / ID-карты и свидетельство о регистрации ЯТТ из fo.birdarcha.uz (ИНН подтягивается автоматически).',
      'Пройдите видеоидентификацию в приложении банка — счёт активируется за 1–3 рабочих дня.',
      'Получите выписку с реквизитами (20-значный счёт 20208..., МФО банка, ИНН) — эти данные указываются в договоре с Uzum Market и эквайрингом.',
    ],
    links: [
      { label: 'kapitalbank.uz — Kapitalbank Business', url: 'https://kapitalbank.uz' },
      { label: 'anorbank.uz — Anorbank Business', url: 'https://anorbank.uz' },
    ],
    law: 'Инструкция Центрального банка РУз о порядке открытия, ведения и закрытия банковских счетов',
    tip: '💡 Деньги от продаж на маркетплейсах и через эквайринг Click/Payme зачисляются на ваш банковский счёт. С расчетного счета ЯТТ предприниматель может свободно переводить чистую прибыль на свою личную карту физического лица без дополнительного налога.',
  },
  {
    id: 'hunarmand',
    icon: Award,
    color: 'rose',
    title: 'Как получить сертификат Хунарманд (мастера-ремесленника)?',
    badge: '100% освобождение от налога с оборота',
    timeline: '7–14 рабочих дней',
    fee: 'Вступительный и членский взнос в ассоциацию',
    steps: [
      'Проверьте, входит ли ваше направление в официальный перечень видов ремесленнической деятельности (керамика, резьба по дереву, чеканка, вышивка сюзане, национальный текстиль, ювелирное дело).',
      'Подготовьте портфолио: качественные фотографии ваших изделий, описание техники изготовления, сертификаты об участии в выставках (при наличии).',
      'Подайте онлайн-заявление на членство через сайт hunarmand.uz или обратитесь в районное отделение ассоциации «Хунарманд».',
      'Экспертный совет оценит художественную и ремесленную ценность ваших работ.',
      'После одобрения и оплаты членского взноса вам выдаётся официальное свидетельство члена ассоциации «Хунарманд».',
      'Свидетельство дает полное освобождение от налога с оборота по доходам от ремесленной деятельности, право на льготные кредиты и бесплатное участие в государственных ярмарках.',
    ],
    links: [
      { label: 'hunarmand.uz — Сайт «Хунарманд»', url: 'https://hunarmand.uz' },
    ],
    law: 'Указы Президента РУз о мерах по поддержке и развитию ремесленничества (УП-5242, УП-91)',
    tip: '✨ Члены ассоциации «Хунарманд» имеют уникальную государственную льготу: 0% налога с оборота от продажи изделий собственного ремесленного труда.',
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
      'САМОЗАНЯТЫЕ: освобождены от покупки кассовых аппаратов, при необходимости чек формируется через приложение Soliq.',
    ],
    links: [
      { label: 'my.soliq.uz — Регистрация онлайн-ККМ', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Приложение Soliq', url: 'https://soliq.uz/mobile' },
    ],
    law: 'Порядок применения онлайн контрольно-кассовых машин и виртуальных касс (ПКМ № 943, ст. 221 НК РУз)',
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
      '📌 1. ЕЖЕМЕСЯЧНО ДО 15 ЧИСЛА — Единый налог с оборота 1%:',
      '   • С 1 января 2026 года (Закон № ЗРУ-1108, ст. 467 строка 5) установлена единая ставка налога с оборота 1% для ИП и самозанятых с доходом до 1 млрд сум;',
      '   • При продажах через Uzum Market маркетплейс удерживает этот 1% автоматически как налоговый агент;',
      '   • При розничных и прямых продажах налог уплачивается самостоятельно через my.soliq.uz до 15 числа.',
      '📌 2. ЕЖЕМЕСЯЧНО ДО 15 ЧИСЛА — Социальный налог ЯТТ:',
      '   • Ровно 1 БРВ в месяц (440 000 сум/мес) в обязательном порядке для ЯТТ (ст. 408 НК РУз).',
      '📌 3. ГОДОВОЙ ОТЧЕТ — до 1 апреля следующего года подается годовая налоговая декларация через my.soliq.uz.',
      '⚠️ ПОРОГ НДС (1 МЛРД СУМ): если ваша выручка с начала года превысит 1 миллиард сум, возникает обязательство перейти на уплату НДС (12%) и налога на прибыль.',
      '💡 САМОЗАНЯТЫЕ: налог с оборота — 1% с первого сума (льгота 0% до 100 млн сум отменена с 01.01.2026 г.). Социальный налог — 1 БРВ в год (440 000 сум) ДОБРОВОЛЬНО для пенсионного стажа.',
    ],
    links: [
      { label: 'my.soliq.uz — Оплата налогов онлайн', url: 'https://my.soliq.uz' },
    ],
    law: 'Налоговый кодекс Республики Узбекистан (статьи 467, 408, 237, ред. ЗРУ-1108)',
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
    fee: '7% BHM = ~30 800 so\'m (jismoniy shaxslar uchun)',
    steps: [
      'Rasmiy e-imzo.uz portaliga kiring va operatsion tizimingiz (Windows/macOS/Android/iOS) uchun E-IMZO modulini yuklab oling.',
      'Modulni o\'rnating va «ERI kalitini olish» bo\'limini tanlang.',
      'Pasport yoki ID-karta seriyasi, raqami hamda tug\'ilgan sanangizni kiriting.',
      'Smartfoningiz orqali Face ID (biometrik qiyofani aniqlash)dan o\'ting yoki Davlat xizmatlari markaziga (DXM) shaxsan murojaat qiling.',
      'Ma\'lumotlar kiritilgandan so\'ng tizim avtomatik ravishda 7% BHM (30 800 so\'m) miqdoridagi to\'lov hisobini shakllantiradi. Click, Payme yoki Apelsin orqali onlayn to\'lanadi.',
      'ERI sertifikati parolingiz bilan himoyalangan .pfx fayli ko\'rinishida 2 yil muddatga beriladi.',
      'Jismoniy shaxs ERIsi fo.birdarcha.uz, my.gov.uz, my.soliq.uz portallariga kirish va YaTT ochish uchun xizmat qiladi.',
    ],
    links: [
      { label: 'e-imzo.uz — Rasmiy E-IMZO portali', url: 'https://e-imzo.uz' },
      { label: 'my.gov.uz — Davlat xizmatlari portali', url: 'https://my.gov.uz' },
    ],
    law: 'O‘zbekiston Respublikasining «Elektron raqamli imzo to‘g‘risida»gi Qonuni',
    tip: '💡 ERI olish narxi: jismoniy shaxslar uchun 7% BHM (~30 800 so\'m), yuridik shaxslar uchun 10% BHM (~44 000 so\'m)ni tashkil qiladi. Bepul tarzda faqat yangi ID-karta olayotganda yoki litsey/kollej o\'quvchilariga beriladi.',
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
      'Davlat bojini Click, Payme yoki bank kartasi orqali to\'lang (onlayn to\'lovda 10% chegirma — 1 BHM o\'rniga 0.9 BHM).',
      'To\'lov amalga oshirilishi bilanoq QR-kodli elektron YaTT guvohnomasi shaxsiy kabinetingizda tayyor bo\'ladi.',
    ],
    links: [
      { label: 'fo.birdarcha.uz — Biznesni ro\'yxatdan o\'tkazish portali', url: 'https://fo.birdarcha.uz' },
      { label: 'my.gov.uz — Yagona interaktiv davlat xizmatlari', url: 'https://my.gov.uz' },
    ],
    law: 'Tadbirkorlik subyektlarini davlat ro‘yxatidan o‘tkazish tartibi (VMQ № 66, «Tadbirkorlik faoliyati erkinligining kafolatlari to‘g‘risida»gi Qonun)',
    tip: '⚠️ QAT\'IY TALAB: Agar siz tovarlarni Xitoydan (1688, Taobao, kargo) yoki ulgurji bozorlardan qayta sotish uchun olib kelsangiz — YaTT maqomi SHART! Qayta sotishda o\'z-o\'zini band qilish qonunan man etilgan.',
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
      '104 ta ruxsat berilgan faoliyat turidan o\'zingizga mosini tanlang: kiyim tikish va to\'qimachilik (№36), xalq hunarmandchiligi (№39), uyda pishiriq va pazandachilik (№50), sartaroshlik, repetitorlik, IT-frilans va boshqalar.',
      'Ma\'lumotlarni tasdiqlang — QR-kodli elektron ma\'lumotnoma darhol shakllanadi.',
      'Ma\'lumotnomani yuklab oling: u bankda biznes-karta ochish, mijozlar va Uzum Market bilan ishlash uchun rasmiy hujjat hisoblanadi.',
    ],
    links: [
      { label: 'my.soliq.uz — Elektron soliq xizmatlari', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Soliq mobil ilovasi', url: 'https://soliq.uz/mobile' },
    ],
    law: 'O‘zbekiston Respublikasi Prezidentining PQ-4742-son «Tadbirkorlik faoliyati va o‘zini o‘zi band qilishni tartibga solish chora-tadbirlari to‘g‘risida»gi qarori',
    tip: '💡 Asosiy qoidalar: 1) 2026-yil 1-yanvardan (O\'RQ-1108) o\'z-o\'zini band qilganlar uchun 1% aylanmadan soliq to\'lanadi (100 mln so\'mgacha 0% imtiyoz bekor qilingan); 2) Ijtimoiy soliq: pensiya staji uchun yiliga 1 BHM ixtiyoriy; 3) Ishchi yollash taqiqlanadi; 4) Qayta sotish uchun tovar sotib olish TAQIQLANADI — faqat o\'z mehnatingiz bilan yaratilgan buyumlarni sotishingiz mumkin.',
  },
  {
    id: 'uzum',
    icon: ShoppingBag,
    color: 'purple',
    title: 'Uzum Market\'da sotuvchi qanday bo\'lish mumkin? (YaTT vs O\'z-o\'zini band qilgan)',
    badge: 'Elektron tijorat',
    timeline: '2–4 ish kuni',
    fee: 'Ro\'yxatdan o\'tish bepul (8–15% savdo komissiyasi)',
    steps: [
      'MAQOMINGIZNI ANQLANG:',
      '• Agar mahsulotni O\'ZINGIZ ISHLAB CHIQARAYOTGAN bo\'lsangiz (handmade, tikuvchilik, kiyim, shirinliklar) — siz Uzum Market\'da O\'Z-O\'ZINI BAND QILGAN SHAXS sifatida sota olasiz! Hujjatlar: pasport, Soliq QR-ma\'lumotnomasi, shaxsiy so\'m kartasi.',
      '• Agar tovarlarni QAYTA SOTAYOTGAN bo\'lsangiz (Xitoy, fabrika, ulgurji bozor tovarlari) — YaTT yoki MChJ ochishingiz SHART! Hujjatlar: YaTT guvohnomasi, pasport, bankdagi hisobvaraq.',
      'seller.uzum.uz saytiga o\'ting va sotuvchi hisobini ochish uchun ariza topshiring.',
      'Kerakli hujjatlarni yuklab, oferta shartnomasini imzolang.',
      'my.soliq.uz shaxsiy kabinetida Uzum Market (Marketpleys)ni komissionerlar ro\'yxatiga qo\'shing (majburiy soliq tartibi).',
      'Mahsulot kartochkalarini to\'ldirib, Uzum qoidalariga ko\'ra qadoqlang va omborga topshiring.',
    ],
    links: [
      { label: 'seller.uzum.uz — Uzum sotuvchilar portali', url: 'https://seller.uzum.uz' },
      { label: 'partner.uzum.uz — Sotuvchilar uchun qo\'llanma', url: 'https://partner.uzum.uz' },
    ],
    law: 'O‘zbekiston Respublikasining «Elektron tijorat to‘g‘risida»gi Qonuni; Soliq kodeksi (yagona 1% aylanma solig\'i, O\'RQ-1108)',
    tip: '⚡ Uzum Market orqali savdoda aylanmadan soliq stavkasi yagona 1% ni tashkil qiladi (Uzum soliq agenti sifatida 1% soliqni avtomatik ushlab qoladi). Tushumlar YaTT hisobvarag\'iga yoki o\'z-o\'zini band qilgan shaxsning kartasiga kelib tushadi.',
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
      '• YaTT UCHUN: alohida 20208... hisobvarag\'i ochish majburiy (ulgurji xaridlar, Click/Payme ekvayring va do\'konlar uchun).',
      'YaTT hisobvarag\'ini onlayn ochish: tanlangan bankning biznes ilovasini yuklab oling (masalan, Kapitalbank Business, Anor Business, Ipoteka-Retail).',
      'Pasport/ID-karta va fo.birdarcha.uz\'dan olingan YaTT guvohnomasini yuklang (STIR avtomatik ravishda tekshiriladi).',
      'Ilovada video-identifikatsiyadan o\'ting — hisobvaraq 1–3 ish kunida faollashadi.',
      '20 xonali hisob raqami (20208...), MFO va STIR rekvizitlarini oling — bu ma\'lumotlar Uzum Market va ekvayring shartnomalariga kiritiladi.',
    ],
    links: [
      { label: 'kapitalbank.uz — Kapitalbank biznes hisob', url: 'https://kapitalbank.uz' },
      { label: 'anorbank.uz — Anorbank onlayn biznes', url: 'https://anorbank.uz' },
    ],
    law: 'O‘zbekiston Respublikasi Markaziy bankining Bank hisobvaraqlarini ochish, yuritish va yopish tartibi to‘g‘risidagi yo‘riqnomasi',
    tip: '💡 Savdodan tushgan sof foydani YaTT hisobvarag\'idan o\'zingizning shaxsiy jismoniy shaxs kartangizga qo\'shimcha soliqlarsiz bemalol o\'tkazib olishingiz mumkin.',
  },
  {
    id: 'hunarmand',
    icon: Award,
    color: 'rose',
    title: 'Hunarmand sertifikati qanday olinadi?',
    badge: 'Aylanma solig\'idan 100% ozod etish imtiyozi',
    timeline: '7–14 ish kuni',
    fee: 'Assotsiatsiyaga kirish va a\'zolik badali',
    steps: [
      'Faoliyatingiz xalq hunarmandchiligining rasmiy ro\'yxatiga (kulolchilik, yog\'och o\'ymakorligi, zardo\'zlik, milliy liboslar, so\'zana, zargarlik) kirishini tekshiring.',
      'Portfolio tayyorlang: buyumlaringizning sifatli fotosuratlari, tayyorlash uslubi va ko\'rgazmalardagi ishtirok sertifikatlari (mavjud bo\'lsa).',
      'hunarmand.uz veb-sayti orqali arizani onlayn yuboring yoki tuman «Hunarmand» uyushmasiga shaxsan boring.',
      'Ekspertlar kengashi buyumlaringizning badiiy va amaliy qimmatini baholaydi.',
      'A\'zolik tasdiqlanib, badal to\'langandan so\'ng «Hunarmand» uyushmasi a\'zolik guvohnomasi beriladi.',
      'Guvohnoma hunarmandchilik mahsulotlarini sotishdan olingan daromadlar bo\'yicha aylanmadan olinadigan soliqdan 100% ozod qiladi.',
    ],
    links: [
      { label: 'hunarmand.uz — «Hunarmand» uyushmasi', url: 'https://hunarmand.uz' },
    ],
    law: 'O‘zbekiston Respublikasi Prezidentining hunarmandchilikni rivojlantirish to‘g‘risidagi Farmonlari (PF-5242, PF-91)',
    tip: '✨ «Hunarmand» uyushmasi a\'zolari o\'z mehnati bilan tayyorlagan buyumlarni sotishda aylanmadan olinadigan soliqni to\'lashdan to\'liq ozod qilingan.',
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
      'O\'Z-O\'ZINI BAND QILGANLAR: kassa apparati sotib olish majburiyatidan ozod, kerak bo\'lsa chek Soliq ilovasida chiqariladi.',
    ],
    links: [
      { label: 'my.soliq.uz — Onlayn-NKM ro\'yxatdan o\'tkazish', url: 'https://my.soliq.uz' },
      { label: 'soliq.uz/mobile — Soliq mobil ilovasi', url: 'https://soliq.uz/mobile' },
    ],
    law: 'Onlayn nazorat-kassa mashinalari va virtual kassalarni qo‘llash tartibi (VMQ № 943, Soliq kodeksi 221-modda)',
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
      '📌 1. HAR OYNING 15-SANASIGACHA — Yagona 1% aylanmadan soliq:',
      '   • 2026-yil 1-yanvardan (O\'RQ-1108-son qonun, SK 467-modda 5-band) YaTT va o\'z-o\'zini band qilganlar uchun 1 mlrd so\'mgacha yagona 1% stavka o\'rnatilgan;',
      '   • Uzum Market orqali savdoda Uzum 1% soliqni soliq agenti sifatida o\'zi ushlab qoladi;',
      '   • To\'g\'ridan-to\'g\'ri va do\'kon savdosida soliq my.soliq.uz orqali har oyning 15-sanasigacha to\'lanadi.',
      '📌 2. HAR OYNING 15-SANASIGACHA — YaTT ijtimoiy solig\'i:',
      '   • Har oyda qat\'iy 1 BHM (440 000 so\'m/oy) — daromad bo\'lmagan oylarda ham to\'lanishi majburiy.',
      '📌 3. YILLIK HISOBOT — keyingi yilning 1 apreligacha my.soliq.uz orqali yillik soliq deklaratsiyasi topshiriladi.',
      '⚠️ QQS CHEGARASI (1 MLRD SO\'M): yillik jami aylanma 1 milliard so\'mdan oshganda, tadbirkor avtomatik ravishda 12% QQS va foyda solig\'i to\'lashga o\'tadi.',
      '💡 O\'Z-O\'ZINI BAND QILGANLAR: aylanmadan soliq — 1% (100 mln so\'mgacha 0% imtiyoz 2026-yildan bekor qilingan). Ijtimoiy soliq — yiliga 1 BHM (440 000 so\'m) pensiya staji uchun IXTIYORIY.',
    ],
    links: [
      { label: 'my.soliq.uz — Soliqlarni onlayn to\'lash', url: 'https://my.soliq.uz' },
    ],
    law: 'O‘zbekiston Respublikasi Soliq kodeksi (467, 408, 237-moddalar, O\'RQ-1108)',
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

const COLOR_MAP = {
  violet: {
    bg: 'bg-violet-100 dark:bg-violet-950',
    text: 'text-violet-700 dark:text-violet-300',
    badge: 'bg-violet-50 dark:bg-violet-950 text-violet-700 dark:text-violet-300 border-violet-200 dark:border-violet-800',
    border: 'border-violet-300 dark:border-violet-700',
  },
  amber: {
    bg: 'bg-amber-100 dark:bg-amber-950',
    text: 'text-amber-700 dark:text-amber-300',
    badge: 'bg-amber-50 dark:bg-amber-950 text-amber-700 dark:text-amber-300 border-amber-200 dark:border-amber-800',
    border: 'border-amber-300 dark:border-amber-700',
  },
  emerald: {
    bg: 'bg-emerald-100 dark:bg-emerald-950',
    text: 'text-emerald-700 dark:text-emerald-300',
    badge: 'bg-emerald-50 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 border-emerald-200 dark:border-emerald-800',
    border: 'border-emerald-300 dark:border-emerald-700',
  },
  rose: {
    bg: 'bg-rose-100 dark:bg-rose-950',
    text: 'text-rose-700 dark:text-rose-300',
    badge: 'bg-rose-50 dark:bg-rose-950 text-rose-700 dark:text-rose-300 border-rose-200 dark:border-rose-800',
    border: 'border-rose-300 dark:border-rose-700',
  },
  teal: {
    bg: 'bg-teal-100 dark:bg-teal-950',
    text: 'text-teal-700 dark:text-teal-300',
    badge: 'bg-teal-50 dark:bg-teal-950 text-teal-700 dark:text-teal-300 border-teal-200 dark:border-teal-800',
    border: 'border-teal-300 dark:border-teal-700',
  },
  purple: {
    bg: 'bg-purple-100 dark:bg-purple-950',
    text: 'text-purple-700 dark:text-purple-300',
    badge: 'bg-purple-50 dark:bg-purple-950 text-purple-700 dark:text-purple-300 border-purple-200 dark:border-purple-800',
    border: 'border-purple-300 dark:border-purple-700',
  },
  indigo: {
    bg: 'bg-indigo-100 dark:bg-indigo-950',
    text: 'text-indigo-700 dark:text-indigo-300',
    badge: 'bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border-indigo-200 dark:border-indigo-800',
    border: 'border-indigo-300 dark:border-indigo-700',
  },
  sky: {
    bg: 'bg-sky-100 dark:bg-sky-950',
    text: 'text-sky-700 dark:text-sky-300',
    badge: 'bg-sky-50 dark:bg-sky-950 text-sky-700 dark:text-sky-300 border-sky-200 dark:border-sky-800',
    border: 'border-sky-300 dark:border-sky-700',
  },
};

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
      const data = await res.json();
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.answer || (lang === 'uz' ? "Kechirasiz, javob olishda xatolik." : "Ошибка при получении ответа.") }
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
      <div className="glass-card rounded-2xl p-4 border-l-4 border-l-rose-600 dark:border-l-rose-400 bg-gradient-to-r from-rose-50/50 via-white to-white dark:from-rose-950/30 dark:via-slate-900 dark:to-slate-900">
        <div className="flex items-center space-x-2 text-rose-800 dark:text-rose-300">
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
