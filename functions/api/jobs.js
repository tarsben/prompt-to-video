// GET /api/jobs -> { jobs: [...] }  (newest first, max 20)
// Proxies the Modal list_jobs endpoint (stateless — no KV needed).
export async function onRequestGet(context) {
  const modalSecret = context.env.MODAL_WEBHOOK_SECRET;
  let listUrl = context.env.MODAL_LIST_URL;
  if (!listUrl) {
    // Fall back to deriving it from the generate URL: Modal names web
    // endpoints https://<workspace>--<app>-<function>.modal.run, and this
    // repo deploys the list function as `list_jobs` -> `-list-jobs`.
    const genUrl = context.env.MODAL_GENERATE_URL || '';
    const m = genUrl.match(/^(https:\/\/.*)-generate(\.modal\.run\/?)$/);
    if (m) listUrl = `${m[1]}-list-jobs${m[2]}`;
  }
  if (!listUrl) return Response.json({ error: 'Backend not configured' }, { status: 503 });

  try {
    const res = await fetch(listUrl, {
      headers: modalSecret ? { Authorization: `Bearer ${modalSecret}` } : {},
    });
    const data = await res.json();
    return Response.json(data, { status: res.status });
  } catch (err) {
    console.error('Jobs proxy failed:', err);
    return Response.json({ error: 'Could not reach backend' }, { status: 502 });
  }
}
