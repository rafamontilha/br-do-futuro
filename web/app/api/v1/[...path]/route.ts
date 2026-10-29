import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.API_URL || "http://127.0.0.1:18080";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(request.url);
  const targetUrl = `${API_BASE}/v1/${targetPath}${url.search}`;

  const headers = new Headers();
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const role = request.headers.get("x-actor-role");
  if (role) headers.set("x-actor-role", role);

  try {
    const res = await fetch(targetUrl, {
      method: "GET",
      headers,
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: "api_gateway_unavailable", details: err?.message },
      { status: 503 }
    );
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const targetPath = path.join("/");
  const url = new URL(request.url);
  const targetUrl = `${API_BASE}/v1/${targetPath}${url.search}`;

  const headers = new Headers();
  headers.set("content-type", "application/json");
  const auth = request.headers.get("authorization");
  if (auth) headers.set("authorization", auth);
  const role = request.headers.get("x-actor-role");
  if (role) headers.set("x-actor-role", role);

  const bodyText = await request.text();

  try {
    const res = await fetch(targetUrl, {
      method: "POST",
      headers,
      body: bodyText,
      cache: "no-store",
    });
    const data = await res.json().catch(() => ({}));
    return NextResponse.json(data, { status: res.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: "api_gateway_unavailable", details: err?.message },
      { status: 503 }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      Allow: "GET, POST, OPTIONS",
    },
  });
}
