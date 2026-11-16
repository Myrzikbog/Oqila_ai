import { mediaUrl } from './session';
import { downloadFile } from './telegram';

/**
 * Download a protected file of this server (a card picture, a shipping label): the URL gets `download=1`, so the
 * server answers with `Content-Disposition: attachment`, and a short-lived media token.
 */
export async function downloadServerFile(path, fileName) {
  const withFlag = `${path}${path.includes('?') ? '&' : '?'}download=1`;
  return downloadFile(await mediaUrl(withFlag), fileName);
}
