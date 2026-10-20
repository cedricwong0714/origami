import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const apiBase = (process.env.STRUCTURAL_API_URL ?? "http://127.0.0.1:41287").replace(/\/$/, "");

async function proxy(request: NextRequest, path: string[]): Promise<NextResponse> {
  const target = `${apiBase}/api/${path.map(encodeURIComponent).join("/")}${request.nextUrl.search}`;
  try {
    const headers = new Headers();
    const contentType = request.headers.get("content-type");
    if (contentType) headers.set("content-type", contentType);
    const init: RequestInit = { method: request.method, headers, redirect: "manual" };
    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.text();
    }
    const upstream = await fetch(target, init);
    const text = await upstream.text();
    const trimmed = text.trim();
    const looksJson = trimmed.startsWith("{") || trimmed.startsWith("[");
    if (!looksJson) {
      return NextResponse.json(
        {
          detail:
            "The calculator did not return model data. Check that the Python API is running and that STRUCTURAL_API_URL is a public address.",
        },
        { status: 502 },
      );
    }
    return new NextResponse(text, {
      status: upstream.status,
      headers: { "content-type": "application/json" },
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "The calculator is not connected on this host. Start the Python API, or set STRUCTURAL_API_URL to a public address.",
      },
      { status: 502 },
    );
  }
}

type Context = { params: Promise<{ path: string[] }> };

async function handle(request: NextRequest, context: Context): Promise<NextResponse> {
  const { path } = await context.params;
  return proxy(request, path);
}

export const GET = handle;
export const POST = handle;
export const PUT = handle;
export const PATCH = handle;
export const DELETE = handle;
