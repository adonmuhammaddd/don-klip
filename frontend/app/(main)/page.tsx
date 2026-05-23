import Link from "next/link";

import { JobList } from "@/components/job/job-list";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Button asChild>
          <Link href="/new">Job Baru</Link>
        </Button>
      </div>
      <JobList />
    </div>
  );
}
