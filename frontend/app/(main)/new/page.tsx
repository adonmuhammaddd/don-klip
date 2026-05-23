import { JobForm } from "@/components/job/job-form";

export default function NewJobPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Buat Job Baru</h1>
      <JobForm />
    </div>
  );
}
