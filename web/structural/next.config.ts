import type { NextConfig } from "next";

const onVercel = process.env.VERCEL === "1";

if (onVercel && !process.env.STRUCTURAL_API_URL) {
  console.warn(
    "STRUCTURAL_API_URL is not set. /api routes on Vercel will proxy to localhost and fail. " +
      "Add your Render API URL in Vercel → Project → Environment Variables.",
  );
}

const nextConfig: NextConfig = {
  // The app directory includes a route handler, so this build stays a Node
  // server. Static export cannot host that handler and `next build` fails.
  images: { unoptimized: true },
  basePath: process.env.NEXT_BASE_PATH || "",
  async rewrites() {
    // /api is handled by src/app/api/[...path]/route.ts, which always returns
    // JSON. A rewrite to a private host makes Vercel answer with plain text
    // and the browser then crashes on response.json().
    return [];
  },
};

export default nextConfig;
