"use client";

import { useEffect, useRef } from "react";
import type { HelixScene } from "@/lib/sa";

type HelixCanvasProps = {
  scene: HelixScene | null;
  selected?: number | null;
};

function project(x: number, y: number, z: number) {
  const yaw = Math.PI / 5;
  const pitch = 0.55;
  const cy = Math.cos(yaw);
  const sy = Math.sin(yaw);
  const cp = Math.cos(pitch);
  const sp = Math.sin(pitch);
  const x1 = x * cy - y * sy;
  const y1 = x * sy + y * cy;
  const y2 = y1 * cp - z * sp;
  const z2 = y1 * sp + z * cp;
  return { x: x1, y: z2, depth: y2 };
}

export function HelixCanvas({ scene, selected = null }: HelixCanvasProps) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = Math.floor(width * dpr);
    canvas.height = Math.floor(height * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, height);

    ctx.fillStyle = "#F7F1E8";
    ctx.fillRect(0, 0, width, height);

    if (!scene || scene.sites.length === 0) {
      ctx.fillStyle = "#8A8175";
      ctx.font = "13px 'IBM Plex Sans', sans-serif";
      ctx.fillText("Run a prediction to place the screw.", 24, height / 2);
      return;
    }

    const pts = [
      ...scene.ca_A.map((p) => ({ ...project(p[0], p[1], p[2]), kind: "ca" as const })),
      ...scene.sites.map((s) => ({
        ...project(s.x_A, s.y_A, s.z_A),
        kind: "site" as const,
        index: s.index,
      })),
    ];
    const xs = pts.map((p) => p.x);
    const ys = pts.map((p) => p.y);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);
    const pad = 36;
    const sx = (width - pad * 2) / Math.max(maxX - minX, 1);
    const sy = (height - pad * 2) / Math.max(maxY - minY, 1);
    const scale = Math.min(sx, sy);
    const mapX = (x: number) => pad + (x - minX) * scale;
    const mapY = (y: number) => height - pad - (y - minY) * scale;

    const axis = scene.sites.map((s) => project(0, 0, s.z_A));
    ctx.strokeStyle = "#D9CFC2";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    axis.forEach((p, i) => {
      const x = mapX(p.x);
      const y = mapY(p.y);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    const ca = scene.ca_A.map((p) => project(p[0], p[1], p[2]));
    ctx.fillStyle = "rgba(38, 111, 177, 0.22)";
    ca.forEach((p) => {
      ctx.beginPath();
      ctx.arc(mapX(p.x), mapY(p.y), 1.6, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.strokeStyle = "#FF8000";
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    scene.sites.forEach((s, i) => {
      const p = project(s.x_A, s.y_A, s.z_A);
      const x = mapX(p.x);
      const y = mapY(p.y);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    scene.sites.forEach((s) => {
      const p = project(s.x_A, s.y_A, s.z_A);
      const x = mapX(p.x);
      const y = mapY(p.y);
      const active = selected === s.index;
      ctx.beginPath();
      ctx.arc(x, y, active ? 7 : 5, 0, Math.PI * 2);
      ctx.fillStyle = s.index === 0 ? "#266FB1" : s.index === scene.sites.length - 1 ? "#C45C12" : "#242220";
      if (active) ctx.fillStyle = "#FF8000";
      ctx.fill();
      ctx.fillStyle = "#5C564E";
      ctx.font = "11px 'IBM Plex Sans', sans-serif";
      ctx.fillText(String(s.index), x + 8, y - 6);
    });

    ctx.fillStyle = "#8A8175";
    ctx.font = "11px 'IBM Plex Sans', sans-serif";
    ctx.fillText("orange: junctions · blue cloud: Cα · left: SpyCatcher-side 0", 16, height - 12);
  }, [scene, selected]);

  return (
    <canvas
      ref={ref}
      className="h-[320px] w-full rounded-xl border border-[#E3D9CC] bg-[#F7F1E8] md:h-[420px]"
    />
  );
}
