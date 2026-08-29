import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

export async function POST(req: Request) {
  try {
    const formData = await req.formData();
    const sessionId = formData.get('sessionId');

    if (!sessionId) {
      return NextResponse.json({ error: { message: 'Missing sessionId' } }, { status: 400 });
    }

    // Remove sessionId from formData before sending to backend
    formData.delete('sessionId');

    const url = `${BACKEND_URL}/api/v1/chat/sessions/${sessionId}/documents/batch`;
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
