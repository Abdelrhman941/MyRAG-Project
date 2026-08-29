import { getBackendUrl } from '@/lib/backend-url';
import { NextResponse } from 'next/server';

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const sessionId = formData.get('sessionId');

    if (typeof sessionId !== 'string' || !UUID_PATTERN.test(sessionId)) {
      return NextResponse.json({ error: { message: 'Missing sessionId' } }, { status: 400 });
    }

    // Remove sessionId from formData before sending to backend
    formData.delete('sessionId');

    const url = `${getBackendUrl()}/api/v1/chat/sessions/${encodeURIComponent(sessionId)}/documents/batch`;
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
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
