/**
 * imageFile.js — prepare a photo before it is uploaded: phones produce 5-12 MB pictures of 4000+ px, which is slow on
 * a mobile connection and more than the AI uses. A picture is scaled to at most 2048 px and re-encoded as JPEG.
 */
export const MAX_SIDE = 2048;
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

const HEIC = /\.(heic|heif)$/i;

/** HEIC/HEIF (iPhone "high efficiency") is not supported: the browser often reports an empty type for it. */
export function isHeic(file) {
  return /image\/hei[cf]/i.test(file.type || '') || (!file.type && HEIC.test(file.name || '')) || HEIC.test(file.name || '');
}

/** Returns a File ready for upload; throws Error('heic' | 'not_image' | 'too_large') for files that cannot be used. */
export async function prepareImage(file) {
  if (isHeic(file)) throw new Error('heic');
  if (file.type && !file.type.startsWith('image/')) throw new Error('not_image');
  if (!file.type) throw new Error('not_image');
  let bitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' });
  } catch {
    // The browser cannot decode it here: send it as it is, the server checks the file anyway
    if (file.size > MAX_UPLOAD_BYTES) throw new Error('too_large');
    return file;
  }
  const scale = Math.min(1, MAX_SIDE / Math.max(bitmap.width, bitmap.height));
  if (scale === 1 && file.size <= 1.5 * 1024 * 1024 && /jpe?g/i.test(file.type)) {
    bitmap.close?.();
    return file;
  }
  const canvas = document.createElement('canvas');
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#ffffff'; // PNG transparency becomes white instead of black
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close?.();
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.88));
  if (!blob) return file;
  const name = (file.name || 'photo').replace(/\.[^.]+$/, '') + '.jpg';
  return new File([blob], name, { type: 'image/jpeg' });
}
