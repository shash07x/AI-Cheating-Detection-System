import { useEffect, useRef } from "react";
import * as THREE from "three";

export default function SpeakingScene({ audioLevel = 0 }) {
  const mountRef = useRef(null);
  const audioLevelRef = useRef(audioLevel);

  useEffect(() => {
    audioLevelRef.current = audioLevel;
  }, [audioLevel]);

  useEffect(() => {
    const mount = mountRef.current;
    if (!mount) {
      return undefined;
    }

    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x050816, 0.035);

    const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 1000);
    camera.position.set(0, 0, 14);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x02030a, 1);
    mount.appendChild(renderer.domElement);

    const ambient = new THREE.AmbientLight(0x7a8cff, 0.9);
    const keyLight = new THREE.PointLight(0x8ef3ff, 2.4, 120);
    keyLight.position.set(7, 4, 14);
    const rimLight = new THREE.PointLight(0xff49c6, 2.6, 120);
    rimLight.position.set(-10, -6, 10);
    scene.add(ambient, keyLight, rimLight);

    const globe = new THREE.Group();
    scene.add(globe);

    const globeGeometry = new THREE.IcosahedronGeometry(3.3, 12);
    const globeMaterial = new THREE.MeshPhongMaterial({
      color: 0x4b7bff,
      emissive: 0x17245d,
      shininess: 90,
      wireframe: true,
      transparent: true,
      opacity: 0.55,
    });
    const globeMesh = new THREE.Mesh(globeGeometry, globeMaterial);
    globe.add(globeMesh);

    const shellGeometry = new THREE.SphereGeometry(3.85, 48, 48);
    const shellMaterial = new THREE.MeshBasicMaterial({
      color: 0x7af7ff,
      transparent: true,
      opacity: 0.08,
      blending: THREE.AdditiveBlending,
    });
    const shell = new THREE.Mesh(shellGeometry, shellMaterial);
    globe.add(shell);

    const nebulaGroup = new THREE.Group();
    scene.add(nebulaGroup);

    const nebulaColors = [0x4b7bff, 0x8f52ff, 0x00e5ff, 0xff4fd8];
    const nebulaClouds = [];
    nebulaColors.forEach((color, index) => {
      const cloud = new THREE.Mesh(
        new THREE.PlaneGeometry(18 + index * 4, 18 + index * 4),
        new THREE.MeshBasicMaterial({
          color,
          transparent: true,
          opacity: 0.08,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        })
      );
      cloud.position.set((index - 1.5) * 1.5, (index % 2 === 0 ? 1 : -1) * 1.2, -8 - index * 2);
      nebulaGroup.add(cloud);
      nebulaClouds.push(cloud);
    });

    const starCount = 1800;
    const starPositions = new Float32Array(starCount * 3);
    const starColors = new Float32Array(starCount * 3);
    const color = new THREE.Color();
    for (let i = 0; i < starCount; i += 1) {
      const i3 = i * 3;
      const radius = 28 + Math.random() * 32;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      starPositions[i3] = radius * Math.sin(phi) * Math.cos(theta);
      starPositions[i3 + 1] = radius * Math.sin(phi) * Math.sin(theta);
      starPositions[i3 + 2] = radius * Math.cos(phi);

      color.setHSL(0.55 + Math.random() * 0.2, 0.9, 0.7 + Math.random() * 0.2);
      starColors[i3] = color.r;
      starColors[i3 + 1] = color.g;
      starColors[i3 + 2] = color.b;
    }

    const starGeometry = new THREE.BufferGeometry();
    starGeometry.setAttribute("position", new THREE.BufferAttribute(starPositions, 3));
    starGeometry.setAttribute("color", new THREE.BufferAttribute(starColors, 3));
    const stars = new THREE.Points(
      starGeometry,
      new THREE.PointsMaterial({
        size: 0.16,
        vertexColors: true,
        transparent: true,
        opacity: 0.95,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      })
    );
    scene.add(stars);

    const resize = () => {
      const width = mount.clientWidth;
      const height = mount.clientHeight;
      camera.aspect = width / Math.max(height, 1);
      camera.updateProjectionMatrix();
      renderer.setSize(width, height);
    };

    resize();
    window.addEventListener("resize", resize);

    const clock = new THREE.Clock();
    let frameId = 0;

    const animate = () => {
      const elapsed = clock.getElapsedTime();
      const voiceEnergy = THREE.MathUtils.clamp(audioLevelRef.current, 0, 1);
      const pulse = 1 + voiceEnergy * 0.32;

      globe.rotation.y += 0.0025 + voiceEnergy * 0.01;
      globe.rotation.x = Math.sin(elapsed * 0.2) * 0.15;
      globe.scale.setScalar(0.98 + Math.sin(elapsed * 1.4) * 0.015 + voiceEnergy * 0.14);

      shell.scale.setScalar(pulse * 1.03);
      shell.material.opacity = 0.08 + voiceEnergy * 0.22;
      globeMaterial.opacity = 0.48 + voiceEnergy * 0.4;
      globeMaterial.emissiveIntensity = 0.8 + voiceEnergy * 2.4;

      nebulaGroup.rotation.z += 0.0007;
      nebulaClouds.forEach((cloud, index) => {
        cloud.rotation.z = elapsed * (0.02 + index * 0.005);
        cloud.position.x = Math.sin(elapsed * 0.18 + index) * (1.2 + voiceEnergy * 1.8);
        cloud.position.y = Math.cos(elapsed * 0.15 + index * 0.4) * (0.8 + voiceEnergy * 1.3);
        cloud.material.opacity = 0.07 + voiceEnergy * 0.1;
        cloud.scale.setScalar(1 + voiceEnergy * 0.18);
      });

      stars.rotation.y += 0.00035 + voiceEnergy * 0.0015;
      stars.rotation.x = Math.sin(elapsed * 0.08) * 0.08;
      stars.material.size = 0.16 + voiceEnergy * 0.14;

      camera.position.z = 14 - voiceEnergy * 1.8;
      renderer.render(scene, camera);
      frameId = window.requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.cancelAnimationFrame(frameId);
      window.removeEventListener("resize", resize);
      mount.removeChild(renderer.domElement);

      globeGeometry.dispose();
      shellGeometry.dispose();
      starGeometry.dispose();
      globeMaterial.dispose();
      shellMaterial.dispose();
      stars.material.dispose();
      nebulaClouds.forEach((cloud) => {
        cloud.geometry.dispose();
        cloud.material.dispose();
      });
      renderer.dispose();
    };
  }, []);

  return <div className="scene-canvas" ref={mountRef} aria-hidden="true" />;
}
