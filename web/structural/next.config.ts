import type { NextConfig } from "next";

const onVercel = process.env.VERCEL === "1";
const apiBase = (process.env.STRUCTURAL_API_URL ?? "http://127.0.0.1:41287").replace(/\/$/, "");

if (onVercel && !process.env.STRUCTURAL_API_URL) {
  console.warn(
    "STRUCTURAL_API_URL is not set. /api routes on Vercel will proxy to localhost and fail. " +
      "Add your Render API URL in Vercel → Project → Environment Variables.",
  );
}

const nextConfig: NextConfig = {
  // Static export for local/wiki builds; on Vercel use serverless Next so rewrites reach Render.
  ...(onVercel ? {} : { output: "export" as const }),
  images: { unoptimized: true },
  basePath: process.env.NEXT_BASE_PATH || "",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiBase}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
