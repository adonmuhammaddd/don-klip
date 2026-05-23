import { JobProgress } from "@/components/job/job-progress";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <JobProgress jobId={id} />;
}
