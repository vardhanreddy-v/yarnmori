// Yarn-ball cursor: a real 3D crocheted ball (sphere + wrapped threads) that
// trails your mouse across the site. Falls back gracefully when WebGL is
// unavailable, on touch devices, or when "reduce motion" is requested.
import * as THREE from '/static/vendor/three.module.js';

const SIZE = 46; // CSS pixels of the cursor canvas

// Skip on touch devices / reduced motion.
if (!('ontouchstart' in window) && !window.matchMedia('(pointer: coarse)').matches
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  try {
    document.body.classList.add('yarn-cursor-active');
    const host = document.createElement('div');
    host.className = 'yarn-cursor';
    host.setAttribute('aria-hidden', 'true');
    document.body.appendChild(host);

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    renderer.setSize(SIZE, SIZE);
    renderer.domElement.style.display = 'block';
    host.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
    camera.position.z = 6;

    scene.add(new THREE.HemisphereLight(0xffffff, 0x9fb3a8, 2.4));
    const key = new THREE.DirectionalLight(0xffffff, 2.6);
    key.position.set(3, 4, 5);
    scene.add(key);
    const rim = new THREE.PointLight(0xd6cae7, 0.8, 30);
    rim.position.set(-4, -3, 4);
    scene.add(rim);

    const ball = new THREE.Group();
    scene.add(ball);
    const yarn = new THREE.MeshStandardMaterial({ color: 0xD6CAE7, roughness: 0.96, metalness: 0 });
    ball.add(new THREE.Mesh(new THREE.SphereGeometry(1.4, 32, 24), yarn));

    // Wrapped crochet threads around the ball.
    for (let i = 0; i < 34; i++) {
      const pts = [];
      for (let j = 0; j <= 100; j++) {
        const a = (j / 100) * Math.PI * 2;
        const r = 1.46;
        pts.push(new THREE.Vector3(
          r * Math.cos(a),
          r * Math.sin(a),
          0.07 * Math.sin(a * 9 + i)
        ));
      }
      const curve = new THREE.CatmullRomCurve3(pts);
      const strand = new THREE.Mesh(new THREE.TubeGeometry(curve, 100, 0.022, 5, false), yarn);
      strand.rotation.set(i * 0.17, i * 0.4, i * 0.28);
      ball.add(strand);
    }

    // Mouse tracking with smooth trailing.
    let tx = window.innerWidth / 2, ty = window.innerHeight / 2;
    let cx = tx, cy = ty;
    let hoveringLink = false;

    window.addEventListener('mousemove', (e) => { tx = e.clientX; ty = e.clientY; });
    window.addEventListener('touchmove', (e) => {
      if (e.touches[0]) { tx = e.touches[0].clientX; ty = e.touches[0].clientY; }
    }, { passive: true });

    document.addEventListener('mouseover', (e) => {
      hoveringLink = !!e.target.closest('a, button, [role="button"], input, textarea, select');
    });

    let visible = true;
    document.addEventListener('visibilitychange', () => { visible = !document.hidden; });

    function frame() {
      if (visible) {
        cx += (tx - cx) * 0.2;
        cy += (ty - cy) * 0.2;
        host.style.transform = `translate3d(${cx - SIZE / 2}px, ${cy - SIZE / 2}px, 0)`;
        ball.rotation.y += 0.012;
        ball.rotation.x += 0.004;
        ball.rotation.z = Math.sin(performance.now() * 0.001) * 0.12;
        ball.scale.setScalar(hoveringLink ? 1.18 : 1);
        renderer.render(scene, camera);
      }
      requestAnimationFrame(frame);
    }
    frame();

    addEventListener('pagehide', () => {
      renderer.setAnimationLoop(null);
      renderer.dispose();
    }, { once: true });
  } catch (err) {
    console.info('3D yarn cursor unavailable; product photos remain visible.');
  }
}