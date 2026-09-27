/**
 * confetti.js — Lightweight canvas confetti burst
 * Zero dependencies, works smoothly in Telegram WebApp.
 */
export function fireConfetti() {
  try {
    const canvas = document.createElement('canvas');
    canvas.style.position = 'fixed';
    canvas.style.top = '0';
    canvas.style.left = '0';
    canvas.style.width = '100vw';
    canvas.style.height = '100vh';
    canvas.style.pointerEvents = 'none';
    canvas.style.zIndex = '99999';
    document.body.appendChild(canvas);

    const ctx = canvas.getContext('2d');
    const width = (canvas.width = window.innerWidth);
    const height = (canvas.height = window.innerHeight);

    const colors = ['#0d9488', '#14b8a6', '#f59e0b', '#ec4899', '#8b5cf6', '#10b981'];
    const particles = Array.from({ length: 60 }).map(() => ({
      x: width / 2,
      y: height * 0.4,
      vx: (Math.random() - 0.5) * 14,
      vy: (Math.random() - 0.7) * 16,
      size: Math.random() * 7 + 4,
      color: colors[Math.floor(Math.random() * colors.length)],
      alpha: 1,
      rotation: Math.random() * 360,
      vRot: (Math.random() - 0.5) * 10,
    }));

    let animationFrame;
    function render() {
      ctx.clearRect(0, 0, width, height);
      let alive = false;

      particles.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.45; // gravity
        p.vx *= 0.98;
        p.rotation += p.vRot;
        p.alpha -= 0.015;

        if (p.alpha > 0) {
          alive = true;
          ctx.save();
          ctx.globalAlpha = p.alpha;
          ctx.translate(p.x, p.y);
          ctx.rotate((p.rotation * Math.PI) / 180);
          ctx.fillStyle = p.color;
          ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 1.5);
          ctx.restore();
        }
      });

      if (alive) {
        animationFrame = requestAnimationFrame(render);
      } else {
        cancelAnimationFrame(animationFrame);
        if (canvas.parentNode) {
          canvas.parentNode.removeChild(canvas);
        }
      }
    }

    render();
  } catch (err) {
    console.log('Confetti skipped:', err);
  }
}
