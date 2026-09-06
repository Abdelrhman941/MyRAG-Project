import { NextResponse } from 'next/server';

import { getBackendUrl } from '@/lib/backend-url';

export const runtime = 'nodejs';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(req: Request) {
  try {
    const { searchParams } = new URL(req.url);
    const sessionId = searchParams.get('session');

    if (!sessionId || !UUID_PATTERN.test(sessionId)) {
      return NextResponse.json(
        { error: { message: 'Missing or invalid session ID' } },
        { status: 400 }
      );
    }

    const contentType = req.headers.get('content-type');

    if (!contentType) {
      return NextResponse.json(
        { error: { message: 'Missing Content-Type header' } },
        { status: 400 }
      );
    }

    const url = `${getBackendUrl()}/api/v1/chat/sessions/${encodeURIComponent(
      sessionId
    )}/documents/batch`;

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'content-type': contentType,
      },
      body: req.body,
      signal: req.signal,
      // Required by Node.js fetch when streaming a request body.
      // @ts-expect-error Node fetch requires duplex for streaming request bodies.
      duplex: 'half',
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => null);

      return NextResponse.json(errorData ?? { error: { message: 'Backend upload failed' } }, {
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
