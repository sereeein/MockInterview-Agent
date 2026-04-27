"use client";
import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { startMock } from "@/lib/api";

function MockEntryView() {
  const sp = useSearchParams();
  const router = useRouter();
  const sessionId = Number(sp.get("session"));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) {
      setError("缺少 session 参数");
      return;
    }
    startMock(sessionId)
      .then((ms) => router.push(`/mock/${ms.id}`))
      .catch((e) => setError(String(e)));
  }, [sessionId, router]);

  return <main className="container py-12">{error ?? "起会话中……"}</main>;
}

export default function MockEntry() {
  return (
    <Suspense fallback={<main className="container py-12">起会话中……</main>}>
      <MockEntryView />
    </Suspense>
  );
}
