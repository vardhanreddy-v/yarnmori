// Yarnmori 3D Intro Splash Screen
// Spawns 3D yarn balls, crochet hooks, safety pins, and stitch markers that
// fall from the top of the screen with physics, then smoothly unveils the site.

import * as THREE from '/static/vendor/three.module.js';

(function () {
  'use strict';

  const overlay = document.getElementById('yarn-intro');
  const canvas = document.getElementById('yarn-intro-canvas');
  if (!overlay || !canvas) return;

  // Only run once per session so navigating around isn't annoying.
  // The overlay lives in base.html on every page, so always remove it here
  // if the intro already played — otherwise it would block the whole page.
  if (sessionStorage.getItem('yarnmori_intro_seen')) {
    overlay.remove();
    document.body.classList.remove('intro-active');
    return;
  }

  // Skip if reduced motion requested
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    overlay.remove();
    return;
  }

  sessionStorage.setItem('yarnmori_intro_seen', '1');
  document.body.classList.add('intro-active');

  try {
    const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(window.innerWidth, window.innerHeight);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.z = 18;

    // Soft warm lighting
    scene.add(new THREE.HemisphereLight(0xFFFFFF, 0xA5B8A0, 2.5));
    const keyLight = new THREE.DirectionalLight(0xFFFFFF, 2.5);
    keyLight.position.set(5, 10, 7);
    scene.add(keyLight);
    const fillLight = new THREE.PointLight(0xE8B955, 1.2, 30);
    fillLight.position.set(-6, -4, 5);
    scene.add(fillLight);

    // Color palette
    const PALETTE = [
      0xD6CAE7, // Lilac
      0xE8B955, // Honey
      0xA5B8A0, // Sage
      0xFAF6EF, // Cream
      0xE87A90, // Soft Coral
      0x94B0DA  // Soft Blue
    ];

    // Shared materials
    const yarnMats = PALETTE.map(c => new THREE.MeshStandardMaterial({ color: c, roughness: 0.95 }));
    const metalMat = new THREE.MeshStandardMaterial({ color: 0xD8D8D8, metalness: 0.85, roughness: 0.2 });

    // -------------------------------------------------------------
    // Helper mesh generators
    // -------------------------------------------------------------
    function createYarnBall(mat) {
      const grp = new THREE.Group();
      const r = 0.85 + Math.random() * 0.45;
      grp.add(new THREE.Mesh(new THREE.SphereGeometry(r, 24, 20), mat));

      // Wrapped strands
      const strandsCount = 18;
      for (let i = 0; i < strandsCount; i++) {
        const pts = [];
        for (let j = 0; j <= 40; j++) {
          const a = (j / 40) * Math.PI * 2;
          const sr = r * 1.04;
          pts.push(new THREE.Vector3(
            sr * Math.cos(a),
            sr * Math.sin(a),
            0.04 * Math.sin(a * 7 + i)
          ));
        }
        const curve = new THREE.CatmullRomCurve3(pts);
        const strand = new THREE.Mesh(new THREE.TubeGeometry(curve, 30, 0.022, 5, false), mat);
        strand.rotation.set(i * 0.3, i * 0.5, i * 0.2);
        grp.add(strand);
      }
      return grp;
    }

    function createCrochetHook() {
      const grp = new THREE.Group();
      // Handle (pastel plastic/wood)
      const handleMat = yarnMats[Math.floor(Math.random() * yarnMats.length)];
      const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.14, 2.2, 12), handleMat);
      handle.position.y = -1;
      grp.add(handle);
      // Metal shaft
      const shaft = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 1.8, 12), metalMat);
      shaft.position.y = 0.9;
      grp.add(shaft);
      // Hook tip
      const tip = new THREE.Mesh(new THREE.TorusGeometry(0.1, 0.06, 8, 12, Math.PI * 1.2), metalMat);
      tip.position.set(0.06, 1.75, 0);
      tip.rotation.z = -Math.PI / 3;
      grp.add(tip);
      grp.scale.setScalar(0.7);
      return grp;
    }

    function createSafetyPin() {
      const grp = new THREE.Group();
      const path = new THREE.CurvePath();
      const r = 0.3, h = 1.4;
      // Loop body using TubeGeometry along a curve
      const pts = [];
      for (let i = 0; i <= 20; i++) {
        const a = (i / 20) * Math.PI;
        pts.push(new THREE.Vector3(Math.cos(a) * r, h / 2 + Math.sin(a) * r, 0));
      }
      pts.push(new THREE.Vector3(-r, -h / 2, 0));
      for (let i = 0; i <= 20; i++) {
        const a = (i / 20) * Math.PI;
        pts.push(new THREE.Vector3(-Math.cos(a) * r, -h / 2 - Math.sin(a) * r, 0));
      }
      pts.push(new THREE.Vector3(r, h / 2 * 0.7, 0));

      const curve = new THREE.CatmullRomCurve3(pts);
      const pin = new THREE.Mesh(new THREE.TubeGeometry(curve, 40, 0.035, 6, false), metalMat);
      grp.add(pin);

      // Pin cap (colored accent)
      const capMat = yarnMats[Math.floor(Math.random() * yarnMats.length)];
      const cap = new THREE.Mesh(new THREE.BoxGeometry(0.25, 0.45, 0.18), capMat);
      cap.position.set(0, h / 2 + r * 0.5, 0);
      grp.add(cap);

      grp.scale.setScalar(0.7);
      return grp;
    }

    function createStitchMarker() {
      // Ring/clip marker
      const grp = new THREE.Group();
      const mat = yarnMats[Math.floor(Math.random() * yarnMats.length)];
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.4, 0.08, 10, 20), mat);
      grp.add(ring);
      // Small dangling charm
      const charm = new THREE.Mesh(new THREE.SphereGeometry(0.2, 12, 12), metalMat);
      charm.position.y = -0.65;
      grp.add(charm);
      grp.scale.setScalar(0.75);
      return grp;
    }

    // -------------------------------------------------------------
    // Spawn falling objects
    // -------------------------------------------------------------
    const objects = [];
    const OBJECT_COUNT = 24;

    for (let i = 0; i < OBJECT_COUNT; i++) {
      let mesh;
      const type = Math.random();
      if (type < 0.55) {
        mesh = createYarnBall(yarnMats[i % yarnMats.length]);
      } else if (type < 0.75) {
        mesh = createCrochetHook();
      } else if (type < 0.88) {
        mesh = createSafetyPin();
      } else {
        mesh = createStitchMarker();
      }

      // Random starting positions (scattered above viewport)
      const x = (Math.random() - 0.5) * 22;
      const startY = 12 + Math.random() * 18;
      const z = (Math.random() - 0.5) * 8;

      mesh.position.set(x, startY, z);
      scene.add(mesh);

      // Physics props
      objects.push({
        mesh,
        vy: -0.08 - Math.random() * 0.14,           // gravity / fall speed
        vx: (Math.random() - 0.5) * 0.02,           // slight drift
        rx: (Math.random() - 0.5) * 0.04,           // spin rate
        ry: (Math.random() - 0.5) * 0.05,
        rz: (Math.random() - 0.5) * 0.03,
        delay: Math.random() * 40                     // staggered start frames
      });
    }

    // Resize handler
    window.addEventListener('resize', () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    });

    // -------------------------------------------------------------
    // Animation loop & Timeline
    // -------------------------------------------------------------
    let frameId;
    let startTime = performance.now();
    const DURATION = 2600; // Total intro duration in ms

    function animate(t) {
      const elapsed = t - startTime;

      // Update falling physics
      objects.forEach(obj => {
        if (elapsed < obj.delay * 16) return; // delay staggered spawn
        obj.mesh.position.y += obj.vy;
        obj.mesh.position.x += obj.vx;
        obj.mesh.rotation.x += obj.rx;
        obj.mesh.rotation.y += obj.ry;
        obj.mesh.rotation.z += obj.rz;
      });

      renderer.render(scene, camera);

      // Outro transition: fade out canvas and logo around 2.2s
      if (elapsed > DURATION - 600) {
        const progress = (elapsed - (DURATION - 600)) / 600;
        overlay.style.opacity = String(1 - Math.min(1, progress));
      }

      if (elapsed < DURATION) {
        frameId = requestAnimationFrame(animate);
      } else {
        // Cleanup after transition ends
        cancelAnimationFrame(frameId);
        renderer.dispose();
        overlay.classList.add('yarn-intro-hidden');
        document.body.classList.remove('intro-active');
        setTimeout(() => overlay.remove(), 400);
      }
    }

    // Start intro
    requestAnimationFrame(animate);

    // Skip intro on click/tap
    overlay.addEventListener('click', () => {
      overlay.style.opacity = '0';
      document.body.classList.remove('intro-active');
      setTimeout(() => overlay.remove(), 300);
    });

  } catch (err) {
    console.info('3D intro unavailable:', err);
    overlay.remove();
    document.body.classList.remove('intro-active');
  }
})();
