import { getSessions, createSession } from '@/lib/api';
import { redirect } from 'next/navigation';

export default async function IndexPage() {
  const sessions = await getSessions();
  if (sessions && sessions.length > 0) {
    redirect(`/chat/${sessions[0].id}`);
  } else {
    let session;
    try {
      session = await createSession();
    } catch (e) {
      console.error(e);
      throw new Error('Failed to initialize session');
    }
    redirect(`/chat/${session.id}`);
  }
}
