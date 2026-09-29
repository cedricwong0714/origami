"use client";

import { Component, useMemo, type ReactNode } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import * as THREE from "three";
import type { HelixScene } from "@/lib/sa";

type ScrewViewProps = {
  scene: HelixScene | null;
  selected?: number | null;
};

type ScrewModel = {
  curve: THREE.CatmullRomCurve3 | null;
  segments: number;
  sites: { index: number; graft: boolean; position: THREE.Vector3 }[];
  distance: number;
};

class ViewBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };

  static getDerivedStateFromError(): { failed: boolean } {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <div className="flex h-[560px] items-center justify-center rounded-xl bg-[#1c1a18] px-6 text-center text-sm text-[#E7E0D6]">
          This browser could not start the 3D view. The coordinates are still in the tables and in the PDB export.
        </div>
      );
    }
    return this.props.children;
  }
}

function centroid(points: number[][]): [number, number, number] {
  if (points.length === 0) return [0, 0, 0];
  const sum = points.reduce(
    (acc, point) => [acc[0] + point[0], acc[1] + point[1], acc[2] + point[2]],
    [0, 0, 0]
  );
  return [sum[0] / points.length, sum[1] / points.length, sum[2] / points.length];
}

function buildModel(scene: HelixScene): ScrewModel {
  const cloud = scene.ca_A;
  const sitePoints = scene.sites.map((site) => [site.x_A, site.y_A, site.z_A]);
  const origin = centroid(cloud.length > 0 ? cloud : sitePoints);
  const shift = (x: number, y: number, z: number) =>
    new THREE.Vector3(x - origin[0], y - origin[1], z - origin[2]);
  const ca = cloud.map((point) => shift(point[0], point[1], point[2]));
  const curve = ca.length >= 2 ? new THREE.CatmullRomCurve3(ca, false, "centripetal", 0.5) : null;
  const segments = Math.max(ca.length * 2, 64);
  const sites = scene.sites.map((site) => ({
    index: site.index,
    graft: Boolean(site.m13_graft),
    position: shift(site.x_A, site.y_A, site.z_A),
  }));
  const reach = Math.max(
    18,
    ...ca.map((point) => point.length()),
    ...sites.map((site) => site.position.length())
  );
  // Pull back so the upright screw, including the tube radius, sits inside a 34° frame.
  const halfFov = (34 * Math.PI) / 360;
  const distance = (reach / Math.tan(halfFov)) * 1.18;
  return { curve, segments, sites, distance };
}

function ScrewMesh({ model, selected }: { model: ScrewModel; selected: number | null }) {
  return (
    // Deposited coordinates are z-up. Three.js is y-up, so the screw stands upright.
    <group rotation={[-Math.PI / 2, 0, 0]}>
      {model.curve ? (
        <mesh>
          <tubeGeometry args={[model.curve, model.segments, 1.35, 12, false]} />
          <meshStandardMaterial color="#d7e4f2" roughness={0.38} metalness={0.05} />
        </mesh>
      ) : null}
      {model.sites.map((site) => {
        const last = site.index === model.sites.length - 1;
        const color =
          site.graft || selected === site.index
            ? "#ff8000"
            : site.index === 0
              ? "#3d8fd4"
              : last
                ? "#c45c12"
                : "#2a2622";
        return (
          <mesh key={site.index} position={site.position}>
            <sphereGeometry args={[site.graft ? 3.1 : 1.85, 32, 32]} />
            <meshStandardMaterial color={color} roughness={0.28} />
          </mesh>
        );
      })}
    </group>
  );
}

export function ScrewView({ scene, selected = null }: ScrewViewProps) {
  const model = useMemo(() => (scene && scene.sites.length > 0 ? buildModel(scene) : null), [scene]);

  if (!model) {
    return (
      <div className="flex h-[560px] items-center justify-center rounded-xl bg-[#1c1a18] text-sm text-[#E7E0D6]">
        Run a prediction to place the screw.
      </div>
    );
  }

  const distance = model.distance;
  const eye = new THREE.Vector3(0.62, 0.2, 0.78).normalize().multiplyScalar(distance);
  return (
    <ViewBoundary>
      <div className="h-[560px] w-full overflow-hidden rounded-xl bg-[#1c1a18]">
        <Canvas
          camera={{
            fov: 34,
            near: 0.1,
            far: distance * 40,
            position: [eye.x, eye.y, eye.z],
          }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: false }}
        >
          <color attach="background" args={["#1c1a18"]} />
          <ambientLight intensity={0.55} />
          <hemisphereLight args={["#f4efe6", "#2a2420", 0.45]} />
          <directionalLight position={[80, 120, 40]} intensity={1.45} />
          <directionalLight position={[-60, 20, -80]} intensity={0.35} />
          <ScrewMesh model={model} selected={selected ?? null} />
          <OrbitControls
            makeDefault
            autoRotate
            autoRotateSpeed={1.6}
            enableDamping
            target={[0, 0, 0]}
          />
        </Canvas>
      </div>
    </ViewBoundary>
  );
}
