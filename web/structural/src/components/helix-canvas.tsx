"use client";

import { useCallback, useEffect, useRef, type PointerEvent } from "react";
import { useStudioTheme } from "@/components/theme-provider";
import type { HelixScene } from "@/lib/sa";

function studioVar(name: string, fallback: string): string {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

type HelixCanvasProps = {
  scene: HelixScene | null;
  selected?: number | null;
};

type Point = { x: number; y: number; depth: number };

function interCanvasFont(size: number): string {
  const raw = getComputedStyle(document.documentElement).getPropertyValue("--font-inter").trim();
  const family = raw || "Inter, sans-serif";
  return `${size}px ${family}`;
}

function project(x: number, y: number, z: number, yaw: number, pitch: number): Point {
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
  const view = useRef({ yaw: Math.PI / 5, pitch: 0.55 });
  const drag = useRef<{ x: number; y: number; yaw: number; pitch: number } | null>(null);
  const { theme } = useStudioTheme();

  const paint = useCallback(() => {
    void theme;
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
    ctx.fillStyle = studioVar("--studio-helix-bg", "#F7F1E8");
    ctx.fillRect(0, 0, width, height);

    if (!scene || scene.sites.length === 0) {
      ctx.fillStyle = studioVar("--studio-helix-label", "#8A8175");
      ctx.font = interCanvasFont(13);
      ctx.fillText("Run a prediction to place the screw.", 24, height / 2);
      return;
    }

    const { yaw, pitch } = view.current;
    const projectAt = (x: number, y: number, z: number) => project(x, y, z, yaw, pitch);
    const pts = [
      ...scene.ca_A.map((p) => projectAt(p[0], p[1], p[2])),
      ...scene.sites.map((s) => projectAt(s.x_A, s.y_A, s.z_A)),
    ];
    const minX = Math.min(...pts.map((p) => p.x));
    const maxX = Math.max(...pts.map((p) => p.x));
    const minY = Math.min(...pts.map((p) => p.y));
    const maxY = Math.max(...pts.map((p) => p.y));
    const pad = 36;
    const scale = Math.min(
      (width - pad * 2) / Math.max(maxX - minX, 1),
      (height - pad * 2) / Math.max(maxY - minY, 1)
    );
    const mapX = (x: number) => pad + (x - minX) * scale;
    const mapY = (y: number) => height - pad - (y - minY) * scale;
    const place = (x: number, y: number, z: number) => {
      const p = projectAt(x, y, z);
      return { x: mapX(p.x), y: mapY(p.y), depth: p.depth };
    };

    const axis = scene.sites.map((s) => place(0, 0, s.z_A));
    ctx.strokeStyle = studioVar("--studio-helix-axis", "#D9CFC2");
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    axis.forEach((p, i) => {
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();

    const ca = scene.ca_A
      .map((p) => place(p[0], p[1], p[2]))
      .sort((a, b) => a.depth - b.depth);
    ctx.fillStyle = "rgba(38, 111, 177, 0.28)";
    ca.forEach((p) => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.6, 0, Math.PI * 2);
      ctx.fill();
    });

    const sites = scene.sites.map((s) => ({ site: s, p: place(s.x_A, s.y_A, s.z_A) }));
    ctx.strokeStyle = "#FF8000";
    ctx.lineWidth = 2.4;
    ctx.beginPath();
    sites.forEach((row, i) => {
      if (i === 0) ctx.moveTo(row.p.x, row.p.y);
      else ctx.lineTo(row.p.x, row.p.y);
    });
    ctx.stroke();

    const graft = sites.find((row) => row.site.m13_graft);
    const nEnd = sites[0];
    const cEnd = sites[sites.length - 1];
    if (graft && nEnd && cEnd && graft !== nEnd && graft !== cEnd) {
      ctx.strokeStyle = "#266FB1";
      ctx.setLineDash([4, 4]);
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(nEnd.p.x, nEnd.p.y);
      ctx.lineTo(graft.p.x, graft.p.y);
      ctx.lineTo(cEnd.p.x, cEnd.p.y);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    sites.forEach(({ site, p }) => {
      const active = selected === site.index;
      ctx.beginPath();
      ctx.arc(p.x, p.y, active || site.m13_graft ? 7 : 5, 0, Math.PI * 2);
      ctx.fillStyle =
        site.index === 0
          ? studioVar("--studio-blue", "#266FB1")
          : site.index === sites.length - 1
            ? studioVar("--studio-accent", "#C45C12")
            : studioVar("--studio-helix-marker", "#242220");
      if (site.m13_graft || active) ctx.fillStyle = "#FF8000";
      ctx.fill();
      if (site.m13_graft) {
        ctx.strokeStyle = studioVar("--studio-helix-marker", "#242220");
        ctx.lineWidth = 1.5;
        ctx.stroke();
      }
      ctx.fillStyle = studioVar("--studio-muted", "#5C564E");
      ctx.font = interCanvasFont(11);
      ctx.fillText(site.m13_graft ? `${site.index} m13` : String(site.index), p.x + 8, p.y - 6);
    });

    ctx.fillStyle = studioVar("--studio-helix-label", "#8A8175");
    ctx.font = interCanvasFont(11);
    ctx.fillText("drag to rotate · pixel distance is not Å · dashed lines are graft chords · 0 is the SpyCatcher side", 16, height - 12);
  }, [scene, selected, theme]);

  useEffect(() => {
    paint();
  }, [paint]);

  function onPointerDown(event: PointerEvent<HTMLCanvasElement>) {
    drag.current = {
      x: event.clientX,
      y: event.clientY,
      yaw: view.current.yaw,
      pitch: view.current.pitch,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onPointerMove(event: PointerEvent<HTMLCanvasElement>) {
    if (!drag.current) return;
    const yaw = drag.current.yaw + (event.clientX - drag.current.x) * 0.01;
    const pitch = Math.min(1.2, Math.max(-1.2, drag.current.pitch + (event.clientY - drag.current.y) * 0.01));
    view.current = { yaw, pitch };
    paint();
  }

  function onPointerUp() {
    drag.current = null;
  }

  function onDoubleClick() {
    view.current = { yaw: Math.PI / 5, pitch: 0.55 };
    paint();
  }

  return (
    <canvas
      ref={ref}
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerUp}
      onDoubleClick={onDoubleClick}
      className="h-[320px] w-full touch-none rounded-xl border border-studio-border bg-studio-helix-bg md:h-[420px]"
    />
  );
}
