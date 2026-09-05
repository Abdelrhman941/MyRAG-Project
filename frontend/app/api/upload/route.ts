import { getBackendUrl } from '@/lib/backend-url';
import { NextResponse } from 'next/server';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const sessionId = searchParams.get('session');

    if (!sessionId || !UUID_PATTERN.test(sessionId)) {
      return NextResponse.json({ error: { message: 'Missing or invalid session ID' } }, { status: 400 });
    }

    const url = `${getBackendUrl()}/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/documents/batch`;
    const response = await fetch(url, {
      method: 'POST',
      body: req.body,
      headers: { 'content-type': req.headers.get('content-type')! },
      // @ts-expect-error Node fetch requires duplex for streaming request bodies
      duplex: 'half',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);
      return NextResponse.json(errorData || { error: { message: 'Backend upload failed' } }, {
        status: response.status,
      });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Proxy upload error:', error);
    return NextResponse.json({ error: { message: 'Internal proxy error' } }, { status: 500 });
  }
}
