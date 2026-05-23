export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Job Detail</h1>
      <p className="text-muted-foreground">
        Progress realtime + review klip untuk job <span className="font-mono">{id}</span> akan ada
        di sini (Sprint 2–3).
      </p>
    </div>
  );
}
