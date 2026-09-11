// POST /api/generate  { topic } -> { jobId }
// Kicks off the video pipeline on Modal and returns immediately.
export async function onRequestPost(context) {
  let body;
  try {
    body = await context.request.json();
  } catch {
    return Response.json({ error: 'Invalid JSON' }, { status: 400 });
  }
  const topic = (body.topic || '').trim();
  if (!topic) return Response.json({ error: 'Topic is required' }, { status: 400 });
  if (topic.length > 300) return Response.json({ error: 'Topic is too long' }, { status: 400 });

  const generateUrl = context.env.MODAL_GENERATE_URL;
  const modalSecret = context.env.MODAL_WEBHOOK_SECRET;
  if (!generateUrl) return Response.json({ error: 'Backend not configured' }, { status: 503 });

  const jobId = crypto.randomUUID();
  try {
    const res = await fetch(generateUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(modalSecret ? { Authorization: `Bearer ${modalSecret}` } : {}),
      },
      body: JSON.stringify({ jobId, topic }),
    });
    if (!res.ok) throw new Error(`Modal responded ${res.status}`);
  } catch (err) {
    console.error('Failed to start Modal job:', err);
    return Response.json({ error: 'Could not start video job' }, { status: 502 });
  }
  return Response.json({ jobId });
}
