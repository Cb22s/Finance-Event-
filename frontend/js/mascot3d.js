// ============================================================================
// MIRA 3D — VRM anime character renderer
// ============================================================================
// Loads a real artist-made anime model (.vrm) and renders it with three.js.
//
// FAIL-SAFE BY DESIGN: if the model file is missing, the CDN is blocked, WebGL
// is unavailable, or anything else throws, this module does nothing and the 2D
// SVG character in mascot.js stays on screen. The guide can degrade, but it can
// never take the dashboard down on event day.
//
// Pinned versions: three 0.180.0 + @pixiv/three-vrm 3.5.5 (peer dep: three>=0.137).
// ============================================================================

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRMUtils } from '@pixiv/three-vrm';

const MODEL_URL = './assets/mira.vrm';

// VRM 1.0 standard expression names. Mapped from our game moods.
const MOOD_TO_VRM = {
    happy:   'happy',
    excited: 'happy',
    alert:   'surprised',
    worried: 'sad',
    sleepy:  'relaxed'
};
// How strongly to apply each — full 1.0 on every mood looks cartoonish.
const MOOD_WEIGHT = { happy: 0.75, excited: 1.0, alert: 0.7, worried: 0.85, sleepy: 0.6 };

let vrm = null;
let currentMood = 'happy';
let targetWeights = {};

function boot() {
    const body = document.getElementById('mascotBody');
    if (!body) return;

    // WebGL support probe — some lab machines and locked-down browsers lack it.
    const probe = document.createElement('canvas');
    const hasWebGL = !!(probe.getContext('webgl2') || probe.getContext('webgl'));
    if (!hasWebGL) {
        console.info('[Mira] No WebGL — staying on the 2D character.');
        return;
    }

    const W = 200, H = 260;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(W, H);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.domElement.id = 'miraCanvas';
    renderer.domElement.style.cssText = 'display:block;width:100%;height:100%;';

    const scene = new THREE.Scene();

    // Soft key + fill so the model reads on a light background without blowing out.
    const key = new THREE.DirectionalLight(0xffffff, 2.0);
    key.position.set(1, 1.6, 1.4);
    scene.add(key);
    scene.add(new THREE.AmbientLight(0xdbeafe, 1.6));
    const rim = new THREE.DirectionalLight(0x7dd3fc, 0.8);
    rim.position.set(-1.2, 1.0, -1);
    scene.add(rim);

    // Framed on head and shoulders — a full body at this size is unreadable.
    const camera = new THREE.PerspectiveCamera(28, W / H, 0.1, 20);
    camera.position.set(0, 1.32, 1.05);
    camera.lookAt(0, 1.28, 0);

    const lookTarget = new THREE.Object3D();
    camera.add(lookTarget);
    scene.add(camera);

    const loader = new GLTFLoader();
    loader.register((parser) => new VRMLoaderPlugin(parser));

    loader.load(
        MODEL_URL,
        (gltf) => {
            vrm = gltf.userData.vrm;
            if (!vrm) { console.warn('[Mira] Not a VRM file — keeping 2D.'); return; }

            VRMUtils.removeUnnecessaryVertices(gltf.scene);
            VRMUtils.combineSkeletons(gltf.scene);
            VRMUtils.rotateVRM0(vrm);          // no-op for VRM 1.0, fixes VRM 0.x facing

            vrm.scene.traverse((o) => { o.frustumCulled = false; });
            scene.add(vrm.scene);

            if (vrm.lookAt) vrm.lookAt.target = lookTarget;

            // Swap the 2D drawing out for the live model.
            const svg = body.querySelector('svg');
            if (svg) svg.style.display = 'none';
            body.appendChild(renderer.domElement);
            body.classList.add('is3d');

            applyMood(currentMood);
            console.info('[Mira] 3D model loaded.');
        },
        undefined,
        (err) => {
            console.info('[Mira] Model not loaded (' + (err && err.message) +
                         ') — staying on the 2D character. Drop a .vrm at ' + MODEL_URL);
        }
    );

    // ── Head follows the cursor ──
    let mx = 0, my = 0;
    window.addEventListener('pointermove', (e) => {
        mx = (e.clientX / window.innerWidth) * 2 - 1;
        my = -(e.clientY / window.innerHeight) * 2 + 1;
    }, { passive: true });

    const reduced = window.matchMedia &&
        window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const clock = new THREE.Clock();
    let blinkAt = 2 + Math.random() * 3;
    let t = 0;

    function animate() {
        requestAnimationFrame(animate);
        const dt = clock.getDelta();
        if (!vrm) return;
        t += dt;

        lookTarget.position.set(mx * 0.4, my * 0.25, -1);

        const em = vrm.expressionManager;
        if (em) {
            // Ease expression weights so moods cross-fade instead of snapping.
            for (const name in targetWeights) {
                const cur = em.getValue(name) || 0;
                em.setValue(name, cur + (targetWeights[name] - cur) * Math.min(1, dt * 6));
            }
            // Irregular blinking — a fixed interval reads robotic.
            if (!reduced) {
                blinkAt -= dt;
                if (blinkAt <= 0) {
                    em.setValue('blink', 1);
                    setTimeout(() => em && em.setValue('blink', 0), 110);
                    blinkAt = 2 + Math.random() * 4;
                }
            }
        }

        if (!reduced && vrm.humanoid) {
            // Breathing + idle sway. Small amplitudes: big ones look like a seizure.
            const chest = vrm.humanoid.getNormalizedBoneNode('chest');
            const spine = vrm.humanoid.getNormalizedBoneNode('spine');
            const head  = vrm.humanoid.getNormalizedBoneNode('head');
            if (chest) chest.rotation.x = Math.sin(t * 1.6) * 0.022;
            if (spine) spine.rotation.y = Math.sin(t * 0.7) * 0.03;
            if (head)  head.rotation.z  = Math.sin(t * 0.9) * 0.025;
        }

        vrm.update(dt);
        renderer.render(scene, camera);
    }
    animate();
}

function applyMood(mood) {
    currentMood = mood;
    if (!vrm || !vrm.expressionManager) return;
    targetWeights = { happy: 0, angry: 0, sad: 0, relaxed: 0, surprised: 0 };
    const name = MOOD_TO_VRM[mood];
    if (name) targetWeights[name] = MOOD_WEIGHT[mood] || 0.8;
}

// mascot.js calls this instead of drawing SVG faces once 3D is live.
window.MiraCore = window.MiraCore || {};
window.MiraCore.on3D = applyMood;

try { boot(); } catch (e) { console.info('[Mira] 3D init failed, 2D fallback active.', e); }
