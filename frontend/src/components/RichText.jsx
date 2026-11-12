import React from 'react';

/**
 * Text from the server or the AI with bold spans, rendered WITHOUT raw HTML.
 * Only two markers are understood: **bold** and <b>bold</b>. Everything else, including any other tag,
 * is shown as plain text, so an answer like `<img src=x onerror=alert(1)>` is just visible characters.
 */
const BOLD = /(\*\*[^*\n]+?\*\*|<b>[^<]*?<\/b>)/g;

export default function RichText({ text, className = '' }) {
  const parts = String(text ?? '').split(BOLD);
  return (
    <div className={`whitespace-pre-line ${className}`}>
      {parts.map((part, i) => {
        if (part.startsWith('**') && part.endsWith('**') && part.length > 4) return <b key={i}>{part.slice(2, -2)}</b>;
        if (part.startsWith('<b>') && part.endsWith('</b>')) return <b key={i}>{part.slice(3, -4)}</b>;
        return <React.Fragment key={i}>{part}</React.Fragment>;
      })}
    </div>
  );
}
