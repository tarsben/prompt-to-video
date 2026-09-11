// GET /api/status?jobId=... -> { stage, videoUrl?, error? }
// Proxies job state from the Modal backend (stateless — no KV needed).
export async function onRequestGet(context) {
  const jobId = new URL(context.request.url).searchParams.get('jobId');
  if (!jobId) return Response.json({ error: 'jobId is required' }, { status: 400 });

  const modalBase = context.env.MODAL_BASE_URL;
  const modalSecret = context.env.MODAL_WEBHOOK_SECRET;
  if (!modalBase) return Response.json({ error: 'Backend not configured' }, { status: 503 });

  try {
    const res = await fetch(`${modalBase}/status?jobId=${encodeURIComponent(jobId)}`, {
      headers: modalSecret ? { Authorization: `Bearer ${modalSecret}` } : {},
    });
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch (err) {
    console.error('Status proxy failed:', err);
    return Response.json({ error: 'Could not reach backend' }, { status: 502 });
  }
}
