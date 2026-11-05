import React, { useEffect, useState } from 'react';
import { fetchAdminPhotoUrl } from '../utils/adminApi';

/** Shows a card's studio photo in the admin panel (loaded with admin credentials). */
export default function AdminPhoto({ card, className, alt }) {
  const isProtected = typeof card.studio_photo_url === 'string' && card.studio_photo_url.startsWith('/api/cards/');
  const [src, setSrc] = useState(isProtected ? null : card.studio_photo_url);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    if (!isProtected) return undefined;
    let objectUrl = null;
    let cancelled = false;
    fetchAdminPhotoUrl(card.id)
      .then((url) => {
        objectUrl = url;
        if (cancelled) URL.revokeObjectURL(url);
        else setSrc(url);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [card.id, isProtected]);

  if (failed) return null;
  if (!src) return <div className={`${className} animate-pulse bg-slate-800`} />;
  return <img src={src} alt={alt} className={className} loading="lazy" />;
}
