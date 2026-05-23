import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <Button asChild>
          <Link href="/new">Job Baru</Link>
        </Button>
      </div>
      <p className="text-muted-foreground">
        Belum ada job. Daftar job akan tampil di sini (Sprint 2).
      </p>
    </div>
  );
}
